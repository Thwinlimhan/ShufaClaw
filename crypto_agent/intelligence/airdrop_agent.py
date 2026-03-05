import logging
import json
from datetime import datetime
from crypto_agent.storage import database
from crypto_agent.airdrop.tracker import AirdropTracker
from crypto_agent.airdrop.wallet_scorer import WalletScorer
from crypto_agent.intelligence.analyst import get_ai_response

logger = logging.getLogger(__name__)

class AirdropIntelAgent:
    def __init__(self, bot=None, chat_id=None):
        self.bot = bot
        self.chat_id = chat_id
        self.tracker = AirdropTracker()
        self.scorer = WalletScorer()

    async def get_airdrop_strategy(self) -> str:
        """
        Generates a prioritized, EV-aware airdrop strategy.
        Analyzes tracked protocols vs wallet reputation gaps.
        """
        # 1. Fetch Dashboard & Wallet Data
        dashboard = self.tracker.get_dashboard()
        
        # We need to fetch the last known wallet metrics from DB
        # This assumes the user has linked a wallet address.
        # For this agent, we'll try to get the first one from wallet_metrics.
        wallet_addr = None
        wallet_data = {}
        try:
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT wallet_address FROM wallet_metrics LIMIT 1")
            row = cursor.fetchone()
            if row:
                wallet_addr = row[0]
                wallet_data = database.get_wallet_metrics(wallet_addr)
            conn.close()
        except Exception as e:
            logger.error(f"Error fetching wallet for airdrop agent: {e}")

        # 2. Score Wallet and identify gaps
        wallet_analysis = self.scorer.score_wallet(wallet_data) if wallet_data else None
        
        # 3. Construct Strategy Prompt
        prompt = (
            f"You are the Airdrop Intelligence & Triage Agent for a crypto farmer.\n"
            f"Your goal is to turn airdrop hunting into a prioritized, EV-aware pipeline.\n\n"
            
            f"--- AIRDROP HUB STATE ---\n"
            f"Total Tracked: {dashboard['total_tracked']}\n"
            f"Criteria Met (>=70%): {dashboard['criteria_met']}\n"
            f"Close to Eligibility (40-70%): {dashboard['close']}\n"
            f"Needs Work (<40%): {dashboard['needs_work']}\n"
            f"Met Protocols: {', '.join([p[0] for p in dashboard.get('met_list', [])])}\n"
            f"Upcoming Snapshots: {', '.join([f'{s[0]} ({s[1]})' for s in dashboard.get('upcoming_snapshots', [])])}\n\n"
            
            f"--- WALLET REPUTATION ({wallet_addr if wallet_addr else 'No wallet linked'}) ---\n"
            f"Score: {wallet_analysis['composite_score'] if wallet_analysis else 'N/A'}/100\n"
            f"Gaps: {', '.join(wallet_analysis['gaps_to_address']) if wallet_analysis else 'N/A'}\n"
            f"Sybil Flags: {', '.join(wallet_analysis['sybil_flags']) if wallet_analysis else 'None'}\n\n"
            
            "Based on this data, provide a structured action plan:\n"
            "1. PRIORITY TRIAGE: Which 2-3 protocols are highest EV (Expected Value) right now? (Combine Tier + Your Score).\n"
            "2. DAILY ACTION PLAN: List 3-5 concrete tasks to do today (e.g., bridge to X, swap on Y, vote on Z).\n"
            "3. HYGIENE & ANTI-SYBIL: Specific advice to improve the wallet reputation score and avoid being flagged.\n"
            "4. EV CLASSIFICATION: For each prioritized protocol, categorize as SKIP, LOW, MEDIUM, HIGH, or CORE.\n\n"
            "Be aggressive about efficiency. If something is overfarmed or low EV, say so. Keep it under 300 words."
        )

        strategy = await get_ai_response([{"role": "user", "content": prompt}])
        
        if not strategy:
            return "❌ Airdrop intelligence engine failed. Please try again later."

        # 4. Extract structured data for logging
        ev_label = "MEDIUM"
        for line in strategy.split('\n'):
            line_u = line.upper()
            for label in ['SKIP', 'LOW', 'MEDIUM', 'HIGH', 'CORE']:
                if label in line_u:
                    ev_label = label
                    break

        # 5. Log Decisions
        try:
            database.log_agent_decision(
                agent_name="AirdropIntelAgent",
                skill_name="get_airdrop_strategy",
                input_type="AIRDROP_PIPELINE",
                input_payload=json.dumps(dashboard),
                context_snapshot_id=None,
                recommendation=strategy[:250] + "...",
                prediction_type="EV_CATEGORY",
                prediction_horizon="30D", # Airdrops are longer term
                explicit_prediction=ev_label,
                confidence_score=70
            )
        except Exception as e:
            logger.error(f"Failed to log airdrop agent decision: {e}")

        return f"🪂 **AIRDROP INTELLIGENCE & TRIAGE**\n\n{strategy}"
