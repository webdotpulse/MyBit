import os
import time
import pandas as pd
import logging
from datetime import datetime, timezone
from backend.bot_connection import BybitConnection
from backend.strategy import ScalpingStrategy
from backend.indicators import Indicators
from backend.database import SessionLocal
from backend.models import TradeHistory, DailyStats, SystemEvent

logger = logging.getLogger(__name__)

class BotEngine:
    def __init__(self):
        self.symbol = os.getenv("TRADING_PAIR", "BTCUSDT")
        self.max_daily_drawdown = float(os.getenv("MAX_DAILY_DRAWDOWN", 50))
        self.daily_profit_goal = float(os.getenv("DAILY_PROFIT_GOAL", 50))

        self.connection = BybitConnection(testnet=True) # set to False for production
        self.strategy = ScalpingStrategy()

        # Initialize dataframe for indicators
        self.kline_data = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume', 'turnover'])
        self.indicators = Indicators(self.kline_data)

        self.is_running = False
        self.halt_until_next_day = False
        self.daily_pnl = 0.0
        self.start_of_day_equity = None

        # UI callback hooks
        self.on_pnl_update = None
        self.on_signal = None
        self.ob_imbalance = 0
        self.on_kline = None

    def _log_event(self, event_type, message):
        logger.info(f"[{event_type}] {message}")
        try:
            db = SessionLocal()
            event = SystemEvent(event_type=event_type, message=message)
            db.add(event)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"DB Error: {e}")

    def update_daily_stats(self):
        """Calculates PnL for the current day to enforce drawdown limits."""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        db = SessionLocal()
        stats = db.query(DailyStats).filter(DailyStats.date == today).first()
        if not stats:
            stats = DailyStats(date=today, total_pnl=0.0)
            db.add(stats)
            db.commit()

        self.daily_pnl = stats.total_pnl
        db.close()

        if self.daily_pnl <= -self.max_daily_drawdown:
            self._log_event("WARNING", f"Max daily drawdown reached (${self.daily_pnl}). Halting bot until UTC midnight.")
            self.halt_until_next_day = True
            self.kill_switch()

        elif self.daily_pnl >= self.daily_profit_goal:
            self._log_event("INFO", f"Daily profit goal reached (${self.daily_pnl}). Halting bot until UTC midnight.")
            self.halt_until_next_day = True
            self.kill_switch()

        if self.on_pnl_update:
            self.on_pnl_update(self.daily_pnl)

    def handle_kline_message(self, message):
        """Callback for websocket kline stream."""
        if not self.is_running or self.halt_until_next_day:
            return

        data = message.get("data", [])
        if data:
            candle = data[0]
            # Convert string to float
            row = pd.DataFrame([{
                'open': float(candle['open']),
                'high': float(candle['high']),
                'low': float(candle['low']),
                'close': float(candle['close']),
                'volume': float(candle['volume']),
                'turnover': float(candle['turnover'])
            }], index=[pd.to_datetime(int(candle['start']), unit='ms')])

            # Update indicator dataframe correctly without duplicating same candle timestamps
            timestamp = pd.to_datetime(int(candle['start']), unit='ms')
            if not self.kline_data.empty and timestamp == self.kline_data.index[-1]:
                self.kline_data.loc[timestamp] = row.iloc[0]
                self.indicators.df = self.kline_data.copy()
                self.indicators.calculate_all()
            else:
                self.kline_data = pd.concat([self.kline_data, row]).tail(100)
                self.indicators.df = self.kline_data.copy()
                self.indicators.calculate_all()

            if hasattr(self, "on_kline") and self.on_kline:
                self.on_kline(candle)

            latest = self.indicators.get_latest()

            # Check strategy signal
            signal = self.strategy.get_signal(latest)

            # Combine with order book imbalance (e.g. require > 0.2 imbalance to confirm trend)
            confirmed_signal = "HOLD"
            if signal == "BUY" and self.ob_imbalance > 0.2:
                confirmed_signal = "BUY"
            elif signal == "SELL" and self.ob_imbalance < -0.2:
                confirmed_signal = "SELL"

            if self.on_signal:
                self.on_signal({"signal": confirmed_signal, "close": float(candle['close'])})

            if confirmed_signal in ["BUY", "SELL"]:
                self.execute_trade(confirmed_signal, float(candle['close']))

    def handle_orderbook_message(self, message):
        """Calculates orderbook imbalance."""
        data = message.get("data", {})
        bids = data.get("b", [])
        asks = data.get("a", [])

        bid_vol = sum(float(b[1]) for b in bids if len(b) > 1)
        ask_vol = sum(float(a[1]) for a in asks if len(a) > 1)

        total_vol = bid_vol + ask_vol
        if total_vol > 0:
            self.ob_imbalance = (bid_vol - ask_vol) / total_vol
        else:
            self.ob_imbalance = 0

    def handle_execution_message(self, message):
        """Callback for execution stream (fills, etc.)"""
        data = message.get("data", [])
        for exec_info in data:
            if exec_info.get("execType") == "Trade":
                symbol = exec_info.get("symbol")
                side = exec_info.get("side")
                qty = float(exec_info.get("execQty", 0))
                price = float(exec_info.get("execPrice", 0))
                fee = float(exec_info.get("execFee", 0))
                closed_pnl = float(exec_info.get("closedPnl", 0))

                self._log_event("TRADE", f"Executed {side} {qty} {symbol} @ {price}. PnL: {closed_pnl}")

                # Update DB
                try:
                    db = SessionLocal()
                    trade = TradeHistory(
                        symbol=symbol,
                        side=side,
                        entry_price=price,
                        exit_price=price,
                        qty=qty,
                        realized_pnl=closed_pnl,
                        fee_paid=fee
                    )
                    db.add(trade)

                    if closed_pnl != 0:
                        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                        stats = db.query(DailyStats).filter(DailyStats.date == today).first()
                        if stats:
                            stats.total_pnl += closed_pnl
                            stats.total_trades += 1

                    db.commit()
                    db.close()

                    if closed_pnl != 0:
                        self.update_daily_stats() # Recalculate and check limits
                except Exception as e:
                    logger.error(f"Error logging trade: {e}")

    def execute_trade(self, signal, current_price):
        """Executes trade if we don't have open positions and within limits."""
        # 1. Check open positions
        positions = self.connection.get_open_positions(self.symbol)
        has_open_position = any(float(p.get("size", 0)) > 0 for p in positions)

        if has_open_position:
            # For simplicity, don't average in or reverse. Just wait for exit.
            return

        # 2. Get Balance
        wallet = self.connection.get_wallet_balance()
        if not wallet or wallet['availableBalance'] <= 0:
            return

        # 3. Calculate Risk & Size
        qty = self.strategy.calculate_position_size(wallet['availableBalance'], current_price)
        qty = round(qty, 3) # adjust rounding based on symbol step size rules
        if qty <= 0:
            return

        # 4. Check Fees & Expected Spread
        # Scalping expects a quick exit. We estimate exit based on take profit.
        tp_price = self.strategy.calculate_take_profit(current_price, "Buy" if signal == "BUY" else "Sell")

        if not self.strategy.evaluate_fees(current_price, tp_price):
            self._log_event("INFO", f"Skipped trade: Spread doesn't cover fees.")
            return

        # 5. Calculate SL
        sl_price = self.strategy.calculate_stop_loss(current_price, "Buy" if signal == "BUY" else "Sell")

        # 6. Place Market Order
        # Format prices correctly for API (assuming typical 2 decimal places for USDT pairs)
        sl_price_str = f"{sl_price:.2f}"
        tp_price_str = f"{tp_price:.2f}"

        side = "Buy" if signal == "BUY" else "Sell"
        self._log_event("INFO", f"Placing {side} Market Order for {qty} {self.symbol}")
        res = self.connection.place_order(
            symbol=self.symbol,
            side=side,
            order_type="Market",
            qty=qty,
            stop_loss=sl_price_str,
            take_profit=tp_price_str
        )
        if res.get("retCode") != 0:
            self._log_event("ERROR", f"Order failed: {res.get('retMsg')}")

    def kill_switch(self):
        """Emergency stop: close all positions, cancel orders, halt bot."""
        self.is_running = False
        self._log_event("KILL_SWITCH", "Kill switch activated. Closing all positions and stopping bot.")
        self.connection.close_all_positions(self.symbol)

    def start(self):
        """Starts the bot and connects websockets."""
        if self.halt_until_next_day:
            # Check if it's a new day
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            db = SessionLocal()
            stats = db.query(DailyStats).filter(DailyStats.date == today).first()
            db.close()

            # If there's no stats for today or PnL is within limits, we can restart
            if not stats or (stats.total_pnl > -self.max_daily_drawdown and stats.total_pnl < self.daily_profit_goal):
                self.halt_until_next_day = False
            else:
                self._log_event("WARNING", "Cannot start. Daily limits are still in effect for today.")
                return

        self.is_running = True
        self._log_event("INFO", "Bot Engine Started")

        # Subscribe to public kline data (1 minute intervals for scalping)
        self.connection.subscribe_kline(self.symbol, "1", self.handle_kline_message)
        # Subscribe to orderbook depth 50
        if hasattr(self.connection, "subscribe_orderbook"):
            self.connection.subscribe_orderbook(self.symbol, 50, self.handle_orderbook_message)

        # Subscribe to private execution data
        self.connection.subscribe_execution(self.handle_execution_message)

        self.update_daily_stats()

    def stop(self):
        """Gracefully stops the bot without liquidating."""
        self.is_running = False
        self._log_event("INFO", "Bot Engine Stopped")
