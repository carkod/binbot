import requests


class CoinGecko:
    """
    CoinGecko API client for fetching cryptocurrency data.
    """

    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"

    def get_all_categories(self) -> list:
        url = f"{self.base_url}/coins/categories"
        r = requests.get(url)
        r.raise_for_status()
        return [cat["id"] for cat in r.json()]

    def get_coins_in_category(self, category_id: str) -> list:
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "category": category_id,
            "order": "market_cap_desc",
            "per_page": str(250),
            "page": str(1)
        }
        r = requests.get(url, params=params)
        r.raise_for_status()
        page = 1
        all_coins = []
        while True:
            url = f"{self.base_url}/coins/markets"
            params = {
                "vs_currency": "usd",
                "category": category_id,
                "order": "market_cap_desc",
                "per_page": str(250),
                "page": str(page)
            }
            r = requests.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            all_coins.extend(data)
            page += 1
        return all_coins
