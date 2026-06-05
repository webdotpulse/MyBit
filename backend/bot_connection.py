import os
import logging
from pybit.unified_trading import HTTP
from pybit.unified_trading import WebSocket as BybitWebSocket
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class BybitConnection:
    def __init__(self, testnet=True):
        self.api_key = os.getenv("BYBIT_API_KEY")
        self.api_secret = os.getenv("BYBIT_API_SECRET")
        self.testnet = testnet
        self.ws_private = None
        self.ws_public = None

        # REST Client
        self.session = HTTP(
            testnet=self.testnet,
            api_key=self.api_key,
            api_secret=self.api_secret,
        )

        # WebSocket Clients
        try:
            self.ws_private = BybitWebSocket(
                testnet=self.testnet,
                channel_type="private",
                api_key=self.api_key,
                api_secret=self.api_secret,
            )
        except Exception as e:
            logger.error(f"Failed to connect ws_private: {e}")

        try:
            self.ws_public = BybitWebSocket(
                testnet=self.testnet,
                channel_type="linear", # linear perp
            )
        except Exception as e:
            logger.error(f"Failed to connect ws_public: {e}")

    def get_wallet_balance(self, coin="USDT"):
        try:
            # When querying for total UTA balance, it is better not to restrict by coin
            # unless we only care about a specific coin's physical balance.
            # In a Unified Trading Account, `totalEquity` and `totalAvailableBalance`
            # provide the global USD value used for linear perps margin.
            response = self.session.get_wallet_balance(
                accountType="UNIFIED"
            )
            # Safely navigate the nested response structure
            if response.get("retCode") == 0:
                list_data = response.get("result", {}).get("list", [])
                if list_data:
                    account_data = list_data[0]
                    # Unified account level balances
                    total_equity = account_data.get("totalEquity")
                    total_available = account_data.get("totalAvailableBalance")

                    if total_equity is not None and total_available is not None:
                        return {
                            "equity": float(total_equity or 0),
                            "availableBalance": float(total_available or 0)
                        }

                    # Fallback to specific coin if total balances are absent
                    coins = account_data.get("coin", [])
                    for c in coins:
                        if c.get("coin") == coin:
                            return {
                                "equity": float(c.get("equity", 0)),
                                "availableBalance": float(c.get("availableToWithdraw", 0))
                            }
            logger.warning(f"Failed to fetch balance: {response.get('retMsg')}")
            return None
        except Exception as e:
            logger.error(f"Error fetching wallet balance: {e}")
            return None

    def get_tickers(self, category="linear"):
        try:
            response = self.session.get_tickers(category=category)
            if response.get("retCode") == 0:
                return response.get("result", {}).get("list", [])
            return []
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            return []

    def get_open_positions(self, symbol):
        try:
            response = self.session.get_positions(
                category="linear",
                symbol=symbol
            )
            if response.get("retCode") == 0:
                return response.get("result", {}).get("list", [])
            return []
        except Exception as e:
            logger.error(f"Error fetching open positions: {e}")
            return []

    def place_order(self, symbol, side, order_type, qty, price=None, stop_loss=None, take_profit=None):
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": order_type,
                "qty": str(qty),
                "timeInForce": "GTC",
            }
            if price and order_type == "Limit":
                params["price"] = str(price)
            if stop_loss:
                params["stopLoss"] = str(stop_loss)
            if take_profit:
                params["takeProfit"] = str(take_profit)

            response = self.session.place_order(**params)
            return response
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    def cancel_all_orders(self, symbol):
        try:
            response = self.session.cancel_all_orders(
                category="linear",
                symbol=symbol
            )
            return response
        except Exception as e:
            logger.error(f"Error canceling all orders: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    def close_all_positions(self, symbol):
        """Emergency kill switch method"""
        positions = self.get_open_positions(symbol)
        responses = []
        for pos in positions:
            size = float(pos.get("size", 0))
            if size > 0:
                side = pos.get("side")
                close_side = "Sell" if side == "Buy" else "Buy"
                resp = self.place_order(symbol, close_side, "Market", size)
                responses.append(resp)
        self.cancel_all_orders(symbol)
        return responses

    def subscribe_kline(self, symbol, interval, callback):
        if self.ws_public:
            self.ws_public.kline_stream(
                interval=interval,
                symbol=symbol,
                callback=callback
            )

    def subscribe_orderbook(self, symbol, depth, callback):
        if self.ws_public:
            self.ws_public.orderbook_stream(
                depth=depth,
                symbol=symbol,
                callback=callback
            )

    def subscribe_ticker(self, symbol, callback):
        if self.ws_public:
            self.ws_public.ticker_stream(
                symbol=symbol,
                callback=callback
            )

    def subscribe_execution(self, callback):
        if self.ws_private:
            self.ws_private.execution_stream(callback=callback)

    def subscribe_wallet(self, callback):
        if self.ws_private:
            self.ws_private.wallet_stream(callback=callback)
