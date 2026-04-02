import logging
from sqlalchemy import text
from sqlmodel import Session, select
from databases.crud.symbols_crud import SymbolsCrud
from databases.crud.autotrade_crud import AutotradeCrud
from databases.crud.asset_index_crud import AssetIndexCrud
from databases.tables.symbol_table import SymbolTable
from databases.utils import get_db_session, independent_session
from pybinbot import QuoteAssets, ExchangeId, BinbotErrors
from kucoin_universal_sdk.generate.spot.market.model_get_all_symbols_resp import (
    GetAllSymbolsResp,
)
from kucoin_universal_sdk.generate.futures.market.model_get_all_symbols_resp import (
    GetAllSymbolsResp as FuturesGetAllSymbolsResp,
)


class SymbolDataEtl(SymbolsCrud):
    """
    Exchange data manipulation to ingest symbols
    data into the database before CRUD operations.
    """

    def __init__(self, session: Session | None = None):
        if session is None:
            session = independent_session()

        super().__init__(session=session)
        self.autotrade_settings = AutotradeCrud().get_settings()
        self.fiat = self.autotrade_settings.fiat

    def binance_symbols_reingestion(self):
        exchange_info_data = self.binance_api.exchange_info()
        for item in exchange_info_data["symbols"]:
            if item["status"] != "TRADING":
                continue
            if item["quoteAsset"] == "TRY":
                continue

            try:
                self.get_symbol(item["symbol"])
            except BinbotErrors:
                price_precision, qty_precision, min_notional = (
                    self.calculate_precisions(item)
                )
                self.add_symbol(
                    symbol=item["symbol"],
                    quote_asset=item["quoteAsset"],
                    base_asset=item["baseAsset"],
                    exchange_id=ExchangeId.BINANCE,
                    active=True,
                    price_precision=price_precision,
                    qty_precision=qty_precision,
                    min_notional=min_notional,
                    is_margin_trading_allowed=item.get("isMarginTradingAllowed", False),
                )

    def binance_symbols_ingestion(self):
        exchange_info_data = self.binance_api.exchange_info()
        filtered_symbols = [
            item
            for item in exchange_info_data["symbols"]
            if str(item["symbol"]).endswith(self.fiat)
        ]

        for item in filtered_symbols:
            if item["status"] != "TRADING" or item["symbol"].startswith(
                ("DOWN", "UP", "AUD", "USDT", "EUR", "GBP")
            ):
                continue
            if item["quoteAsset"] == "TRY":
                continue
            if item["quoteAsset"] in list(QuoteAssets):
                price_precision, qty_precision, min_notional = (
                    self.calculate_precisions(item)
                )
                self.add_symbol(
                    symbol=item["symbol"],
                    quote_asset=item["quoteAsset"],
                    base_asset=item["baseAsset"],
                    exchange_id=ExchangeId.BINANCE,
                    active=True,
                    price_precision=price_precision,
                    qty_precision=qty_precision,
                    min_notional=min_notional,
                    is_margin_trading_allowed=item.get("isMarginTradingAllowed", False),
                )

    def ingest_futures_data(self, all_raw_symbols: FuturesGetAllSymbolsResp):
        """
        - Ingest futures data as a data seed (empty local database)
        - Reingests through cronjob
        - Resets data (when delete_existing=True)
        """
        for item in all_raw_symbols.data:
            symbol = item.symbol

            futures_suffix = f"{self.fiat}M" if self.fiat == "USDT" else self.fiat
            if futures_suffix and not symbol.endswith(futures_suffix):
                continue

            active = True
            if symbol.startswith(("BTC", "ETH")):
                active = False

            if item.quote_currency in list(QuoteAssets):
                price_precision = self._convert_to_int(item.tick_size)
                qty_precision = self._convert_to_int(item.lot_size)
                min_notional = self._convert_to_int(
                    float(item.tick_size)
                    * float(item.lot_size)
                    * float(item.multiplier)
                )

                with get_db_session() as s:
                    result = s.exec(
                        select(SymbolTable).where(SymbolTable.id == symbol)
                    ).first()
                    if result:
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=False,
                        )
                    else:
                        self.add_symbol(
                            symbol=symbol,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            exchange_id=ExchangeId.KUCOIN,
                            active=active,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            min_notional=min_notional,
                        )
                        # ensure exchange link added in same session
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=False,
                        )

    def ingest_spot_data(self, all_raw_symbols: GetAllSymbolsResp):
        for item in all_raw_symbols.data:
            symbol = item.symbol.replace("-", "")
            price_precision = self._convert_to_int(item.price_increment)
            qty_precision = self._convert_to_int(item.base_increment)
            min_notional = float(item.min_funds or item.quote_min_size or 0)

            if not symbol.endswith(self.fiat):
                continue

            if not item.enable_trading or item.symbol.startswith(
                ("DOWN", "UP", "AUD", "EUR", "GBP")
            ):
                continue

            if item.st:
                # assets to be delisted
                try:
                    with get_db_session() as s:
                        result = s.exec(
                            select(SymbolTable).where(SymbolTable.id == symbol)
                        ).first()
                        if result:
                            result.active = False
                            result.blacklist_reason = "At risk to be delisted soon"
                            s.add(result)
                            s.flush()
                            s.refresh(result)
                            self._add_exchange_link_if_not_exists(
                                s,
                                symbol=symbol,
                                exchange_id=ExchangeId.KUCOIN,
                                min_notional=min_notional,
                                price_precision=price_precision,
                                qty_precision=qty_precision,
                                quote_asset=item.quote_currency,
                                base_asset=item.base_currency,
                                is_margin_trading_allowed=item.is_margin_enabled,
                            )
                    continue
                except Exception as e:
                    logging.error(f"Error updating delisted symbol {symbol}: {e}")
                    continue

            active = True
            if symbol in ("BTCUSDC", "ETHUSDC", "BNBUSDC"):
                active = False

            if item.quote_currency in list(QuoteAssets):
                with get_db_session() as s:
                    result = s.exec(
                        select(SymbolTable).where(SymbolTable.id == symbol)
                    ).first()
                    if result:
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=item.is_margin_enabled,
                        )
                    else:
                        self.add_symbol(
                            symbol=symbol,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            exchange_id=ExchangeId.KUCOIN,
                            active=active,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            min_notional=min_notional,
                        )
                        # ensure exchange link added in same session
                        self._add_exchange_link_if_not_exists(
                            s,
                            symbol=symbol,
                            exchange_id=ExchangeId.KUCOIN,
                            min_notional=min_notional,
                            price_precision=price_precision,
                            qty_precision=qty_precision,
                            quote_asset=item.quote_currency,
                            base_asset=item.base_currency,
                            is_margin_trading_allowed=item.is_margin_enabled,
                        )

    def kucoin_symbols_ingestion(self):
        all_spot_symbols = self.kucoin_api.get_all_symbols()
        all_future_symbols = (
            self.kucoin_futures_api.futures_market_api.get_all_symbols()
        )

        self.ingest_spot_data(all_spot_symbols)
        self.ingest_futures_data(all_future_symbols)

    def etl_symbols_ingestion(self, delete_existing: bool = False):
        if delete_existing:
            # TRUNCATE in its own fresh session so it never conflicts with earlier SELECTs
            with get_db_session() as s:
                s.execute(text("TRUNCATE TABLE symbol CASCADE"))

            asset_index_crud = AssetIndexCrud()
            asset_index_crud.delete_all()

        exchange_id = self.autotrade_settings.exchange_id

        if exchange_id == ExchangeId.BINANCE:
            self.binance_symbols_ingestion()
            logging.info("Binance symbols ingestion completed.")
        elif exchange_id == ExchangeId.KUCOIN:
            self.kucoin_symbols_ingestion()
            logging.info("Kucoin symbols ingestion completed.")
        else:
            logging.warning(
                "Skipping symbols ingestion for unsupported exchange %s",
                exchange_id,
            )
