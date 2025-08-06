from flask import Flask, render_template_string
from flask_socketio import SocketIO
import json, time, threading, re
from portfoliolive import totaltotal
from flask import request, jsonify
from aistocky import fetch_news, summarize_and_advise, load_portfolio, buy_stock, sell_stock
import datetime
from stockprice import get_stock_price
from save_live_data import record_portfolio_worth
from gains_calculator import get_gains_and_losses_data

app = Flask(__name__)
socketio = SocketIO(app)

# --- All backend routes are unchanged ---
@app.route("/portfolio", methods=["GET"])
def get_portfolio():
    portfolio_data = load_portfolio();
    for stock in portfolio_data:
        try: stock["current_price"] = get_stock_price(stock["ticker"], datetime.datetime.now())
        except Exception: stock["current_price"] = None
    return jsonify(portfolio_data)

@app.route("/trade", methods=["POST"])
def trade():
    data = request.json; action = data.get("action"); ticker = data.get("ticker", "").upper(); quantity = int(data.get("quantity", 0))
    if action not in ["buy", "sell"]: return jsonify({"error": "Invalid action"}), 400
    if not ticker or quantity <= 0: return jsonify({"error": "Ticker and positive quantity required"}), 400
    try:
        if action == "buy": buy_stock(ticker, quantity); return jsonify({"result": f"Bought {quantity} shares of {ticker}."})
        else:
            portfolio = load_portfolio(); owned_qty = sum(item["quantity"] for item in portfolio if item["ticker"] == ticker)
            if owned_qty < quantity: return jsonify({"error": f"Not enough shares to sell (owned: {owned_qty})."}), 400
            sell_stock(ticker, quantity); return jsonify({"result": f"Sold {quantity} shares of {ticker}."})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/aistock/advice", methods=["POST"])
def get_advice():
    data = request.json; ticker = data.get("ticker", "").upper()
    if not ticker: return jsonify({"error": "Ticker required"}), 400
    fetch_news(ticker); advice = summarize_and_advise(ticker); portfolio = load_portfolio()
    owned_quantity = sum(item["quantity"] for item in portfolio if item["ticker"] == ticker)
    return jsonify({"advice": advice, "owned_quantity": owned_quantity})

@app.route("/aistock/execute", methods=["POST"])
def execute_trade():
    data = request.json; ticker = data.get("ticker", "").upper(); advice = data.get("advice"); qty = int(data.get("qty", 0))
    portfolio = load_portfolio(); owned_quantity = sum(item["quantity"] for item in portfolio if item["ticker"] == ticker)
    if advice == "buy": buy_stock(ticker, qty); return jsonify({"result": f"Bought {qty} shares of {ticker}."})
    elif advice == "sell": sell_qty = min(qty, owned_quantity); sell_stock(ticker, sell_qty); return jsonify({"result": f"Sold {sell_qty} shares of {ticker}."})
    else: return jsonify({"result": "No action taken."})

@app.route("/history")
def history():
    try:
        with open("portfolio_live.json", "r") as f: raw = f.read()
        cleaned = "[" + ",".join(re.findall(r"\{.*?\}", raw, re.S)) + "]"; data = json.loads(cleaned)
        for d in data: d["timestamp"] = d["timestamp"].replace("T", " ")
        data.sort(key=lambda x: x["timestamp"]); return jsonify(data)
    except (FileNotFoundError, json.JSONDecodeError): return jsonify([])

@app.route("/gains")
def gains_page():
    gains_data = get_gains_and_losses_data()
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>Portfolio Gains & Losses</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; color: #333; } h1, h2 { color: #2c3e50; } a { color: #007bff; text-decoration: none; } a:hover { text-decoration: underline; } nav { margin-bottom: 20px; } .container { max-width: 900px; margin: auto; padding: 20px; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); } .summary-box { display: flex; justify-content: space-around; background-color: #ecf0f1; padding: 20px; border-radius: 5px; margin-bottom: 30px; text-align: center; } .summary-item h3 { margin: 0 0 5px 0; color: #7f8c8d; font-size: 16px; } .summary-item p { margin: 0; font-size: 24px; font-weight: bold; } table { width: 100%; border-collapse: collapse; margin-top: 20px; } th, td { padding: 12px; border: 1px solid #ddd; text-align: left; } th { background-color: #34495e; color: white; } tr:nth-child(even) { background-color: #f2f2f2; } .positive { color: #2ecc71; font-weight: bold; } .negative { color: #e74c3c; font-weight: bold; } td, p { transition: background-color 0.5s ease; }
        </style>
    </head>
    <body>
        <div class="container">
            <nav><a href="/">&larr; Back to Dashboard</a></nav>
            <h1>Portfolio Gains & Losses</h1>
            <h2>Overall Summary</h2>
            <div id="summary-container" class="summary-box">
                <div class="summary-item"><h3>Realized Gains</h3><p class="{{ 'positive' if data.summary.total_realized_gains|float >= 0 else 'negative' }}">${{ data.summary.total_realized_gains }}</p></div>
                <div class="summary-item"><h3>Unrealized Gains</h3><p class="{{ 'positive' if data.summary.total_unrealized_gains|float >= 0 else 'negative' }}">${{ data.summary.total_unrealized_gains }}</p></div>
                <div class="summary-item"><h3>Total Combined</h3><p class="{{ 'positive' if data.summary.total_combined_gains|float >= 0 else 'negative' }}">${{ data.summary.total_combined_gains }}</p></div>
            </div>
            <h2>Detailed Breakdown</h2>
            <table>
                <thead><tr><th>Ticker</th><th>Holdings</th><th>Avg. Buy Price</th><th>Current Price</th><th>Realized Gains</th><th>Unrealized Gains</th></tr></thead>
                <tbody id="details-table-body">
                    {% for stock in data.details %}
                    <tr><td><b>{{ stock.ticker }}</b></td><td>{{ stock.current_holdings }}</td><td>${{ stock.avg_buy_price }}</td><td>${{ stock.current_price }}</td><td class="{{ 'positive' if stock.realized_gains|float >= 0 else 'negative' }}">${{ stock.realized_gains }}</td><td class="{{ 'positive' if stock.unrealized_gains|float >= 0 else 'negative' }}">${{ stock.unrealized_gains }}</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <script src="https://cdn.socket.io/4.3.2/socket.io.min.js"></script>
        <script>
            const socket = io();
            socket.on('update_gains', function(data) { updateSummary(data.summary); updateDetailsTable(data.details); });
            function updateSummary(summary) { const container = document.getElementById('summary-container'); const realizedClass = parseFloat(summary.total_realized_gains.replace(/,/g, '')) >= 0 ? 'positive' : 'negative'; const unrealizedClass = parseFloat(summary.total_unrealized_gains.replace(/,/g, '')) >= 0 ? 'positive' : 'negative'; const combinedClass = parseFloat(summary.total_combined_gains.replace(/,/g, '')) >= 0 ? 'positive' : 'negative'; container.innerHTML = `<div class="summary-item"><h3>Realized Gains</h3><p class="${realizedClass}">$${summary.total_realized_gains}</p></div><div class="summary-item"><h3>Unrealized Gains</h3><p class="${unrealizedClass}">$${summary.total_unrealized_gains}</p></div><div class="summary-item"><h3>Total Combined</h3><p class="${combinedClass}">$${summary.total_combined_gains}</p></div>`; }
            function updateDetailsTable(details) { const tableBody = document.getElementById('details-table-body'); let newHtml = ''; details.forEach(stock => { const realizedClass = parseFloat(stock.realized_gains.replace(/,/g, '')) >= 0 ? 'positive' : 'negative'; const unrealizedClass = parseFloat(stock.unrealized_gains.replace(/,/g, '')) >= 0 ? 'positive' : 'negative'; newHtml += `<tr><td><b>${stock.ticker}</b></td><td>${stock.current_holdings}</td><td>$${stock.avg_buy_price}</td><td>$${stock.current_price}</td><td class="${realizedClass}">$${stock.realized_gains}</td><td class="${unrealizedClass}">$${stock.unrealized_gains}</td></tr>`; }); tableBody.innerHTML = newHtml; }
        </script>
    </body>
    </html>
    """, data=gains_data)


# --- MODIFIED: The main page template has the chart container fix ---
@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Live Portfolio Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; color: #333; }
        h1, h2 { color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }
        a { color: #007bff; text-decoration: none; } a:hover { text-decoration: underline; }
        nav { margin-bottom: 20px; font-size: 18px; }
        .container { max-width: 900px; margin: auto; padding: 20px; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .section { margin-bottom: 40px; }
        #value { font-size: 28px; font-weight: bold; color: #333; text-align: center; margin-bottom: 20px; }
        
        /* FIX: Define the chart container's size here */
        .chart-container { position: relative; height: 350px; width: 100%; }
        
        .time-buttons { text-align: center; margin: 20px 0; }
        .time-buttons button { margin: 0 5px; padding: 8px 15px; cursor: pointer; border: 1px solid #bdc3c7; background-color: #fff; border-radius: 5px; }
        .time-buttons button.active { background-color: #007bff; color: white; border-color: #007bff; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        th { background-color: #34495e; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        form { display: flex; flex-wrap: wrap; gap: 15px; align-items: center; background-color: #ecf0f1; padding: 20px; border-radius: 5px; }
        form label, form input, form select, form button { font-size: 14px; padding: 8px; border-radius: 5px; border: 1px solid #bdc3c7; }
        form button { background-color: #27ae60; color: white; border-color: #27ae60; cursor: pointer; }
        #tradeFeedback { margin-top: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <nav><a href="/gains">View Gains & Losses Report &rarr;</a></nav>
        <div class="section">
            <h1>Live Portfolio Dashboard</h1>
            <p id="value">Loading...</p>
            
            <!-- FIX: The canvas is now inside a container with a fixed height -->
            <div class="chart-container">
                <canvas id="valueChart"></canvas>
            </div>
            
            <div class="time-buttons">
                <button onclick="setRange('live')" class="active" id="liveBtn">Live</button>
                <button onclick="setRange('1h')" id="1hBtn">1 Hour</button>
                <button onclick="setRange('1d')" id="1dBtn">1 Day</button>
                <button onclick="setRange('1w')" id="1wBtn">1 Week</button>
            </div>
        </div>
        <!-- ... The rest of your HTML sections are unchanged ... -->
        <div class="section"><h2>Your Portfolio</h2><table id="portfolioTable"><thead><tr><th>Ticker</th><th>Quantity</th><th>Buy Price</th><th>Current Price</th></tr></thead><tbody></tbody></table></div>
        <div class="section"><h2>AI Stock Advisor</h2><form id="aiAdvisorForm" onsubmit="return false;"><input id="tickerInput" placeholder="Enter ticker (e.g., AAPL)" style="text-transform: uppercase;" /><button type="button" id="getAdviceBtn">Get Advice</button></form><div id="adviceResult" style="margin-top: 15px; font-weight: bold;"></div><div id="tradeControls" style="display:none; margin-top:10px;"><label>Quantity: <input type="number" id="qtyInput" min="1" /></label><button type="button" id="executeBtn">Execute Trade</button></div><div id="tradeResult" style="margin-top: 10px; color: green; font-weight: bold;"></div></div>
        <div class="section"><h2>Manual Trade</h2><form id="tradeForm"><label>Action: <select id="actionSelect"><option value="buy">Buy</option><option value="sell">Sell</option></select></label><label>Ticker: <input type="text" id="tradeTicker" style="text-transform: uppercase;" required /></label><label>Quantity: <input type="number" id="tradeQuantity" min="1" required /></label><button type="submit">Execute Trade</button></form><div id="tradeFeedback"></div></div>
    </div>

    <script src="https://cdn.socket.io/4.3.2/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/moment@2.29.4/moment.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-moment@1.0.0/dist/chartjs-adapter-moment.min.js"></script>
    
    <script>
    const ctx = document.getElementById('valueChart').getContext('2d');
    let liveData = [], fullHistory = [], currentRange = 'live';
    const chart = new Chart(ctx, {
        type: 'line', data: { datasets: [{ label: 'Portfolio Value', data: [], fill: true, tension: 0, pointRadius: 0, pointHoverRadius: 6, segment: { borderColor: ctx => ctx.p1.parsed.y >= 0 ? 'rgba(0, 200, 0, 1)' : 'rgba(200, 0, 0, 1)', backgroundColor: ctx => ctx.p1.parsed.y >= 0 ? 'rgba(0, 200, 0, 0.2)' : 'rgba(200, 0, 0, 0.2)' } }] },
        options: {
            scales: { x: { type: 'time', time: { tooltipFormat: 'HH:mm:ss', displayFormats: { second: 'HH:mm:ss', minute: 'HH:mm', hour: 'HH:mm', day: 'MMM DD' } }, title: { display: true, text: 'Time' } }, y: { beginAtZero: false, title: { display: true, text: 'Value ($)' } } },
            plugins: { legend: { display: true } },
            animation: { duration: 300 }, // Restored smooth animation
            responsive: true,
            maintainAspectRatio: false // This is key when using a container div
        }
    });

    async function loadHistoricalData() {
        try { const res = await fetch('/history'); const data = await res.json(); fullHistory = data.map(d => ({ x: moment(d.timestamp), y: d.total_worth })); } catch (err) { console.error('Failed to load historical data:', err); }
    }

    const socket = io();
    socket.on('update', function(data) {
        const now = moment(); document.getElementById('value').innerText = 'Total Portfolio Value: $' + data.value.toFixed(2);
        liveData.push({x: now, y: data.value}); if(liveData.length > 20) { liveData.shift(); }
        if (currentRange === 'live') { chart.data.datasets[0].data = liveData; chart.update(); }
        updatePortfolioPrices();
    });

    function findClosestDataPoint(targetTime, history, maxDiff) {
        if (!history || history.length === 0) return null; let closest = null; let minDiff = maxDiff; 
        for (const point of history) { const diff = Math.abs(targetTime.diff(point.x)); if (diff < minDiff) { minDiff = diff; closest = point; } }
        return closest;
    }

    function setRange(range) {
        currentRange = range; document.querySelectorAll('.time-buttons button').forEach(btn => btn.classList.remove('active')); document.getElementById(range + 'Btn').classList.add('active');
        let chartData = []; const now = moment();
        if (range === 'live') { chartData = liveData; chart.options.scales.x.time.unit = 'second'; }
        else {
            if (range === '1h') { const startTime = now.clone().subtract(60, 'minutes'); chartData = fullHistory.filter(d => d.x.isAfter(startTime)); chart.options.scales.x.time.unit = 'minute'; }
            else if (range === '1d') {
                const startTime = now.clone().subtract(24, 'hours').startOf('hour'); const thirtyMinutes = 30 * 60 * 1000; chartData = [];
                for (let i = 0; i < 24; i++) { const targetTime = startTime.clone().add(i, 'hours'); const closestPoint = findClosestDataPoint(targetTime, fullHistory, thirtyMinutes); chartData.push({ x: targetTime, y: closestPoint ? closestPoint.y : null }); } // Use null for gaps
                chart.options.scales.x.time.unit = 'hour';
            } else if (range === '1w') {
                const startTime = now.clone().subtract(7, 'days').startOf('day'); const twelveHours = 12 * 60 * 60 * 1000; chartData = [];
                for (let i = 0; i < 7; i++) { const targetTime = startTime.clone().add(i, 'days'); const closestPoint = findClosestDataPoint(targetTime, fullHistory, twelveHours); chartData.push({ x: targetTime, y: closestPoint ? closestPoint.y : null }); } // Use null for gaps
                chart.options.scales.x.time.unit = 'day';
            }
        }
        chart.data.labels = []; chart.data.datasets[0].data = chartData; chart.update();
    }
    
    async function updatePortfolioPrices() {
        try {
            const res = await fetch('/portfolio'); const portfolio = await res.json(); const tbody = document.querySelector('#portfolioTable tbody'); tbody.innerHTML = '';
            portfolio.forEach(stock => { const tr = document.createElement('tr'); const currentPrice = stock.current_price ? `$${stock.current_price.toFixed(2)}` : "N/A"; tr.innerHTML = `<td><b>${stock.ticker}</b></td><td>${stock.quantity}</td><td>$${stock.price.toFixed(2)}</td><td>${currentPrice}</td>`; tbody.appendChild(tr); });
        } catch (err) { console.error("Failed to update portfolio prices", err); }
    }
    
    
    // --- AI ADVISOR LOGIC ---
    const tickerInput = document.getElementById('tickerInput');
    const getAdviceBtn = document.getElementById('getAdviceBtn');
    const adviceResult = document.getElementById('adviceResult');
    const tradeControls = document.getElementById('tradeControls');
    const qtyInput = document.getElementById('qtyInput');
    const executeBtn = document.getElementById('executeBtn');
    const tradeResult = document.getElementById('tradeResult');
    let currentAdvice = null, currentTicker = null, ownedQuantity = 0;

    getAdviceBtn.onclick = async () => {
        const ticker = tickerInput.value.trim().toUpperCase();
        if (!ticker) { alert("Please enter a ticker symbol."); return; }
        adviceResult.textContent = "Loading advice...";
        tradeControls.style.display = "none";
        tradeResult.textContent = "";
        qtyInput.value = "";
        try {
            const response = await fetch('/aistock/advice', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ticker}) });
            const data = await response.json();
            if (data.error) { adviceResult.textContent = "Error: " + data.error; return; }
            currentAdvice = data.advice; currentTicker = ticker; ownedQuantity = data.owned_quantity;
            adviceResult.textContent = `AI Advice for ${ticker}: ${currentAdvice.toUpperCase()}. You own ${ownedQuantity} shares.`;
            if (currentAdvice === "buy" || (currentAdvice === "sell" && ownedQuantity > 0)) {
                tradeControls.style.display = "block";
                qtyInput.min = 1;
                qtyInput.max = (currentAdvice === "sell") ? ownedQuantity : null;
            } else { tradeControls.style.display = "none"; }
        } catch (err) { adviceResult.textContent = "Failed to fetch advice."; }
    };

    executeBtn.onclick = async () => {
        const qty = parseInt(qtyInput.value);
        if (!qty || qty < 1) { alert("Please enter a valid quantity."); return; }
        if (currentAdvice === "sell" && qty > ownedQuantity) { alert(`You cannot sell more than you own (${ownedQuantity}).`); return; }
        tradeResult.textContent = "Executing trade...";
        try {
            const response = await fetch('/aistock/execute', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ticker: currentTicker, advice: currentAdvice, qty}) });
            const data = await response.json();
            tradeResult.textContent = data.result;
            tradeControls.style.display = "none";
            adviceResult.textContent = "";
            qtyInput.value = "";
            await updatePortfolioPrices();
        } catch (err) { tradeResult.textContent = "Trade execution failed."; }
    };
    
    // --- MANUAL TRADE LOGIC ---
    const tradeForm = document.getElementById('tradeForm');
    const tradeFeedback = document.getElementById('tradeFeedback');
    tradeForm.addEventListener('submit', async e => {
        e.preventDefault();
        const action = document.getElementById('actionSelect').value;
        const ticker = document.getElementById('tradeTicker').value.trim().toUpperCase();
        const quantity = parseInt(document.getElementById('tradeQuantity').value);
        if (!ticker || quantity < 1) { alert("Please enter valid ticker and quantity."); return; }
        tradeFeedback.style.color = "black";
        tradeFeedback.textContent = "Processing...";
        try {
            const res = await fetch('/trade', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action, ticker, quantity}) });
            const data = await res.json();
            if (res.ok) {
                tradeFeedback.style.color = "green";
                tradeFeedback.textContent = data.result;
                await updatePortfolioPrices();
            } else {
                tradeFeedback.style.color = "red";
                tradeFeedback.textContent = data.error || "Trade failed";
            }
        } catch (err) { tradeFeedback.style.color = "red"; tradeFeedback.textContent = "Trade failed: " + err.message; }
    });

    // --- INITIAL DATA LOAD ---
    loadHistoricalData().then(() => setRange('live'));
    updatePortfolioPrices();
    </script>
</body>
</html>
    """)
def combined_updates():
    last_10s = time.time()
    last_60s = time.time()
    
    while True:
        now = time.time()

        # 10-second task
        if now - last_10s >= 10:
            value = totaltotal()
            socketio.emit('update', {'value': value})
            last_10s = now

        # 60-second task 
        if now - last_60s >= 60:
            record_portfolio_worth()
            last_60s = now

        time.sleep(1) 
if __name__ == "__main__":
    threading.Thread(target=combined_updates, daemon=True).start()
   
    socketio.run(app, debug=True,port=8080)