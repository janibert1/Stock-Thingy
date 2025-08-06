from flask import Flask, render_template_string
from flask_socketio import SocketIO
import json, time, threading, re
from portfoliolive import totaltotal
from flask import request, jsonify
from aistocky import fetch_news, summarize_and_advise, load_portfolio, buy_stock, sell_stock
import datetime
from stockprice import get_stock_price
from save_live_data import record_portfolio_worth

app = Flask(__name__)
socketio = SocketIO(app)

@app.route("/portfolio", methods=["GET"])
def get_portfolio():
    portfolio_data = load_portfolio()

    # Add current price for each stock
    for stock in portfolio_data:
        try:
            stock["current_price"] = get_stock_price(stock["ticker"], datetime.datetime.now())
        except Exception:
            stock["current_price"] = None  # fallback if fetch fails

    return jsonify(portfolio_data)

@app.route("/trade", methods=["POST"])
def trade():
    data = request.json
    action = data.get("action")
    ticker = data.get("ticker", "").upper()
    quantity = int(data.get("quantity", 0))

    if action not in ["buy", "sell"]:
        return jsonify({"error": "Invalid action"}), 400
    if not ticker or quantity <= 0:
        return jsonify({"error": "Ticker and positive quantity required"}), 400

    try:
        if action == "buy":
            buy_stock(ticker, quantity)
            return jsonify({"result": f"Bought {quantity} shares of {ticker}."})
        else:
            # For selling, you might want to check owned shares before selling
            portfolio = load_portfolio()
            owned_qty = sum(item["quantity"] for item in portfolio if item["ticker"] == ticker)
            if owned_qty < quantity:
                return jsonify({"error": f"Not enough shares to sell (owned: {owned_qty})."}), 400
            sell_stock(ticker, quantity)
            return jsonify({"result": f"Sold {quantity} shares of {ticker}."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/aistock/advice", methods=["POST"])
def get_advice():
    data = request.json
    ticker = data.get("ticker", "").upper()
    if not ticker:
        return jsonify({"error": "Ticker required"}), 400

    fetch_news(ticker)
    advice = summarize_and_advise(ticker)
    
    portfolio = load_portfolio()
    owned_quantity = sum(item["quantity"] for item in portfolio if item["ticker"] == ticker)

    return jsonify({
        "advice": advice,
        "owned_quantity": owned_quantity
    })

@app.route("/aistock/execute", methods=["POST"])
def execute_trade():
    data = request.json
    ticker = data.get("ticker", "").upper()
    advice = data.get("advice")
    qty = int(data.get("qty", 0))

    portfolio = load_portfolio()
    owned_quantity = sum(item["quantity"] for item in portfolio if item["ticker"] == ticker)

    if advice == "buy":
        buy_stock(ticker, qty)
        return jsonify({"result": f"Bought {qty} shares of {ticker}."})
    elif advice == "sell":
        sell_qty = min(qty, owned_quantity)
        sell_stock(ticker, sell_qty)
        return jsonify({"result": f"Sold {sell_qty} shares of {ticker}."})
    else:
        return jsonify({"result": "No action taken."})

@app.route("/history")
def history():
    try:
        with open("portfolio_live.json", "r") as f:
            raw = f.read()

        # Extract all objects into a valid JSON array
        cleaned = "[" + ",".join(re.findall(r"\{.*?\}", raw, re.S)) + "]"
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = []

        # Sort by timestamp
        for d in data:
            d["timestamp"] = d["timestamp"].replace("T", " ")
        data.sort(key=lambda x: x["timestamp"])

        return jsonify(data)
    except FileNotFoundError:
        return jsonify([])

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Portfolio Live</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 20px;
    }
    #value {
      font-size: 24px;
      margin-bottom: 20px;
    }
    #valueChart {
      max-width: 700px;
      max-height: 350px;
    }
    .time-buttons {
      margin: 10px 0;
    }
    .time-buttons button {
      margin-right: 10px;
      padding: 5px 10px;
      cursor: pointer;
    }
    .time-buttons button.active {
      background-color: #007bff;
      color: white;
    }
  </style>
</head>
<body>
  <h1>Portfolio Live</h1>
  <p id="value">Loading...</p>
  <div class="time-buttons">
    <button onclick="setRange('live')" class="active" id="liveBtn">Live (20 points)</button>
    <button onclick="setRange('1m')" id="1mBtn">1 Minute</button>
    <button onclick="setRange('1h')" id="1hBtn">1 Hour</button>
    <button onclick="setRange('1d')" id="1dBtn">1 Day</button>
    <button onclick="setRange('1w')" id="1wBtn">1 Week</button>
  </div>
  <canvas id="valueChart"></canvas>

  <script src="https://cdn.socket.io/4.3.2/socket.io.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/moment@2.29.4/moment.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-moment@1.0.0/dist/chartjs-adapter-moment.min.js"></script>

  <script>
    const ctx = document.getElementById('valueChart').getContext('2d');
    let liveDataPoints = [];
    let liveLabels = [];
    let fullHistory = [];
    let currentRange = 'live';
    let lastHistoryUpdate = 0;

    const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [{
  label: 'Portfolio Value',
  data: [],
  fill: true,
  tension: 0,
  pointRadius: 0,
  pointHoverRadius: 6,
  borderColor: 'rgba(0, 200, 0, 1)',  // default
  backgroundColor: 'rgba(0, 200, 0, 0.2)', // default
  segment: {
    borderColor: ctx => ctx.p1.parsed.y >= 0 
      ? 'rgba(0, 200, 0, 1)' 
      : 'rgba(200, 0, 0, 1)',
    backgroundColor: ctx => ctx.p1.parsed.y >= 0 
      ? 'rgba(0, 200, 0, 0.2)' 
      : 'rgba(200, 0, 0, 0.2)',
  }
}]

  },
  options: {
    scales: {
      x: {
        type: 'time',
        time: {
          parser: 'HH:mm:ss',
          tooltipFormat: 'HH:mm:ss',
          unit: 'second',
          displayFormats: {
            second: 'HH:mm:ss'
          }
        },
        title: {
          display: true,
          text: 'Time'
        }
      },
      y: {
        beginAtZero: false,
        title: {
          display: true,
          text: 'Value ($)'
        }
      }
    },
    plugins: {
      legend: {
        display: true
      }
    },
    animation: {
      duration: 300
    },
    responsive: true,
    maintainAspectRatio: false
  }
});

    // Load historical data on page load
    async function loadHistoricalData() {
      try {
        const res = await fetch('/history');
        const data = await res.json();
        fullHistory = data.map(d => ({
          time: moment(d.timestamp),
          value: d.total_worth
        }));
        lastHistoryUpdate = Date.now();
      } catch (err) {
        console.error('Failed to load historical data:', err);
      }
    }

    // Refresh historical data periodically
    async function refreshHistoricalData() {
      await loadHistoricalData();
      // If we're not in live mode, update the current view
      if (currentRange !== 'live') {
        setRange(currentRange);
      }
    }

    const socket = io();

    socket.on('update', function(data) {
      const now = moment();
      const timeLabel = now.format('HH:mm:ss');

      document.getElementById('value').innerText = 'Total Value: $' + data.value.toFixed(2);

      // Always update live data arrays for when user switches back to live
      liveDataPoints.push(data.value);
      liveLabels.push(timeLabel);

      if(liveDataPoints.length > 20) {
        liveDataPoints.shift();
        liveLabels.shift();
      }

      // Update chart if in live mode
      if (currentRange === 'live') {
        chart.data.labels = [...liveLabels];
        chart.data.datasets[0].data = [...liveDataPoints];
        chart.update();
      } else {
        // For historical views, refresh data and update chart
        refreshHistoricalData();
      }

      // Update portfolio table with live prices
      updatePortfolioPrices();
    });

    // Update portfolio table prices
    async function updatePortfolioPrices() {
      try {
        const res = await fetch('/portfolio');
        const portfolio = await res.json();
        const tbody = document.querySelector('#portfolioTable tbody');
        
        // Update existing rows instead of replacing all
        const rows = tbody.querySelectorAll('tr');
        portfolio.forEach((stock, index) => {
          if (rows[index]) {
            const cells = rows[index].querySelectorAll('td');
            if (cells.length >= 4) {
              cells[3].textContent = stock.current_price ? "$" + stock.current_price.toFixed(2) : "N/A";
            }
          }
        });
      } catch (err) {
        console.error("Failed to update portfolio prices", err);
      }
    }

    function findClosestDataPoint(targetTime, history) {
      if (history.length === 0) return null;
      
      let closest = history[0];
      let minDiff = Math.abs(targetTime.diff(closest.time));
      
      for (let i = 1; i < history.length; i++) {
        const diff = Math.abs(targetTime.diff(history[i].time));
        if (diff < minDiff) {
          minDiff = diff;
          closest = history[i];
        }
      }
      
      return closest;
    }

    function setRange(range) {
      currentRange = range;
      
      // Update button states
      document.querySelectorAll('.time-buttons button').forEach(btn => btn.classList.remove('active'));
      document.getElementById(range + 'Btn').classList.add('active');

      if (range === 'live') {
        // Use live data - preserve the current live data
        chart.data.labels = [...liveLabels];
        chart.data.datasets[0].data = [...liveDataPoints];
        chart.options.scales.x.time.tooltipFormat = 'HH:mm:ss';
        chart.options.scales.x.time.displayFormats = { second: 'HH:mm:ss' };
        chart.update();
        return;
      }

      // Use historical data
      const now = moment();
      let stepSec = 1;
      let startTime;
      let timeFormat = 'HH:mm:ss';

      if (range === '1m') {
        startTime = now.clone().subtract(1, 'minutes');
        stepSec = 1;
        timeFormat = 'HH:mm:ss';
      } else if (range === '1h') {
        startTime = now.clone().subtract(1, 'hours');
        stepSec = 60;
        timeFormat = 'HH:mm:ss';
      } else if (range === '1d') {
        startTime = now.clone().subtract(1, 'days');
        stepSec = 60 * 60; // 1 hour steps
        timeFormat = 'MM-DD HH:mm';
      } else if (range === '1w') {
        startTime = now.clone().subtract(7, 'days');
        stepSec = 60 * 60 * 6; // 6 hour steps
        timeFormat = 'MM-DD HH:mm';
      }

      let labels = [];
      let values = [];
      let lastValue = 0;

      // For 1d and 1w, align to hour boundaries
      if (range === '1d' || range === '1w') {
        // Start from the hour boundary
        startTime.startOf('hour');
        
        for (let t = startTime.clone(); t.isSameOrBefore(now); t.add(stepSec, 'seconds')) {
          // Find the closest data point to this time
          const closest = findClosestDataPoint(t, fullHistory);
          if (closest) {
            lastValue = closest.value;
          }
          
          labels.push(t.format(timeFormat));
          values.push(lastValue);
        }
      } else {
        // For shorter ranges, use the original logic
        for (let t = startTime.clone(); t.isBefore(now); t.add(stepSec, 'seconds')) {
          const candidates = fullHistory.filter(d => d.time.isSameOrBefore(t));
          if (candidates.length > 0) {
            lastValue = candidates[candidates.length - 1].value;
          }
          labels.push(t.format(timeFormat));
          values.push(lastValue);
        }
      }

      chart.data.labels = labels;
      chart.data.datasets[0].data = values;
      chart.options.scales.x.time.tooltipFormat = timeFormat;
      chart.options.scales.x.time.displayFormats = { 
        second: timeFormat,
        minute: timeFormat,
        hour: timeFormat,
        day: timeFormat
      };
      chart.update();
    }

    // Initialize
    loadHistoricalData();
  </script>
  
  <div style="margin-top: 40px;">
    <h2>AI Stock Advisor</h2>
    <input id="tickerInput" placeholder="Enter ticker symbol" style="text-transform: uppercase;" />
    <button id="getAdviceBtn">Get Advice</button>

    <div id="adviceResult" style="margin-top: 15px; font-weight: bold;"></div>

    <div id="tradeControls" style="display:none; margin-top:10px;">
      <label>Quantity: <input type="number" id="qtyInput" min="1" /></label>
      <button id="executeBtn">Execute Trade</button>
    </div>

    <div id="tradeResult" style="margin-top: 10px; color: green; font-weight: bold;"></div>
  </div>

  <script>
    const tickerInput = document.getElementById('tickerInput');
    const getAdviceBtn = document.getElementById('getAdviceBtn');
    const adviceResult = document.getElementById('adviceResult');
    const tradeControls = document.getElementById('tradeControls');
    const qtyInput = document.getElementById('qtyInput');
    const executeBtn = document.getElementById('executeBtn');
    const tradeResult = document.getElementById('tradeResult');

    let currentAdvice = null;
    let currentTicker = null;
    let ownedQuantity = 0;

    getAdviceBtn.onclick = async () => {
      const ticker = tickerInput.value.trim().toUpperCase();
      if (!ticker) {
        alert("Please enter a ticker symbol.");
        return;
      }

      adviceResult.textContent = "Loading advice...";
      tradeControls.style.display = "none";
      tradeResult.textContent = "";
      qtyInput.value = "";

      try {
        const response = await fetch('/aistock/advice', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ticker})
        });

        const data = await response.json();
        if (data.error) {
          adviceResult.textContent = "Error: " + data.error;
          return;
        }

        currentAdvice = data.advice;
        currentTicker = ticker;
        ownedQuantity = data.owned_quantity;

        adviceResult.textContent = `AI Advice for ${ticker}: ${currentAdvice.toUpperCase()}. You own ${ownedQuantity} shares.`;

        if (currentAdvice === "buy") {
          tradeControls.style.display = "block";
          qtyInput.min = 1;
        } else if (currentAdvice === "sell" && ownedQuantity > 0) {
          tradeControls.style.display = "block";
          qtyInput.min = 1;
          qtyInput.max = ownedQuantity;
        } else {
          tradeControls.style.display = "none";
        }
      } catch (err) {
        adviceResult.textContent = "Failed to fetch advice.";
      }
    };

    executeBtn.onclick = async () => {
      const qty = parseInt(qtyInput.value);
      if (!qty || qty < 1) {
        alert("Please enter a valid quantity.");
        return;
      }

      if (currentAdvice === "sell" && qty > ownedQuantity) {
        alert(`You cannot sell more than you own (${ownedQuantity}).`);
        return;
      }

      tradeResult.textContent = "Executing trade...";
      try {
        const response = await fetch('/aistock/execute', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ticker: currentTicker, advice: currentAdvice, qty})
        });
        const data = await response.json();
        tradeResult.textContent = data.result;
        tradeControls.style.display = "none";
        adviceResult.textContent = "";
        qtyInput.value = "";
      } catch (err) {
        tradeResult.textContent = "Trade execution failed.";
      }
    };
  </script>

  <h2>Your Portfolio</h2>
  <table id="portfolioTable" border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; max-width: 700px;">
    <thead>
      <tr>
        <th>Ticker</th>
        <th>Quantity</th>
        <th>Buy Price (USD)</th>
        <th>Current Price (USD)</th>
      </tr>
    </thead>
    <tbody>
      <!-- Portfolio rows inserted here -->
    </tbody>
  </table>

  <h2>Buy / Sell Stocks</h2>
  <form id="tradeForm">
    <label>
      Action:
      <select id="actionSelect">
        <option value="buy">Buy</option>
        <option value="sell">Sell</option>
      </select>
    </label>
    <label>
      Ticker:
      <input type="text" id="tradeTicker" style="text-transform: uppercase;" required />
    </label>
    <label>
      Quantity:
      <input type="number" id="tradeQuantity" min="1" required />
    </label>
    <button type="submit">Execute Trade</button>
  </form>

  <div id="tradeFeedback" style="margin-top: 10px; font-weight: bold; color: green;"></div>

  <script>
    async function loadPortfolio() {
      try {
        const res = await fetch('/portfolio');
        const portfolio = await res.json();
        const tbody = document.querySelector('#portfolioTable tbody');
        tbody.innerHTML = '';
        portfolio.forEach(stock => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${stock.ticker}</td>
            <td>${stock.quantity}</td>
            <td>$${stock.price.toFixed(2)}</td>
            <td>${stock.current_price ? "$" + stock.current_price.toFixed(2) : "N/A"}</td>
          `;
          tbody.appendChild(tr);
        });
      } catch (err) {
        console.error("Failed to load portfolio", err);
      }
    }

    const tradeForm = document.getElementById('tradeForm');
    const tradeFeedback = document.getElementById('tradeFeedback');

    tradeForm.addEventListener('submit', async e => {
      e.preventDefault();

      const action = document.getElementById('actionSelect').value;
      const ticker = document.getElementById('tradeTicker').value.trim().toUpperCase();
      const quantity = parseInt(document.getElementById('tradeQuantity').value);

      if (!ticker || quantity < 1) {
        alert("Please enter valid ticker and quantity.");
        return;
      }

      tradeFeedback.style.color = "black";
      tradeFeedback.textContent = "Processing...";

      try {
        const res = await fetch('/trade', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({action, ticker, quantity})
        });
        const data = await res.json();

        if (res.ok) {
          tradeFeedback.style.color = "green";
          tradeFeedback.textContent = data.result;
          await loadPortfolio();
        } else {
          tradeFeedback.style.color = "red";
          tradeFeedback.textContent = data.error || "Trade failed";
        }
      } catch (err) {
        tradeFeedback.style.color = "red";
        tradeFeedback.textContent = "Trade failed: " + err.message;
      }
    });

    // Load portfolio on page load
    loadPortfolio();
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