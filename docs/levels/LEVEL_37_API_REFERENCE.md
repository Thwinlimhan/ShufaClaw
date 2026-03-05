# REST API Reference (Level 37)

## Base URL

```
http://localhost:8000  (Development)
https://api.yourbot.com  (Production)
```

## Authentication

All endpoints (except `/health` and `/webhook/tradingview`) require API key authentication.

**Header**:
```
Authorization: Bearer YOUR_API_KEY
```

**Example**:
```bash
curl -H "Authorization: Bearer demo_key" \
  https://api.yourbot.com/portfolio
```

## Rate Limiting

- Default: 100 requests per hour per API key
- Returns `429 Too Many Requests` when exceeded
- Rate limit resets every hour

## Endpoints

### Health Check

**GET** `/health`

Check API server status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-26T14:30:00"
}
```

---

### Portfolio

#### Get Portfolio

**GET** `/portfolio`

Get complete portfolio with current values.

**Response**:
```json
{
  "total_value": 58350.50,
  "positions": [
    {
      "symbol": "BTC",
      "amount": 0.5,
      "entry_price": 95000,
      "current_price": 97500,
      "value": 48750,
      "pnl": 1250,
      "pnl_percent": 2.63
    }
  ],
  "pnl_24h": 1250.50,
  "pnl_percent_24h": 2.19
}
```

#### Add Position

**POST** `/portfolio/position`

Add a new portfolio position.

**Parameters**:
- `symbol` (string, required): Coin symbol
- `amount` (float, required): Amount of coins
- `entry_price` (float, required): Entry price

**Example**:
```bash
curl -X POST \
  -H "Authorization: Bearer demo_key" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC","amount":0.5,"entry_price":95000}' \
  https://api.yourbot.com/portfolio/position
```

**Response**:
```json
{
  "success": true,
  "message": "Added 0.5 BTC at $95000"
}
```

---

### Alerts

#### Create Alert

**POST** `/alerts`

Create a price alert.

**Request Body**:
```json
{
  "symbol": "BTC",
  "target_price": 100000,
  "direction": "above",
  "message": "BTC hit 100k!"
}
```

**Response**:
```json
{
  "alert_id": 123,
  "symbol": "BTC",
  "target_price": 100000,
  "direction": "above",
  "active": true,
  "created_at": "2026-02-26T14:30:00"
}
```

#### Get Alerts

**GET** `/alerts`

Get all active alerts.

**Response**:
```json
[
  {
    "alert_id": 123,
    "symbol": "BTC",
    "target_price": 100000,
    "direction": "above",
    "active": true,
    "created_at": "2026-02-26T14:30:00"
  }
]
```

#### Delete Alert

**DELETE** `/alerts/{alert_id}`

Delete an alert.

**Response**:
```json
{
  "success": true,
  "message": "Alert 123 deleted"
}
```

---

### Trade Proposals

#### Generate Proposal

**POST** `/proposals`

Generate a complete trade proposal.

**Request Body**:
```json
{
  "symbol": "BTC",
  "timeframe": "4h",
  "risk_percent": 1.0
}
```

**Response**:
```json
{
  "proposal_id": "BTC_20260226_143022",
  "symbol": "BTC",
  "setup_type": "breakout",
  "direction": "LONG",
  "entry_price": 97970,
  "stop_loss": 94090,
  "target_1": 99470,
  "target_2": 101970,
  "target_3": 104470,
  "position_size_usd": 2577,
  "risk_amount": 100,
  "reward_risk_ratio": 2.58,
  "win_probability": 0.57,
  "expected_value": 0.47,
  "reasoning": "Breakout above resistance at $97,000..."
}
```

#### Get Proposals

**GET** `/proposals`

Get all active proposals.

**Response**:
```json
[
  {
    "proposal_id": "BTC_20260226_143022",
    "symbol": "BTC",
    "setup_type": "breakout",
    "direction": "LONG",
    "entry_price": 97970,
    "stop_loss": 94090,
    "target_2": 101970,
    "reward_risk_ratio": 2.58,
    "status": "pending"
  }
]
```

---

### Market Data

#### Get Market Data

**GET** `/market/{symbol}`

Get current market data for a symbol.

**Example**: `/market/BTC`

**Response**:
```json
{
  "symbol": "BTC",
  "price": 97500,
  "change_24h": 2.5,
  "volume_24h": 28500000000,
  "market_cap": 1900000000000
}
```

#### Get Top Coins

**GET** `/market/top/{limit}`

Get top coins by market cap.

**Example**: `/market/top/10`

**Response**:
```json
[
  {
    "rank": 1,
    "symbol": "BTC",
    "name": "Bitcoin",
    "price": 97500,
    "market_cap": 1900000000000,
    "change_24h": 2.5
  }
]
```

---

### Analysis

#### Analyze Symbol

**POST** `/analysis`

Get technical analysis for a symbol.

**Request Body**:
```json
{
  "symbol": "BTC",
  "timeframe": "4h"
}
```

**Response**:
```json
{
  "symbol": "BTC",
  "timeframe": "4h",
  "price": 97500,
  "rsi": 55,
  "trend": "up",
  "support": 95000,
  "resistance": 100000,
  "recommendation": "BUY"
}
```

---

### Journal

#### Add Journal Entry

**POST** `/journal`

Add a trading journal entry.

**Parameters**:
- `entry` (string, required): Journal text
- `symbol` (string, optional): Related symbol

**Example**:
```bash
curl -X POST \
  -H "Authorization: Bearer demo_key" \
  -H "Content-Type: application/json" \
  -d '{"entry":"Bought BTC at support","symbol":"BTC"}' \
  https://api.yourbot.com/journal
```

**Response**:
```json
{
  "success": true,
  "message": "Journal entry added"
}
```

#### Get Journal

**GET** `/journal?days=7`

Get journal entries from last N days.

**Response**:
```json
[
  {
    "id": 1,
    "entry": "Bought BTC at support",
    "symbol": "BTC",
    "created_at": "2026-02-26T14:30:00"
  }
]
```

---

### TradingView Webhook

**POST** `/webhook/tradingview`

Receive TradingView alerts.

**Headers**:
- `X-Webhook-Secret`: Your webhook secret

**Request Body**:
```json
{
  "symbol": "BTCUSDT",
  "action": "buy",
  "price": 97500,
  "strategy": "RSI Oversold",
  "timeframe": "4h",
  "message": "RSI crossed above 30"
}
```

**Response**:
```json
{
  "success": true,
  "action": "buy",
  "symbol": "BTCUSDT",
  "price": 97500
}
```

---

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Invalid API key"
}
```

### 404 Not Found

```json
{
  "detail": "Data not found for BTC"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Services not available"
}
```

---

## Python Client Example

```python
import requests

class CryptoAgentAPI:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_portfolio(self):
        response = requests.get(
            f"{self.base_url}/portfolio",
            headers=self.headers
        )
        return response.json()
    
    def create_alert(self, symbol, target_price, direction):
        data = {
            "symbol": symbol,
            "target_price": target_price,
            "direction": direction
        }
        response = requests.post(
            f"{self.base_url}/alerts",
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def generate_proposal(self, symbol, timeframe="4h", risk_percent=1.0):
        data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "risk_percent": risk_percent
        }
        response = requests.post(
            f"{self.base_url}/proposals",
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def get_market_data(self, symbol):
        response = requests.get(
            f"{self.base_url}/market/{symbol}",
            headers=self.headers
        )
        return response.json()
    
    def analyze(self, symbol, timeframe="4h"):
        data = {
            "symbol": symbol,
            "timeframe": timeframe
        }
        response = requests.post(
            f"{self.base_url}/analysis",
            headers=self.headers,
            json=data
        )
        return response.json()

# Usage
api = CryptoAgentAPI("https://api.yourbot.com", "your_api_key")

# Get portfolio
portfolio = api.get_portfolio()
print(f"Total value: ${portfolio['total_value']:,.2f}")

# Create alert
alert = api.create_alert("BTC", 100000, "above")
print(f"Alert created: {alert['alert_id']}")

# Generate proposal
proposal = api.generate_proposal("BTC", "4h", 1.0)
print(f"Entry: ${proposal['entry_price']:,.2f}")
print(f"R:R: {proposal['reward_risk_ratio']:.2f}:1")

# Get market data
market = api.get_market_data("BTC")
print(f"BTC: ${market['price']:,.2f} ({market['change_24h']:+.2f}%)")

# Analyze
analysis = api.analyze("BTC", "4h")
print(f"Recommendation: {analysis['recommendation']}")
```

---

## JavaScript Client Example

```javascript
class CryptoAgentAPI {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    };
  }

  async getPortfolio() {
    const response = await fetch(`${this.baseUrl}/portfolio`, {
      headers: this.headers
    });
    return response.json();
  }

  async createAlert(symbol, targetPrice, direction) {
    const response = await fetch(`${this.baseUrl}/alerts`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        symbol,
        target_price: targetPrice,
        direction
      })
    });
    return response.json();
  }

  async generateProposal(symbol, timeframe = '4h', riskPercent = 1.0) {
    const response = await fetch(`${this.baseUrl}/proposals`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        symbol,
        timeframe,
        risk_percent: riskPercent
      })
    });
    return response.json();
  }

  async getMarketData(symbol) {
    const response = await fetch(`${this.baseUrl}/market/${symbol}`, {
      headers: this.headers
    });
    return response.json();
  }

  async analyze(symbol, timeframe = '4h') {
    const response = await fetch(`${this.baseUrl}/analysis`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ symbol, timeframe })
    });
    return response.json();
  }
}

// Usage
const api = new CryptoAgentAPI('https://api.yourbot.com', 'your_api_key');

// Get portfolio
const portfolio = await api.getPortfolio();
console.log(`Total value: $${portfolio.total_value.toFixed(2)}`);

// Generate proposal
const proposal = await api.generateProposal('BTC', '4h', 1.0);
console.log(`Entry: $${proposal.entry_price.toFixed(2)}`);
console.log(`R:R: ${proposal.reward_risk_ratio.toFixed(2)}:1`);
```

---

## Interactive API Documentation

Once the server is running, visit:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

These provide interactive documentation where you can test all endpoints directly in your browser.

---

## Next Steps

1. Start API server
2. Get API key from config
3. Test with curl or Python client
4. Integrate with your applications
5. Set up TradingView webhooks
6. Monitor API usage and performance
