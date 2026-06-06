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
