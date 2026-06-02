import pandas as pd
import logging

logger = logging.getLogger(__name__)

class ScalpingStrategy:
    def __init__(self, maker_fee=0.0002, taker_fee=0.0005, risk_per_trade=0.01, stop_loss_pct=0.005, take_profit_pct=0.01):
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.risk_per_trade = risk_per_trade # % of capital
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def evaluate_fees(self, entry_price, expected_exit_price):
        """
        Check if the spread between entry and expected exit covers the fees.
        Assume taker fee for entry (market order to guarantee execution) and maker fee for exit (limit order).
        """
        fee_cost_pct = self.taker_fee + self.maker_fee
        gross_profit_pct = abs(expected_exit_price - entry_price) / entry_price

        # We need the gross profit to be strictly greater than fee cost
        return gross_profit_pct > (fee_cost_pct * 1.5) # Provide a buffer of 50% over fees

    def calculate_position_size(self, available_balance, current_price):
        """Calculate position size based on risk per trade (e.g., 1% of balance)."""
        position_value = available_balance * self.risk_per_trade
        qty = position_value / current_price
        return qty

    def get_signal(self, latest_data):
        """
        Determines buy/sell/hold signal based on latest indicator data.
        Strategy: Mean reversion & momentum
        - Buy when RSI is oversold (< 30) and close price crosses below lower Bollinger Band, and EMA9 > EMA21.
        - Sell when RSI is overbought (> 70) and close price crosses above upper Bollinger Band, and EMA9 < EMA21.
        """
        if latest_data is None:
            return "HOLD"

        try:
            rsi = latest_data['RSI_14']
            ema9 = latest_data['EMA_9']
            ema21 = latest_data['EMA_21']
            close = latest_data['close']

            # Find BB column names dynamically as they change based on parameters
            bb_lower_col = [col for col in latest_data.index if col.startswith('BBL')][0]
            bb_upper_col = [col for col in latest_data.index if col.startswith('BBU')][0]

            bb_lower = latest_data[bb_lower_col]
            bb_upper = latest_data[bb_upper_col]

            if pd.isna(rsi) or pd.isna(ema9) or pd.isna(ema21) or pd.isna(bb_lower) or pd.isna(bb_upper):
                return "HOLD"

            # Long condition
            if rsi < 30 and close <= bb_lower and ema9 > ema21:
                return "BUY"

            # Short condition
            elif rsi > 70 and close >= bb_upper and ema9 < ema21:
                return "SELL"

        except Exception as e:
            logger.error(f"Error evaluating signal: {e}")

        return "HOLD"

    def calculate_stop_loss(self, entry_price, side):
        if side == "Buy":
            return entry_price * (1 - self.stop_loss_pct)
        elif side == "Sell":
            return entry_price * (1 + self.stop_loss_pct)
        return None

    def calculate_take_profit(self, entry_price, side):
        if side == "Buy":
            return entry_price * (1 + self.take_profit_pct)
        elif side == "Sell":
            return entry_price * (1 - self.take_profit_pct)
        return None
