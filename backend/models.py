from sqlalchemy import Column, Integer, String, Float, DateTime
from backend.database import Base
import datetime

class TradeHistory(Base):
    __tablename__ = "trade_history"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    side = Column(String) # Buy or Sell
    entry_price = Column(Float)
    exit_price = Column(Float)
    qty = Column(Float)
    realized_pnl = Column(Float)
    fee_paid = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class DailyStats(Base):
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True) # YYYY-MM-DD
    total_pnl = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    max_drawdown_reached = Column(Integer, default=0) # 0 or 1 boolean flag

class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String) # e.g., "INFO", "WARNING", "ERROR", "TRADE", "KILL_SWITCH"
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
