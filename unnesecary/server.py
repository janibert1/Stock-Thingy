from flask import Flask, render_template_string
from flask_socketio import SocketIO
import json, time, threading
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

@app.route("/portfolio", methods=["GET"])
def portfolio():
    portfolio_data = load_portfolio()
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


@app.route("/")
def index():
    return render_template_string("""
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
  </style>
</head>
<body>
  <h1>Portfolio Live</h1>
  <p id="value">Loading...</p>
  <canvas id="valueChart"></canvas>

  <script src="https://cdn.socket.io/4.3.2/socket.io.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/moment@2.29.4/moment.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-moment@1.0.0/dist/chartjs-adapter-moment.min.js"></script>

  <script>
    const ctx = document.getElementById('valueChart').getContext('2d');
    const dataPoints = [];
    const labels = [];

    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Portfolio Value',
          data: dataPoints,
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 6,
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

    const socket = io();

    socket.on('update', function(data) {
      const now = moment(); // current time with moment.js
      const timeLabel = now.format('HH:mm:ss');

      document.getElementById('value').innerText = 'Total Value: $' + data.value.toFixed(2);

      dataPoints.push(data.value);
      labels.push(timeLabel);

      if(dataPoints.length > 20) {
        dataPoints.shift();
        labels.shift();
      }

      chart.update();
    });
    
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
        await loadPortfolio(); // Refresh portfolio table after trade
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

def background_updates():
    while True:
        value = totaltotal()
        record_portfolio_worth()
        socketio.emit('update', {'value': value})
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=background_updates, daemon=True).start()
    socketio.run(app, debug=True, port=8080)
