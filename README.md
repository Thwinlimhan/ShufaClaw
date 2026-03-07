# 🏙️ ShufaClaw: Living Crypto Agent

ShufaClaw is a professional-grade, AI-driven personal cryptocurrency operating system. It functions as a "Living Agent" that manages research, execution discipline, airdrop farming, and portfolio optimization through a unified interface across Telegram, Discord, and a high-performance web dashboard.

---

## 🧠 Core Philosophy
*   **Data over Vibes**: Every recommendation is cited with technical, on-chain, and sentiment data.
*   **Execution Discipline**: An "Execution Guard" acts as a gatekeeper against FOMO and emotional trading.
*   **Self-Evolution**: The agent tracks its own predictions and learns from mistakes over time.
*   **Airdrop Triage**: Converts airdrop hunting into a prioritized, EV-aware pipeline.

---

## 🚀 Key Modules

### 1. Market Intelligence
*   **Real-time Data**: Integrated with Binance, CoinGecko, and CryptoPanic.
*   **Technical Analysis**: Automated RSI, Trend, and Volatility scans.
*   **Sentiment Engine**: Tracks Fear & Greed indices and news impact.

### 2. Portfolio & Risk Management
*   **Unified Tracking**: Consolidated view of all positions and performance metrics.
*   **EV Calculator**: Mathematical assessment of trade setups before entry.
*   **Price Alerts**: Intelligent threshold monitoring with multi-condition triggers.

### 3. Airdrop Intelligence Hub
*   **Wallet Reputation**: Scores your address health across 5 dimensions.
*   **Task Engine**: Generates prioritized daily action plans (Urgent/Regular/Maintenance).
*   **Protocol Registry**: Tracks Tier 1-4 protocols (zkSync, Scroll, Monad, etc.) for eligibility.

### 4. Living Agent Brain
*   **Cognitive Loop**: Proactive reasoning cycles that scan for opportunities and risks.
*   **Evolution Engine**: Logs predictions and calibrates accuracy via self-learning sessions.
*   **Skill System**: Modular reasoning patterns that trigger automatically based on queries.

---

## 🖥️ Command Center

### Telegram Commands
*   `/start` - Initialize agent communications.
*   `/portfolio` - View detailed P&L and asset exposure.
*   `/market` - Get a state-of-the-market research briefing.
*   `/airdrop` - Access the Airdrop Intelligence Hub.
*   `/airdroptasks` - Get your daily prioritized farming agenda.
*   `/evolution` - Check the agent's self-improvement and accuracy stats.

---

## 🛠️ Setup & Installation

### 1. Prerequisites
*   Python 3.10+
*   Telegram Bot Token (from @BotFather)
*   OpenRouter API Key (for LLM reasoning)
*   Etherscan API Key (for airdrop/on-chain tracking)

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/Thwinlimhan/ShufaClaw.git
cd ShufaClaw

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Create a .env file and add your keys (see config.py for required fields)
```

### 3. Run the System
```powershell
python main.py
```

### 4. V2 Infrastructure (Optional — for full quant stack)
The V2 architecture uses TimescaleDB, Redis, and Kafka. Start them with Docker:

```powershell
docker-compose up -d
# Wait ~30 seconds for services to be ready
py test_v2_infra.py   # Verify connectivity
```

Then run the bot — it will auto-initialize V2 tables and market streams.

### 5. V2 Web Dashboard (React)
```powershell
cd v2_frontend
npm install
npm run dev
```
Open http://localhost:5173. The dashboard proxies API calls to the FastAPI backend (port 8000).

---

## 📬 Communications
The agent reports to:
*   **Telegram**: Direct interaction and alert delivery.
*   **Discord**: Organized HQ with dedicated channels for logs and strategy.
*   **Web Dashboard**: Real-time visual metrics and system telemetry (FastAPI).

---

## 🛡️ License
Private Repository - For personal use only.

*Built with ❤️ for professional crypto operators.*