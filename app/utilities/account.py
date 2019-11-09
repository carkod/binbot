import pandas as pd

from utilities.get_data import Account, Exchange_Info, Ticker_Price


def get_balances(min_amount=0.1):
    a = Account()
    data = a.api_data()["balances"]
    df = pd.DataFrame(data)
    df['free'] = pd.to_numeric(df['free'])
    df['asset'] = df['asset'].astype(str)
    df.drop('locked', axis=1, inplace=True)
    df = df[df['free'] > min_amount]
    df.reset_index(drop=True,inplace=True)
    return df
