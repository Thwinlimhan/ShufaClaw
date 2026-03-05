import logging
import json
import re
from datetime import datetime
from crypto_agent.storage import database
from crypto_agent.intelligence.research_snapshot import get_research_snapshot
from crypto_agent.intelligence.behavior_analyzer import BehaviorAnalyzer
from crypto_agent.intelligence.analyst import get_ai_response
from crypto_agent.core import context_builder
from crypto_agent.core import prompts

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
        
        # 1. Fetch tailored feature context (CANONICAL API)
        feature_context = await context_builder.get_feature_context('execution_guard', symbol)
        
        # 2. Fetch data snapshot
        snapshot = await get_research_snapshot(symbol)
        snapshot_summary = "Research snapshot unavailable."
        if snapshot:
            snapshot_summary = (
                f"Price: ${snapshot['market_data']['price']}\n"
                f"1D RSI: {snapshot['technical'].get('1d', {}).get('rsi', 'N/A') if snapshot['technical'].get('1d') else 'N/A'}\n"
                f"24h Change: {snapshot['market_data']['change_24h']}%\n"
                f"7d Change: {snapshot['market_data']['change_7d']}%"
            )

        # 3. Fetch Behavioral & Emotional Context
        behavior_report = self.behavior_analyzer.generate_full_report()
        behavior_json = json.dumps(behavior_report, indent=2)

        # 4. Construct Evaluation Prompt using UNIFIED Prompts
        system_prompt = prompts.get_system_prompt('execution_guard')
        
        user_prompt = (
            f"--- TRADER'S INTENT ---\n"
            f"Asset: {symbol}\n"
            f"Their words: \"{intent_text}\"\n\n"
            
            f"--- RESEARCH SNAPSHOT ---\n"
            f"{snapshot_summary}\n\n"
            
            f"--- DEEP DATA CONTEXT (Portfolio/Rules/Journal) ---\n"
            f"{feature_context}\n\n"
            
            f"--- BEHAVIORAL & EMOTIONAL CONTEXT ---\n"
            f"{behavior_json}\n\n"
            
            "Evaluate this trade based on your system instructions. Reference their own rules back to them. Be the firm guardian. Keep it under 250 words."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        evaluation = await get_ai_response(messages)
        
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
                context_snapshot_id=snapshot.get('snapshot_id') if snapshot else None,
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
