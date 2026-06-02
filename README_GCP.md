# Deploying to Google Cloud Platform (Debian VM)

This guide provides instructions to deploy the High-Frequency Scalping Bot onto a fresh Debian VM on Google Cloud Platform.

## Step 1: Create a VM Instance
1. Go to the **Google Cloud Console**.
2. Navigate to **Compute Engine > VM instances**.
3. Click **Create Instance**.
4. Configure the following:
   * **Name**: `trading-bot-vm`
   * **Region/Zone**: Choose a region close to Bybit's servers (e.g., Tokyo or Singapore) to minimize latency.
   * **Machine configuration**: e2-micro or e2-small is sufficient.
   * **Boot disk**: Change the OS to **Debian** (version 11 or 12).
   * **Firewall**: Check **Allow HTTP traffic** (if you plan to use port 80 eventually) and **Allow HTTPS traffic**.
5. Click **Create**.

## Step 2: Open Firewall for Dashboard (Port 8000)
1. In GCP, go to **VPC network > Firewall**.
2. Click **Create Firewall Rule**.
3. **Name**: `allow-bot-dashboard`
4. **Targets**: All instances in the network
5. **Source IP ranges**: `0.0.0.0/0` (For production, restrict this to your personal IP address).
6. **Specified protocols and ports**: Check `tcp` and type `8000`.
7. Click **Create**.

## Step 3: Connect and Setup
1. SSH into your newly created VM instance from the GCP Console.
2. Clone your repository (or copy the files):
   ```bash
   git clone <your-repo-url> /opt/trading_bot
   cd /opt/trading_bot
   ```
3. Run the setup script to install dependencies and configure the environment:
   ```bash
   sudo chmod +x deployment/setup.sh
   sudo ./deployment/setup.sh
   ```

## Step 4: Configure Credentials
1. Navigate to the project directory:
   ```bash
   cd /opt/trading_bot
   ```
2. Create the environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your favorite editor
   ```
3. Add your Bybit API keys and configure the Web UI credentials. Save and exit.

## Step 5: Start the Background Service
1. Link the `systemd` service file to your system:
   ```bash
   sudo ln -s /opt/trading_bot/deployment/trading-bot.service /etc/systemd/system/trading-bot.service
   ```
2. Reload systemd daemons:
   ```bash
   sudo systemctl daemon-reload
   ```
3. Enable the service to start on boot:
   ```bash
   sudo systemctl enable trading-bot
   ```
4. Start the bot:
   ```bash
   sudo systemctl start trading-bot
   ```
5. Check the status:
   ```bash
   sudo systemctl status trading-bot
   ```

## Accessing the Dashboard
Open your web browser and navigate to:
`http://<YOUR_VM_EXTERNAL_IP>:8000`

Login using the `WEB_USERNAME` and `WEB_PASSWORD` defined in your `.env` file.
