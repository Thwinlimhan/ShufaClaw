# 🚀 Deployment Checklist

Complete checklist for deploying the crypto intelligence agent to production.

## Phase 1: Pre-Deployment Testing ✅

### 1.1 Run Comprehensive Tests
```bash
py test_comprehensive.py
```

**Expected Result**: All tests pass with 0 failures

**If tests fail**:
- Review failed test output
- Fix issues in order of criticality
- Re-run tests until all pass

### 1.2 Run Individual Module Tests
```bash
# Security
py test_security.py

# Performance Attribution
py test_attribution.py

# Trade Proposer
py test_trade_proposer.py

# Debate System
py test_debate_system.py

# Event Predictor
py test_event_predictor.py

# Simulation
py test_simulation.py
```

### 1.3 Check Dependencies
```bash
py -m pip list
```

**Verify installed**:
- python-telegram-bot >= 22.0
- anthropic >= 0.18.0
- fastapi >= 0.109.0
- cryptography >= 41.0.0
- All packages from requirements.txt

### 1.4 Verify File Structure
```
crypto_agent/
├── core/           ✓ Agent, orchestrator, workflows, task queue
├── data/           ✓ Market, technical, news, on-chain
├── intelligence/   ✓ All analysis modules
├── storage/        ✓ Database, backup
├── bot/            ✓ Handlers, keyboards
├── security/       ✓ Encryption, audit, anomaly
├── education/      ✓ Academy
├── testing/        ✓ Mocks, generators, scenarios
├── api/            ✓ REST API server
├── derivatives/    ✓ Options monitor
└── blockchain/     ✓ Cross-chain monitor
```

---

## Phase 2: Configuration ⚙️

### 2.1 Environment Variables

Create/verify `.env` file:

```bash
# CRITICAL - Required for basic operation
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ANTHROPIC_API_KEY=sk-ant-your-key-here
ALLOWED_USER_ID=your_telegram_user_id

# IMPORTANT - Recommended for full features
ETHERSCAN_API_KEY=your_etherscan_key
COINGECKO_API_KEY=your_coingecko_key
CRYPTOPANIC_API_TOKEN=your_cryptopanic_token

# SECURITY - Required for production
ENCRYPTION_SECRET=random_32_character_secret_key
SECURITY_PIN=your_4_digit_pin

# OPTIONAL - Enhanced features
DASHBOARD_PASSWORD=strong_password_here
DASHBOARD_PORT=8080
GROQ_API_KEY=your_groq_key_for_voice
NEYNAR_API_KEY=your_neynar_key_for_farcaster

# API - For TradingView integration
TRADINGVIEW_WEBHOOK_SECRET=random_secret_for_webhooks
API_KEY=your_api_key_for_rest_api
```

### 2.2 Generate Secrets

```bash
# Generate encryption secret (Python)
py -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate API key
py -c "import secrets; print(secrets.token_hex(16))"

# Generate webhook secret
py -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2.3 Get Your Telegram User ID

1. Start a chat with @userinfobot on Telegram
2. Copy your user ID
3. Add to `.env` as `ALLOWED_USER_ID`

### 2.4 Verify Configuration

```bash
py -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✅ Config loaded' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌ Missing token')"
```

---

## Phase 3: Database Setup 💾

### 3.1 Initialize Database

```bash
py -c "from crypto_agent.storage.database import Database; db = Database('crypto_agent.db'); print('✅ Database initialized')"
```

### 3.2 Verify Tables

```bash
py -c "from crypto_agent.storage.database import Database; db = Database('crypto_agent.db'); tables = db.conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall(); print(f'✅ {len(tables)} tables created')"
```

**Expected**: ~40+ tables

### 3.3 Backup Strategy

Create backup directory:
```bash
mkdir -p backups
```

Add to cron (Linux/Mac) or Task Scheduler (Windows):
```bash
# Daily backup at 3 AM
0 3 * * * cp crypto_agent.db backups/crypto_agent_$(date +\%Y\%m\%d).db
```

---

## Phase 4: Security Hardening 🔒

### 4.1 File Permissions

```bash
# Linux/Mac
chmod 600 .env
chmod 600 crypto_agent.db
chmod 700 backups/

# Windows (PowerShell)
icacls .env /inheritance:r /grant:r "$env:USERNAME:(R)"
```

### 4.2 Security Checklist

- [ ] `.env` file not in git (check `.gitignore`)
- [ ] Database file not in git
- [ ] Encryption secret is random and secure
- [ ] Security PIN is not default (1234)
- [ ] API keys are valid and active
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] Auto-delete for sensitive messages enabled

### 4.3 Test Security Features

```bash
py test_security.py
```

---

## Phase 5: Dry Run 🧪

### 5.1 Test Bot Locally

```bash
py main.py
```

**Test these commands in Telegram**:
1. `/start` - Bot responds with welcome
2. `/help` - Shows command menu
3. `/status` - Shows system status
4. `/health` - All systems green
5. `/price BTC` - Returns current price
6. `/market` - Shows market overview

### 5.2 Test Core Features

```
/portfolio - Should show empty or test portfolio
/alert BTC above 100000 - Creates alert
/alerts - Shows active alerts
/journal Test entry - Logs entry
/briefing - Generates briefing
/ta BTC - Technical analysis
/news - News sentiment
```

### 5.3 Test Advanced Features

```
/debate BTC - Multi-analyst debate
/research ETH - Full research report
/optimize - Portfolio optimization
/signal BTC - Unified intelligence
/agenda - Daily action agenda
```

### 5.4 Monitor Logs

Check for errors:
```bash
# If logging to file
tail -f crypto_agent.log

# Or check console output
```

---

## Phase 6: API Testing 🌐

### 6.1 Start API Server

```bash
# In separate terminal
py -c "from crypto_agent.api.server import start_api_server; import asyncio; asyncio.run(start_api_server({}, {}, port=8000))"
```

### 6.2 Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Get portfolio (with API key)
curl -H "Authorization: Bearer your_api_key" http://localhost:8000/api/portfolio

# Interactive docs
# Open browser: http://localhost:8000/docs
```

---

## Phase 7: Performance Optimization ⚡

### 7.1 Run Performance Tests

```bash
py -c "import asyncio; from test_comprehensive import test_performance; asyncio.run(test_performance())"
```

### 7.2 Check Response Times

Monitor these metrics:
- Price fetch: <500ms
- Database query: <100ms
- AI response: <5s
- Morning briefing: <10s

### 7.3 Optimize if Needed

**If slow**:
- Check internet connection
- Verify API rate limits not hit
- Clear old data from database
- Restart bot

---

## Phase 8: Production Deployment 🚀

### 8.1 Choose Deployment Method

**Option A: Local Machine (Easiest)**
- Run on your computer
- Use Task Scheduler (Windows) or cron (Linux/Mac)
- Requires computer to stay on

**Option B: VPS (Recommended)**
- DigitalOcean, Linode, AWS EC2
- Always online
- Better reliability

**Option C: Cloud Platform**
- Heroku, Railway, Render
- Managed infrastructure
- May have cold starts

### 8.2 Setup Process Monitor

**Windows (Task Scheduler)**:
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: At startup
4. Action: Start program
5. Program: `py`
6. Arguments: `C:\path\to\main.py`
7. Start in: `C:\path\to\project`

**Linux (systemd)**:
```bash
# Create service file
sudo nano /etc/systemd/system/crypto-agent.service
```

```ini
[Unit]
Description=Crypto Intelligence Agent
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable crypto-agent
sudo systemctl start crypto-agent
sudo systemctl status crypto-agent
```

**Using PM2 (Node.js process manager)**:
```bash
npm install -g pm2
pm2 start main.py --interpreter python3 --name crypto-agent
pm2 save
pm2 startup
```

### 8.3 Setup Monitoring

**Health Check Script** (`health_check.sh`):
```bash
#!/bin/bash
response=$(curl -s http://localhost:8000/health)
if [[ $response == *"healthy"* ]]; then
    echo "✅ Bot is healthy"
else
    echo "❌ Bot is down - restarting"
    # Restart command here
fi
```

Run every 5 minutes via cron:
```bash
*/5 * * * * /path/to/health_check.sh
```

---

## Phase 9: Post-Deployment Verification ✓

### 9.1 24-Hour Check

After 24 hours, verify:
- [ ] Bot is still running
- [ ] Morning briefing was sent
- [ ] Alerts are working
- [ ] No error messages
- [ ] Database is growing normally
- [ ] Memory usage is stable

### 9.2 Week 1 Monitoring

Monitor daily:
- Response times
- Error rates
- API costs
- Database size
- Memory usage

### 9.3 Performance Metrics

Track these KPIs:
- Uptime: Target 99%+
- Response time: <5s average
- API cost: <$50/month
- Successful commands: >95%

---

## Phase 10: Maintenance Plan 🔧

### 10.1 Daily Tasks (Automated)
- Morning briefing (8 AM)
- Evening summary (9 PM)
- Scanner checks (every 5 min)
- Database backup (3 AM)

### 10.2 Weekly Tasks (Manual)
- Review audit logs
- Check error logs
- Verify API costs
- Test critical commands
- Review performance metrics

### 10.3 Monthly Tasks
- Update dependencies
- Rotate API keys
- Clean old data
- Review and optimize
- Backup full system

---

## Troubleshooting 🔍

### Bot Won't Start

**Check**:
1. `.env` file exists and has correct values
2. All dependencies installed
3. Python version 3.11+
4. No other process using same port

**Fix**:
```bash
py -m pip install -r requirements.txt --upgrade
```

### Commands Not Working

**Check**:
1. User ID matches `ALLOWED_USER_ID`
2. Bot has correct permissions
3. API keys are valid
4. Database is accessible

### High API Costs

**Reduce**:
1. Increase cache duration
2. Reduce scanner frequency
3. Limit AI calls
4. Use mock services for testing

### Database Growing Too Large

**Clean**:
```bash
py -c "from crypto_agent.storage.database import Database; db = Database('crypto_agent.db'); db.cleanup_old_data(days=30)"
```

---

## Success Criteria ✨

Your deployment is successful when:

- ✅ Bot responds to all commands
- ✅ Morning briefing arrives daily
- ✅ Alerts trigger correctly
- ✅ No errors in logs for 24 hours
- ✅ API costs within budget
- ✅ Database backups working
- ✅ Security features active
- ✅ Performance metrics good

---

## Next Steps After Deployment 🎯

1. **Use it daily** for 1-2 weeks
2. **Track what you actually use** vs what's theoretical
3. **Identify pain points** and areas for improvement
4. **Optimize based on real usage**
5. **Consider adding** Discord, Airdrop Intelligence, or Living Agent features

---

## Emergency Contacts 🆘

**If something breaks**:
1. Check logs first
2. Restart the bot
3. Verify configuration
4. Test with `/health` command
5. Review recent changes

**Backup restoration**:
```bash
cp backups/crypto_agent_YYYYMMDD.db crypto_agent.db
py main.py
```

---

## Deployment Complete! 🎉

Once all checklist items are complete, your crypto intelligence agent is production-ready and operational.

**Remember**: Start simple, use it daily, and iterate based on real needs.
