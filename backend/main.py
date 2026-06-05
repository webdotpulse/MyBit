import time
import os
import secrets
import asyncio
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv, set_key

from backend.database import engine, Base, get_db
from backend.models import SystemEvent, TradeHistory, DailyStats
from backend.bot_engine import BotEngine

load_dotenv()

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Algorithmic Trading Bot")
security = HTTPBasic()
bot = BotEngine()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication Dependency
def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, os.getenv("WEB_USERNAME", "admin"))
    correct_password = secrets.compare_digest(credentials.password, os.getenv("WEB_PASSWORD", "securepassword"))
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- Configuration Endpoints ---

@app.get("/api/config")
def get_config(_=Depends(verify_credentials)):
    return {
        "BYBIT_API_KEY": os.getenv("BYBIT_API_KEY", ""),
        "BYBIT_API_SECRET": os.getenv("BYBIT_API_SECRET", ""),
        "BYBIT_TESTNET": os.getenv("BYBIT_TESTNET", "True"),
        "TRADING_PAIR": os.getenv("TRADING_PAIR", "AUTO"),
        "MAX_DAILY_DRAWDOWN": os.getenv("MAX_DAILY_DRAWDOWN", "50"),
        "DAILY_PROFIT_GOAL": os.getenv("DAILY_PROFIT_GOAL", "50"),
        "WEB_USERNAME": os.getenv("WEB_USERNAME", "admin"),
        "WEB_PASSWORD": os.getenv("WEB_PASSWORD", "securepassword")
    }

@app.post("/api/config")
async def update_config(request: Request, _=Depends(verify_credentials)):
    data = await request.json()
    env_file = ".env"

    # Update .env file using set_key
    for key, value in data.items():
        set_key(env_file, key, str(value))
        # Update current process environment
        os.environ[key] = str(value)

    # Reload bot configuration
    bot.reload_config()

    return {"status": "Configuration updated successfully"}

@app.get("/api/ws-token")
def get_ws_token(_=Depends(verify_credentials)):
    return {"token": os.getenv("WEB_PASSWORD", "securepassword")}

# --- Frontend Serving ---

# Get the base directory (one level up from backend)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.get("/")
def serve_index(_=Depends(verify_credentials)):
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))

@app.get("/app.js")
def serve_app_js(_=Depends(verify_credentials)):
    return FileResponse(os.path.join(BASE_DIR, "frontend", "app.js"))

# --- REST Endpoints ---

@app.get("/api/status")
def get_status(_=Depends(verify_credentials)):
    return {
        "is_running": bot.is_running,
        "symbol": bot.symbol,
        "daily_pnl": bot.daily_pnl,
        "halted": bot.halt_until_next_day
    }

@app.post("/api/start")
def start_bot(_=Depends(verify_credentials)):
    if bot.is_running:
        return {"status": "Already running"}
    bot.start()
    return {"status": "Bot started"}

@app.post("/api/stop")
def stop_bot(_=Depends(verify_credentials)):
    if not bot.is_running:
        return {"status": "Already stopped"}
    bot.stop()
    return {"status": "Bot stopped gracefully"}

@app.post("/api/kill")
def kill_switch(_=Depends(verify_credentials)):
    bot.kill_switch()
    return {"status": "Kill switch activated, positions closed."}

@app.get("/api/balance")
def get_balance(_=Depends(verify_credentials)):
    balance = bot.connection.get_wallet_balance()
    return balance if balance else {"equity": 0, "availableBalance": 0}

@app.get("/api/positions")
def get_positions(_=Depends(verify_credentials)):
    positions = bot.connection.get_open_positions(bot.symbol)
    return positions

@app.get("/api/events")
def get_events(limit: int = 50, db: Session = Depends(get_db), _=Depends(verify_credentials)):
    events = db.query(SystemEvent).order_by(SystemEvent.timestamp.desc()).limit(limit).all()
    return events

@app.get("/api/history")
def get_trade_history(limit: int = 50, db: Session = Depends(get_db), _=Depends(verify_credentials)):
    history = db.query(TradeHistory).order_by(TradeHistory.timestamp.desc()).limit(limit).all()
    return history

@app.get("/api/klines")
def get_klines(_=Depends(verify_credentials)):
    """Returns the most recent kline data for the chart."""
    if bot.kline_data.empty:
        return []

    # Format the data for lightweight charts
    formatted_data = []
    for index, row in bot.kline_data.iterrows():
        formatted_data.append({
            "time": int(index.timestamp()),
            "open": row['open'],
            "high": row['high'],
            "low": row['low'],
            "close": row['close']
        })
    return formatted_data

# --- WebSockets for Live UI Updates ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Global loop set by startup event
main_loop = None

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()

# Hook up BotEngine callbacks to broadcast WS events
def on_bot_signal(data):
    if main_loop is None:
        return
    asyncio.run_coroutine_threadsafe(
        manager.broadcast({
            "type": "signal",
            "time": int(time.time() * 1000),
            "signal": data["signal"],
            "close": data["close"]
        }),
        main_loop
    )

def on_bot_kline(candle):
    if main_loop is None:
        return
    asyncio.run_coroutine_threadsafe(
        manager.broadcast({
            "type": "kline",
            "time": int(candle.get("start", 0)),
            "open": float(candle.get("open", 0)),
            "high": float(candle.get("high", 0)),
            "low": float(candle.get("low", 0)),
            "close": float(candle.get("close", 0))
        }),
        main_loop
    )

bot.on_signal = on_bot_signal
bot.on_kline = on_bot_kline

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    # Secure WebSocket with token/password passed in query params
    expected_token = os.getenv("WEB_PASSWORD", "securepassword")
    if token != expected_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
