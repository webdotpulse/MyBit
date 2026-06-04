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

## Step 2: Open Firewall for Dashboard (Port 80)
1. In GCP, go to **VPC network > Firewall**.
2. Click **Create Firewall Rule**.
3. **Name**: `allow-bot-dashboard`
4. **Targets**: All instances in the network
5. **Source IP ranges**: `0.0.0.0/0` (For production, restrict this to your personal IP address).
6. **Specified protocols and ports**: Check `tcp` and type `80`.
7. Click **Create**.

## Step 3: Connect and Setup
1. SSH into your newly created VM instance from the GCP Console.
2. Clone your repository (or copy the files):
   ```bash
   git clone https://github.com/webdotpulse/MyBit /opt/trading_bot
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
`http://<YOUR_VM_EXTERNAL_IP>`

Login using the `WEB_USERNAME` and `WEB_PASSWORD` defined in your `.env` file.

## Resetting the Cloud VM
If you need to start fresh or resolve issues without completely deleting and recreating your VM instance, you can simply reset it.

**Option 1: Using the GCP Console**
1. Go to the **Google Cloud Console**.
2. Navigate to **Compute Engine > VM instances**.
3. Check the box next to your instance (`trading-bot-vm`).
4. Click the **RESET** button at the top of the page. This performs a hard reset (similar to pressing the reset button on a physical computer).

**Option 2: Using the gcloud CLI**
```bash
gcloud compute instances reset trading-bot-vm --zone=<YOUR_VM_ZONE>
```

**Option 3: Restarting from inside the VM**
If you still have SSH access and just want to restart the OS gracefully:
```bash
sudo /sbin/reboot
```

After the VM comes back online, the `trading-bot` service will start automatically if you enabled it in Step 5.

## Updating the Application
When new updates are pushed to the main repository, you can update your running bot without recreating the VM.

1. SSH into your VM instance.
2. Navigate to the project directory:
   ```bash
   cd /opt/trading_bot
   ```
3. Pull the latest changes from the repository:
   ```bash
   sudo git pull origin main
   ```
4. If there are new dependencies, activate the virtual environment and install them:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. Restart the bot service to apply the changes:
   ```bash
   sudo systemctl restart trading-bot
   ```
