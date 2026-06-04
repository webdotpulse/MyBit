import pandas as pd
import pandas_ta_classic as ta

class Indicators:
    def __init__(self, data: pd.DataFrame):
        """
        Initialize with a pandas DataFrame containing at least:
        'open', 'high', 'low', 'close', 'volume' columns.
        """
        self.df = data

    def add_ema(self, length=9):
        self.df.ta.ema(length=length, append=True)

    def add_rsi(self, length=14):
        self.df.ta.rsi(length=length, append=True)

    def add_bollinger_bands(self, length=20, std=2):
        self.df.ta.bbands(length=length, std=std, append=True)

    def get_latest(self):
        """Returns the latest indicator values."""
        if self.df.empty:
            return None
        return self.df.iloc[-1]

    def update_data(self, new_data: pd.DataFrame):
        """Update the dataframe and recalculate indicators."""
        self.df = pd.concat([self.df, new_data]).tail(100) # keep recent history
        self.calculate_all()

    def calculate_all(self):
        self.add_ema(length=9)
        self.add_ema(length=21)
        self.add_rsi(length=14)
        self.add_bollinger_bands(length=20, std=2)
        return self.df
