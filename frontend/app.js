// Configuration
const API_BASE = '/api';
let WS_URL = '';

// UI Elements
const els = {
    status: document.getElementById('status-text'),
    btnStart: document.getElementById('btn-start'),
    btnStop: document.getElementById('btn-stop'),
    btnKill: document.getElementById('btn-kill'),
    valEquity: document.getElementById('val-equity'),
    valAvailable: document.getElementById('val-available'),
    valDailyPnl: document.getElementById('val-dailypnl'),
    pnlProgress: document.getElementById('pnl-progress'),
    positionsTbody: document.getElementById('positions-tbody'),
    historyTbody: document.getElementById('history-tbody'),
    logsContainer: document.getElementById('logs-container'),

    // Config Elements
    btnConfig: document.getElementById('btn-config'),
    configModal: document.getElementById('config-modal'),
    btnCloseConfig: document.getElementById('btn-close-config'),
    configForm: document.getElementById('config-form'),
    confApiKey: document.getElementById('conf-api-key'),
    confApiSecret: document.getElementById('conf-api-secret'),
    confPair: document.getElementById('conf-pair'),
    confTestnet: document.getElementById('conf-testnet'),
    confDrawdown: document.getElementById('conf-drawdown'),
    confProfit: document.getElementById('conf-profit'),
    confWebUser: document.getElementById('conf-web-user'),
    confWebPass: document.getElementById('conf-web-pass'),
};

// Initialize Chart
const chartProperties = {
    layout: {
        background: { type: 'solid', color: '#1F2937' },
        textColor: '#D1D5DB',
    },
    grid: {
        vertLines: { color: '#374151' },
        horzLines: { color: '#374151' },
    },
    crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
    },
    rightPriceScale: {
        borderColor: '#374151',
    },
    timeScale: {
        borderColor: '#374151',
        timeVisible: true,
    },
};

const chartContainer = document.getElementById('tvchart');
const chart = LightweightCharts.createChart(chartContainer, chartProperties);

// Pre-fetch historical klines
async function initChart() {
    const klines = await fetchAPI("/klines");
    if (klines && klines.length > 0) {
        candleSeries.setData(klines);
    }
}
initChart();

const candleSeries = chart.addCandlestickSeries({
    upColor: '#22c55e',
    downColor: '#ef4444',
    borderDownColor: '#ef4444',
    borderUpColor: '#22c55e',
    wickDownColor: '#ef4444',
    wickUpColor: '#22c55e',
});

// Markers array for trade entries/exits
let markers = [];

// API Calls
async function fetchAPI(endpoint, method = 'GET', body = null) {
    try {
        const options = {
            method: method,
            credentials: 'include',
            headers: {}
        };
        if (body) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        return await response.json();
    } catch (error) {
        console.error(`Error fetching ${endpoint}:`, error);
        return null;
    }
}

async function initWebSocketToken() {
    const data = await fetchAPI('/ws-token');
    if (data && data.token) {
        WS_URL = 'ws://' + window.location.host + '/ws?token=' + data.token;
        setupWebSocket();
    }
}

async function updateDashboard() {
    // Status
    const status = await fetchAPI('/status');
    if (status) {
        if (status.halted) {
            els.status.innerHTML = `<span class="text-yellow-500 font-bold">HALTED (Limit Reached)</span>`;
        } else if (status.is_running) {
            els.status.innerHTML = `<span class="text-green-500 font-bold">RUNNING</span> - Pair: ${status.symbol}`;
        } else {
            els.status.innerHTML = `<span class="text-gray-400 font-bold">STOPPED</span>`;
        }

        // Daily PnL
        const pnl = parseFloat(status.daily_pnl || 0);
        els.valDailyPnl.innerText = `$${pnl.toFixed(2)}`;
        els.valDailyPnl.className = `text-3xl font-bold ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`;

        // Progress bar (Assume $50 goal)
        const progress = Math.min(Math.max((pnl / 50) * 100, 0), 100);
        els.pnlProgress.style.width = `${progress}%`;
    }

    // Balance
    const balance = await fetchAPI('/balance');
    if (balance) {
        els.valEquity.innerText = parseFloat(balance.equity).toFixed(2);
        els.valAvailable.innerText = parseFloat(balance.availableBalance).toFixed(2);
    }

    // Positions
    const positions = await fetchAPI('/positions');
    if (positions) {
        els.positionsTbody.innerHTML = '';
        if (positions.length === 0) {
            els.positionsTbody.innerHTML = `<tr><td colspan="5" class="px-4 py-4 text-center text-gray-500">No open positions</td></tr>`;
        } else {
            positions.forEach(p => {
                if(parseFloat(p.size) > 0) {
                    const pnlClass = parseFloat(p.unrealisedPnl) >= 0 ? 'text-green-400' : 'text-red-400';
                    const tr = document.createElement('tr');
                    tr.className = "border-b border-gray-700";
                    tr.innerHTML = `
                        <td class="px-4 py-2 font-bold">${p.symbol}</td>
                        <td class="px-4 py-2 ${p.side === 'Buy' ? 'text-green-400' : 'text-red-400'}">${p.side}</td>
                        <td class="px-4 py-2">${p.size}</td>
                        <td class="px-4 py-2">${p.avgPrice}</td>
                        <td class="px-4 py-2 font-bold ${pnlClass}">${parseFloat(p.unrealisedPnl).toFixed(4)}</td>
                    `;
                    els.positionsTbody.appendChild(tr);
                }
            });
        }
    }

    // History
    const history = await fetchAPI('/history?limit=50');
    if (history) {
        els.historyTbody.innerHTML = '';
        if (history.length === 0) {
            els.historyTbody.innerHTML = `<tr><td colspan="4" class="px-2 py-4 text-center text-gray-500">No recent trades</td></tr>`;
        } else {
            history.forEach(t => {
                const pnlClass = parseFloat(t.realized_pnl) >= 0 ? 'text-green-400' : 'text-red-400';
                const time = new Date(t.timestamp).toLocaleTimeString();
                const tr = document.createElement('tr');
                tr.className = "border-b border-gray-700";
                tr.innerHTML = `
                    <td class="px-2 py-1">${time}</td>
                    <td class="px-2 py-1 font-bold">${t.symbol}</td>
                    <td class="px-2 py-1 ${t.side === 'Buy' ? 'text-green-400' : 'text-red-400'}">${t.side}</td>
                    <td class="px-2 py-1 font-bold ${pnlClass}">${parseFloat(t.realized_pnl).toFixed(4)}</td>
                `;
                els.historyTbody.appendChild(tr);
            });
        }
    }

    // Events
    const events = await fetchAPI('/events?limit=20');
    if (events && events.length > 0) {
        els.logsContainer.innerHTML = '';
        events.forEach(e => {
            const time = new Date(e.timestamp).toLocaleTimeString();
            let color = 'text-gray-300';
            if (e.event_type === 'ERROR' || e.event_type === 'KILL_SWITCH') color = 'text-red-400';
            if (e.event_type === 'WARNING') color = 'text-yellow-400';
            if (e.event_type === 'TRADE') color = 'text-blue-400';

            const div = document.createElement('div');
            div.innerHTML = `<span class="text-gray-500">[${time}]</span> <span class="${color} font-bold">[${e.event_type}]</span> ${e.message}`;
            els.logsContainer.appendChild(div);
        });
    }
}

// Event Listeners
els.btnStart.addEventListener('click', async () => {
    await fetchAPI('/start', 'POST');
    updateDashboard();
});

els.btnStop.addEventListener('click', async () => {
    await fetchAPI('/stop', 'POST');
    updateDashboard();
});

els.btnKill.addEventListener('click', async () => {
    if(confirm("Are you sure you want to ACTIVATE THE KILL SWITCH? This will market close all positions!")) {
        await fetchAPI('/kill', 'POST');
        updateDashboard();
    }
});

// Config Modal Logic
els.btnConfig.addEventListener('click', async () => {
    const config = await fetchAPI('/config');
    if (config) {
        els.confApiKey.value = config.BYBIT_API_KEY || '';
        els.confApiSecret.value = config.BYBIT_API_SECRET || '';
        els.confPair.value = config.TRADING_PAIR || 'AUTO';
        els.confTestnet.value = config.BYBIT_TESTNET || 'True';
        els.confDrawdown.value = config.MAX_DAILY_DRAWDOWN || '50';
        els.confProfit.value = config.DAILY_PROFIT_GOAL || '50';
        els.confWebUser.value = config.WEB_USERNAME || 'admin';
        els.confWebPass.value = config.WEB_PASSWORD || 'securepassword';
        els.configModal.classList.remove('hidden');
    }
});

els.btnCloseConfig.addEventListener('click', () => {
    els.configModal.classList.add('hidden');
});

els.configForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const newConfig = {
        BYBIT_API_KEY: els.confApiKey.value,
        BYBIT_API_SECRET: els.confApiSecret.value,
        TRADING_PAIR: els.confPair.value,
        BYBIT_TESTNET: els.confTestnet.value,
        MAX_DAILY_DRAWDOWN: els.confDrawdown.value,
        DAILY_PROFIT_GOAL: els.confProfit.value,
        WEB_USERNAME: els.confWebUser.value,
        WEB_PASSWORD: els.confWebPass.value
    };

    await fetchAPI('/config', 'POST', newConfig);
    els.configModal.classList.add('hidden');

    // Refresh WS token just in case password changed
    const data = await fetchAPI('/ws-token');
    if (data && data.token) {
        WS_URL = 'ws://' + window.location.host + '/ws?token=' + data.token;
        // Don't restart WS here as it will reconnect automatically or on next poll
    }
});

// WebSocket for Live Data
function setupWebSocket() {
    if (!WS_URL) return;
    const ws = new WebSocket(WS_URL);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);

            // Example handling of simulated kline data from backend broadcast
            if(data.type === 'kline') {
                candleSeries.update({
                    time: data.time / 1000,
                    open: data.open,
                    high: data.high,
                    low: data.low,
                    close: data.close
                });
            }

            if(data.type === 'signal') {
                // Add marker to chart
                markers.push({
                    time: data.time / 1000,
                    position: data.signal === 'BUY' ? 'belowBar' : 'aboveBar',
                    color: data.signal === 'BUY' ? '#22c55e' : '#ef4444',
                    shape: data.signal === 'BUY' ? 'arrowUp' : 'arrowDown',
                    text: data.signal
                });
                candleSeries.setMarkers(markers);
            }
        } catch(e) {}
    };

    ws.onclose = () => {
        console.log("WS Disconnected. Reconnecting in 5s...");
        setTimeout(setupWebSocket, 5000);
    };
}

// Init loop
setInterval(updateDashboard, 5000); // Poll REST APIs every 5 seconds
updateDashboard();
initWebSocketToken(); // Fetch token and then setup WS

// Handle window resize for chart
window.addEventListener('resize', () => {
    chart.applyOptions({ width: chartContainer.clientWidth });
});
