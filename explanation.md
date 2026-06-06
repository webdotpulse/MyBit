# Bot Engine Explanation

This document explains in detail how the algorithmic trading bot makes its decisions regarding **what** trading pair to trade and **when** to buy or sell.

## 1. What to Trade (Asset Selection)
If the trading pair configuration is set to `AUTO`, the bot dynamically selects the most optimal pair to trade. The decision is made within the `select_best_trading_pair` function in `backend/bot_engine.py`.

The process works as follows:
- **Scan the Market:** The bot fetches the 24-hour ticker data for all linear perpetual contracts from Bybit.
- **Filter USDT Pairs:** It filters out any pairs that do not end in `USDT`.
- **Liquidity Check:** It checks the 24-hour trading volume (turnover). Any pair with a trading volume of less than $50,000,000 is ignored. This ensures high liquidity, preventing slippage and allowing for tighter spreads which are essential for scalping.
- **Calculate Volatility:** For each valid pair, it calculates volatility using the 24-hour high and low prices:
  `Volatility = (High - Low) / Low`
- **Scoring System:** It computes a unique score for each pair based on both volatility and volume:
  `Score = Volatility * log(Volume)`
- **Selection:** The bot selects the pair with the highest score. This formula favors highly volatile pairs (which present more trading opportunities) while guaranteeing sufficient volume. If it fails to find any pairs that match the criteria or encounters an API issue, it falls back to a safe default: `BTCUSDT`.

## 2. When to Trade (Signal Generation)
The logic for determining the exact timing to enter a trade is split between `backend/strategy.py` (`ScalpingStrategy.get_signal`) and a confirmation step in `backend/bot_engine.py`.

The strategy is a combination of **Mean Reversion** and **Momentum**:

### Indicator Setup
For the chosen trading pair, the bot continuously analyzes 1-minute candlestick data and calculates the following technical indicators:
- **RSI (Relative Strength Index - 14 periods):** To identify overbought or oversold conditions.
- **EMA (Exponential Moving Average - 9 and 21 periods):** To determine short-term trend direction.
- **Bollinger Bands (20 periods, 2 Standard Deviations):** To gauge volatility and extreme price deviations from the mean.

### BUY Condition (Going Long)
A `BUY` signal is generated when all of the following conditions are met simultaneously:
1. **Oversold Market:** The RSI is below 30.
2. **Price Deviation:** The current close price has dropped below or touched the Lower Bollinger Band.
3. **Upward Momentum:** The short-term trend is still bullish, meaning the 9-period EMA is strictly greater than the 21-period EMA.
4. **Order Book Confirmation (in `bot_engine.py`):** The order book imbalance must be greater than `0.2`. This means there is significantly more buying pressure (bids) than selling pressure (asks) on the book, confirming the reversal.

### SELL Condition (Going Short)
A `SELL` signal is generated when all of the following conditions are met simultaneously:
1. **Overbought Market:** The RSI is above 70.
2. **Price Deviation:** The current close price has risen above or touched the Upper Bollinger Band.
3. **Downward Momentum:** The short-term trend is bearish, meaning the 9-period EMA is strictly less than the 21-period EMA.
4. **Order Book Confirmation (in `bot_engine.py`):** The order book imbalance must be less than `-0.2`. This means selling pressure (asks) significantly outweighs buying pressure (bids) on the book, confirming the reversal.

### Position Sizing and Safety Checks
Before executing a market order based on a signal, the bot performs safety checks:
- It checks if an open position already exists (it currently does not average in or reverse positions; it waits for the exit).
- It sizes the position strictly based on the configured risk (e.g., 1% of the available balance).
- It verifies that the expected spread between the entry price and expected take profit covers the exchange fees (maker and taker fees). If the gross profit is not at least 50% larger than the trading fees, the trade is skipped entirely.

## 3. Recommended Capital and Realistic Daily Goals

When running a high-frequency scalping bot, setting appropriate capital and having realistic expectations are crucial for long-term success.

### Recommended Starting Capital
The ideal starting capital to let the bot trade with is generally between **$500 and $1,000**.
- **Minimum Order Sizes:** Bybit and other exchanges enforce minimum order sizes (often $10 to $20 depending on the asset). If your total capital is too small (e.g., $50), a 1% risk constraint means the bot can only use $0.50 per trade, which the exchange will reject.
- **Risk Management:** With $500 to $1,000, risking 1% to 2% of your account per trade allows the bot to meet the minimum order size requirements comfortably while keeping individual trade risk low enough to survive drawdowns.
- **Fee Coverage:** Larger positions ensure that the expected gross profit per trade significantly outweighs the fixed and proportional exchange fees (maker/taker fees).

### Realistic Daily Goals
In algorithmic trading, compounding small, consistent gains is far more sustainable than aiming for massive single-day returns.
- **Achievable Goal:** A realistic and achievable profit goal is around **0.5% to 1.5% per day**.
- **Why this works:** While 1% a day might sound small to some, it represents massive growth over time due to compounding. Scalping relies on making many small, highly probable trades.
- **Managing Expectations:** Aiming for higher daily returns (e.g., 5% or 10%) usually requires increasing the risk per trade or applying excessive leverage. This significantly increases the probability of hitting stop-losses and draining the account during periods of high market volatility or sideways movement. The bot's primary directive is capital preservation followed by steady, incremental growth.


### Optimal Settings for a $50 Starting Capital

Starting with $50 is considered below the generally recommended capital ($500-$1,000) for high-frequency scalping. The main challenges with a small balance are meeting the exchange's minimum order sizes and the impact of trading fees. However, if you want to start earning with a $50 balance, you need to adjust your settings proportionally to manage risk while allowing the bot to trade.

Here are the recommended settings for a $50 starting capital:

#### 1. TRADING_PAIR
**Recommendation:** `AUTO` (or a high-volume, low-price altcoin like `XRPUSDT`, `DOGEUSDT`, `ADAUSDT`)
- **Why:** Bybit has minimum order sizes. For Bitcoin (`BTCUSDT`) or Ethereum (`ETHUSDT`), the minimum order value might occasionally make it hard to execute small scalping trades with only $50, especially if leverage is kept conservative. Setting it to `AUTO` allows the bot to find the best pair dynamically. Alternatively, picking cheaper altcoins ensures your small balance can comfortably cover minimum order quantities.

#### 2. DAILY_PROFIT_GOAL
**Recommendation:** `0.5` to `0.75`
- **Why:** A realistic daily profit target for a scalping strategy is 0.5% to 1.5% of your total capital. For a $50 account:
  - 1% of $50 = $0.50
  - 1.5% of $50 = $0.75
- Setting the goal to $50 (which would be 100% daily profit) is highly unrealistic and extremely risky. Setting it to `$0.50` will realistically stop the bot once you've hit a sustainable daily target, protecting your gains.

#### 3. MAX_DAILY_DRAWDOWN
**Recommendation:** `2.5` to `5.0`
- **Why:** The maximum daily drawdown should act as a strict safety net. A common risk management rule is never to risk more than 5% to 10% of your account in a single day.
  - 5% of $50 = $2.50
  - 10% of $50 = $5.00
- Setting your max drawdown to `$2.50` ensures that if the market turns heavily against you, the bot will halt trading for the day, preserving the majority of your $50 capital for future trades.

#### Summary
Update your `.env` (or via the Web Dashboard) to:
```env
TRADING_PAIR=AUTO
MAX_DAILY_DRAWDOWN=2.5
DAILY_PROFIT_GOAL=0.5
```

**Note on Leverage:** Ensure your leverage settings on Bybit are appropriate. Higher leverage allows you to meet order size minimums easier with $50, but it drastically increases the chance of liquidation. Keep it conservative to survive short-term market volatility.
