import json
from openai import OpenAI

from tools.config import Config
from strategy_thresholds.models import MarketContextPayload, ThresholdRecommendation


class OpenAiThresholdError(Exception):
    pass


class OpenAiThresholdAdvisor:
    def __init__(self, model: str | None = None):
        self.config = Config()
        self.model = model or self.config.grid_threshold_llm_model
        self.client = OpenAI(api_key=self.config.openai_api_key)
        if not self.client.api_key:
            raise OpenAiThresholdError("OPENAI_API_KEY is not configured")

    def _build_prompt(
        self,
        strategy: str,
        symbol: str,
        context: MarketContextPayload,
    ) -> str:
        return (
            "Return ONLY valid JSON for a threshold recommendation. "
            "Use keys: strategy, symbol, profile, buy_trigger_pct, sell_trigger_pct, ttl_minutes, confidence, reason. "
            "Apply conservative thresholds for range markets and reject unstable trend states.\n"
            f"Strategy: {strategy}\n"
            f"Symbol: {symbol}\n"
            f"Market context: {context.model_dump_json()}"
        )

    def suggest(
        self,
        strategy: str,
        symbol: str,
        context: MarketContextPayload,
    ) -> tuple[ThresholdRecommendation, dict]:
        prompt = self._build_prompt(strategy=strategy, symbol=symbol, context=context)
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            text={"format": {"type": "json_object"}},
        )

        output_text = response.output_text
        if not output_text:
            raise OpenAiThresholdError("OpenAI response did not include output_text")

        try:
            payload = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise OpenAiThresholdError("OpenAI response was not valid JSON") from exc

        payload.setdefault("strategy", strategy)
        payload.setdefault("symbol", symbol)

        recommendation = ThresholdRecommendation.model_validate(payload)
        return recommendation, response.model_dump()
