# MyBit High-Frequency Scalping Bot

## Overview
This is a high-frequency algorithmic scalping bot for the Bybit V5 API, designed for efficiency and speed. It connects to Bybit using websockets and uses pandas-ta for technical analysis.

## Setup Instructions

### 1. Bybit Account and API Keys
To use this bot, you must create an account on Bybit. Once registered, you will need to generate API Keys:

1. Log into your Bybit account.
2. Go to **API Management** (under your profile icon).
3. Click **Create New Key**.
4. Select **System-generated API Keys** or **Auto-generated API Keys**.
5. Ensure you select the following permissions for Unified Trading:
   - Orders: Read/Write
   - Positions: Read/Write
   - Account: Read
6. Choose whether you want to use **Testnet** (for simulated trading) or **Mainnet** (for real trading). Testnet API keys can be created on the Bybit Testnet website (testnet.bybit.com).
7. Save your **API Key** and **API Secret**.

### 2. Configuration Panel
The bot includes a web-based dashboard and configuration panel.

Once you start the application, navigate to `http://<YOUR_IP>:8000` in your web browser.
Log in using the default credentials:
- **Username**: `admin`
- **Password**: `securepassword`

In the dashboard, click the **Settings** button to open the Configuration Panel. Here you can:
- Enter your **Bybit API Key** and **Bybit API Secret**.
- Toggle **Testnet** mode on or off.
- Change the **Trading Pair** (e.g., BTCUSDT).
- Set your **Max Daily Drawdown** and **Daily Profit Goal**.
- Update your **Web Dashboard Authentication** (Username and Password).

Click **Save** to apply your changes. The bot will automatically reload its configuration.

### Deployment
For deployment instructions to Google Cloud Platform, please read `README_GCP.md`.