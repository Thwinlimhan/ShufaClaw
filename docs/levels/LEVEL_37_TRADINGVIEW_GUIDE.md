# TradingView Integration Guide (Level 37)

## Overview

Connect your TradingView alerts directly to the crypto agent bot via webhooks. When your TradingView strategy triggers, the bot receives the signal and can execute actions automatically.

## Setup Steps

### 1. Start API Server

Add to your `main.py`:

```python
from crypto_agent.api import start_api_server
import asyncio

# After bot initialization
async def run_both():
    # Start API server in background
    api_task = asyncio.create_task(
        start_api_server(
            bot_data=application.bot_data,
            config=config,
            port=8000
        )
    )
    
    # Start Telegram bot
    await application.run_polling()

# Run both
asyncio.run(run_both())
```

### 2. Expose Server (Production)

For TradingView to reach your webhook, you need a public URL:

**Option A: ngrok (Development)**
```bash
ngrok http 8000
```
This gives you a URL like: `https://abc123.ngrok.io`

**Option B: Cloud Deployment (Production)**
- Deploy to AWS/GCP/Azure
- Use a domain with SSL certificate
- Example: `https://api.yourbot.com`

### 3. Set Webhook Secret

Add to `.env`:
```bash
TRADINGVIEW_WEBHOOK_SECRET=your_random_secret_here_min_32_chars
```

Generate a secure secret:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### 4. Configure TradingView Alert

In TradingView:

1. Create your strategy/indicator
2. Click "Create Alert"
3. Set conditions
4. In "Webhook URL", enter:
   ```
   https://your-domain.com/webhook/tradingview
   ```

5. In "Message", use JSON format:
   ```json
   {
     "symbol": "{{ticker}}",
     "action": "buy",
     "price": {{close}},
     "strategy": "My Strategy",
     "timeframe": "{{interval}}",
     "message": "RSI crossed above 30"
   }
   ```

6. Add custom header:
   - Name: `X-Webhook-Secret`
   - Value: `your_random_secret_here_min_32_chars`

## TradingView Alert Examples

### Example 1: Simple Buy Signal

**Alert Message**:
```json
{
  "symbol": "BTCUSDT",
  "action": "buy",
  "price": {{close}},
  "message": "Golden cross detected"
}
```

**What happens**:
- Bot receives webhook
- Verifies secret
- Sends Telegram notification
- Optionally adds to portfolio

### Example 2: Sell Signal

**Alert Message**:
```json
{
  "symbol": "ETHUSDT",
  "action": "sell",
  "price": {{close}},
  "strategy": "RSI Overbought",
  "message": "RSI > 70, taking profits"
}
```

### Example 3: Close Position

**Alert Message**:
```json
{
  "symbol": "SOLUSDT",
  "action": "close",
  "price": {{close}},
  "message": "Stop loss hit"
}
```

### Example 4: Multi-Timeframe Confirmation

**Alert Message**:
```json
{
  "symbol": "{{ticker}}",
  "action": "buy",
  "price": {{close}},
  "strategy": "Multi-TF Breakout",
  "timeframe": "{{interval}}",
  "message": "Breakout confirmed on 4H and 1D"
}
```

## TradingView Variables

Use these in your alert messages:

- `{{ticker}}` - Symbol (e.g., BTCUSDT)
- `{{close}}` - Close price
- `{{open}}` - Open price
- `{{high}}` - High price
- `{{low}}` - Low price
- `{{volume}}` - Volume
- `{{time}}` - Timestamp
- `{{interval}}` - Timeframe (e.g., 4h, 1D)
- `{{exchange}}` - Exchange name

## Webhook Response

The bot responds with:

```json
{
  "success": true,
  "action": "buy",
  "symbol": "BTCUSDT",
  "price": 97500.0
}
```

## Telegram Notification

When webhook received, user gets:

```
🔔 TradingView Alert

Action: BUY BTCUSDT
Price: $97,500.00
Strategy: RSI Oversold

RSI crossed above 30, potential reversal
```

## Security Best Practices

### 1. Use Strong Webhook Secret
```python
# Generate 32+ character random string
import secrets
secret = secrets.token_urlsafe(32)
```

### 2. Verify Secret on Every Request
The bot automatically checks `X-Webhook-Secret` header.

### 3. Use HTTPS Only
Never use HTTP in production. TradingView requires HTTPS.

### 4. Rate Limiting
The bot has built-in rate limiting (100 requests/hour per API key).

### 5. IP Whitelisting (Optional)
TradingView webhook IPs:
- 52.89.214.238
- 34.212.75.30
- 54.218.53.128
- 52.32.178.7

Add to your firewall/nginx config.

## Advanced: Auto-Execute Trades

To automatically execute trades from TradingView:

```python
# In _handle_tradingview_webhook method

if webhook.action == "buy":
    # Generate proposal
    proposer = self.bot_data.get('trade_proposer')
    proposal = await proposer.generate_proposal(
        webhook.symbol,
        timeframe="4h",
        risk_percent=1.0
    )
    
    if proposal:
        # Save proposal
        await proposer.save_proposal(proposal)
        
        # Notify with full setup
        message = f"🎯 TradingView Signal → Trade Proposal\n\n"
        message += f"Symbol: {proposal.symbol}\n"
        message += f"Entry: ${proposal.entry_price:,.2f}\n"
        message += f"Stop: ${proposal.stop_loss:,.2f}\n"
        message += f"Target: ${proposal.target_2:,.2f}\n"
        message += f"R:R: {proposal.reward_risk_ratio:.2f}:1\n"
        
        await telegram_bot.send_message(chat_id=user_id, text=message)
```

## Testing Webhooks

### Test with curl:

```bash
curl -X POST https://your-domain.com/webhook/tradingview \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your_secret" \
  -d '{
    "symbol": "BTCUSDT",
    "action": "buy",
    "price": 97500,
    "strategy": "Test",
    "message": "Test webhook"
  }'
```

Expected response:
```json
{
  "success": true,
  "action": "buy",
  "symbol": "BTCUSDT",
  "price": 97500.0
}
```

### Test with Python:

```python
import requests

url = "https://your-domain.com/webhook/tradingview"
headers = {
    "Content-Type": "application/json",
    "X-Webhook-Secret": "your_secret"
}
data = {
    "symbol": "BTCUSDT",
    "action": "buy",
    "price": 97500,
    "strategy": "Test Strategy",
    "message": "Test webhook from Python"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

## Common TradingView Strategies

### 1. RSI Oversold/Overbought

**Pine Script**:
```pine
//@version=5
strategy("RSI Strategy", overlay=true)

rsi = ta.rsi(close, 14)

if (rsi < 30)
    strategy.entry("Buy", strategy.long)
    alert('{"symbol":"' + syminfo.ticker + '","action":"buy","price":' + str.tostring(close) + ',"message":"RSI oversold"}')

if (rsi > 70)
    strategy.close("Buy")
    alert('{"symbol":"' + syminfo.ticker + '","action":"sell","price":' + str.tostring(close) + ',"message":"RSI overbought"}')
```

### 2. Moving Average Crossover

**Pine Script**:
```pine
//@version=5
strategy("MA Cross", overlay=true)

fastMA = ta.sma(close, 20)
slowMA = ta.sma(close, 50)

if (ta.crossover(fastMA, slowMA))
    strategy.entry("Buy", strategy.long)
    alert('{"symbol":"' + syminfo.ticker + '","action":"buy","price":' + str.tostring(close) + ',"message":"Golden cross"}')

if (ta.crossunder(fastMA, slowMA))
    strategy.close("Buy")
    alert('{"symbol":"' + syminfo.ticker + '","action":"sell","price":' + str.tostring(close) + ',"message":"Death cross"}')
```

### 3. Breakout Strategy

**Pine Script**:
```pine
//@version=5
strategy("Breakout", overlay=true)

resistance = ta.highest(high, 20)

if (close > resistance)
    strategy.entry("Buy", strategy.long)
    alert('{"symbol":"' + syminfo.ticker + '","action":"buy","price":' + str.tostring(close) + ',"message":"Breakout above resistance"}')
```

## Troubleshooting

### Webhook Not Received

1. **Check URL**: Ensure it's publicly accessible
   ```bash
   curl https://your-domain.com/health
   ```

2. **Check Secret**: Verify it matches in both places

3. **Check Logs**: Look at server logs for errors

4. **Test Manually**: Use curl to test webhook

### Invalid Secret Error

- Ensure `X-Webhook-Secret` header is set
- Verify secret matches `.env` file
- Check for extra spaces/newlines

### Rate Limit Exceeded

- Default: 100 requests/hour
- Increase in `api_keys` configuration
- Or implement custom rate limiting

### SSL Certificate Error

- TradingView requires valid SSL
- Use Let's Encrypt for free SSL
- Or use ngrok for development

## Production Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  bot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - API_KEY=${API_KEY}
      - TRADINGVIEW_WEBHOOK_SECRET=${TRADINGVIEW_WEBHOOK_SECRET}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl;
    server_name api.yourbot.com;

    ssl_certificate /etc/letsencrypt/live/api.yourbot.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourbot.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Monitoring

### Log Webhooks

```python
# Add to webhook handler
import logging

logger = logging.getLogger(__name__)

logger.info(f"Webhook received: {webhook.action} {webhook.symbol} @ ${webhook.price}")
```

### Track Success Rate

```python
# Add metrics
webhook_count = 0
webhook_success = 0
webhook_errors = 0

# Update on each webhook
webhook_count += 1
if success:
    webhook_success += 1
else:
    webhook_errors += 1

# Calculate rate
success_rate = webhook_success / webhook_count * 100
```

## Next Steps

1. ✅ Start API server
2. ✅ Expose with ngrok (dev) or deploy (prod)
3. ✅ Set webhook secret
4. ✅ Create TradingView alert
5. ✅ Test with curl
6. ✅ Monitor Telegram notifications
7. ⏳ Build custom strategies
8. ⏳ Implement auto-execution
9. ⏳ Track performance

---

**Status**: Ready for TradingView integration

**Webhook URL**: `https://your-domain.com/webhook/tradingview`

**Documentation**: See API docs at `https://your-domain.com/docs`
