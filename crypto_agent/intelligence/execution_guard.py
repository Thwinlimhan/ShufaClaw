import logging
import json
from datetime import datetime
from crypto_agent.storage import database
from crypto_agent.intelligence.research_snapshot import get_research_snapshot
from crypto_agent.intelligence.behavior_analyzer import BehaviorAnalyzer
from crypto_agent.intelligence.analyst import get_ai_response

logger = logging.getLogger(__name__)

class ExecutionGuardAgent:
    def __init__(self, bot=None, chat_id=None):
        self.bot = bot
        self.chat_id = chat_id
        self.behavior_analyzer = BehaviorAnalyzer()

    async def evaluate_trade_intent(self, symbol: str, intent_text: str) -> str:
        """
        Evaluates a trade intent against rules, technicals, and emotional state.
        Ensures the user only acts on high-quality, in-policy setups.
        """
        symbol = symbol.upper()
        
        # 1. Fetch data context
        snapshot = await get_research_snapshot(symbol)
        if not snapshot:
            return "❌ Could not gather enough data to evaluate this trade."

        # 2. Fetch User Rules (Permanent Notes)
        notes = database.get_all_notes(active_only=True)
        rules_text = "\n".join([f"- [{n['category'].upper()}] {n['content']}" for n in notes])
        if not rules_text:
            rules_text = "No specific trading rules found in permanent notes."

        # 3. Fetch Behavior Analysis
        behavior_report = self.behavior_analyzer.generate_full_report()
        behavior_json = json.dumps(behavior_report, indent=2)

        # 4. Construct Evaluation Prompt
        prompt = (
            f"You are the Execution Guard & Emotion Agent for a professional crypto trader.\n"
            f"Your job is to enforce their trading rules and prevent emotional trades.\n\n"
            
            f"--- TRADER'S INTENT ---\n"
            f"Asset: {symbol}\n"
            f"Their words: \"{intent_text}\"\n\n"
            
            f"--- RESEARCH SNAPSHOT ---\n"
            f"Price: ${snapshot['market_data']['price']}\n"
            f"1D RSI: {snapshot['technical'].get('1d', {}).get('rsi', 'N/A') if snapshot['technical'].get('1d') else 'N/A'}\n"
            f"24h Change: {snapshot['market_data']['change_24h']}%\n"
            f"7d Change: {snapshot['market_data']['change_7d']}%\n\n"
            
            f"--- TRADER'S PERMANENT RULES ---\n"
            f"{rules_text}\n\n"
            
            f"--- BEHAVIORAL & EMOTIONAL CONTEXT ---\n"
            f"{behavior_json}\n\n"
            
            "Evaluate this trade and provide a structured report covering:\n"
            "1. POLICY ALIGNMENT: Is this trade 'In-Policy' or 'Out-of-Policy' based on their rules?\n"
            "   (Check if they are trying to buy something oversold, if they are revenge trading, if size is mentioned etc.)\n"
            "2. SETUP QUALITY score (1-10): Based on technical confluence and market regime.\n"
            "3. POSITION SIZING & LEVELS: Suggest a safe size and clear invalidation level (stop loss).\n"
            "4. EMOTIONAL CHECKLIST: Address revenge trading risk, time-of-day performance, or streak patterns detected in behavior data.\n"
            "5. VERDICT: Explicitly state IN_POLICY or OUT_OF_POLICY with a short reasoning.\n\n"
            "Be direct. Be the firm guardian. Reference their own rules back to them. Keep it under 250 words."
        )

        evaluation = await get_ai_response([{"role": "user", "content": prompt}])
        
        if not evaluation:
            return "❌ Evaluation engine failed. Proceed with extreme caution."

        # 5. Extract structured data for logging
        risk_label = "LOW"
        policy_label = "IN_POLICY"
        quality_score = 5
        horizon = "7D" # Default
        
        evaluation_u = evaluation.upper()
        if "OUT_OF_POLICY" in evaluation_u:
            policy_label = "OUT_OF_POLICY"
            risk_label = "HIGH"
        
        # Simple extraction for quality score
        import re
        score_match = re.search(r'SETUP QUALITY.*?(\d+)', evaluation_u)
        if score_match:
            quality_score = int(score_match.group(1))

        # 6. Log Decision
        try:
            database.log_agent_decision(
                agent_name="ExecutionGuardAgent",
                skill_name="evaluate_trade_intent",
                input_type="TRADE_INTENT",
                input_payload=json.dumps({"symbol": symbol, "intent": intent_text}),
                context_snapshot_id=snapshot.get('snapshot_id'),
                recommendation=evaluation[:250] + "...",
                prediction_type="RISK_LEVEL",
                prediction_horizon=horizon,
                explicit_prediction=f"{policy_label} | Score: {quality_score}",
                confidence_score=quality_score * 10 
            )
        except Exception as e:
            logger.error(f"Failed to log execution guard decision: {e}")

        # 7. Format final response
        header = "🛡️ **EXECUTION GUARD & EMOTION AGENT**\n\n"
        if policy_label == "OUT_OF_POLICY":
            header += "⚠️ **CAUTION: THIS TRADE MAY BE OUT-OF-POLICY**\n\n"
        
        return f"{header}{evaluation}"
