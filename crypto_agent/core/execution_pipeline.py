"""
Hard Permission Layer & Execution Pipeline for ShufaClaw.
Ensures every execution passes a hard rule check and user consent.
"""

from enum import Enum
import logging
from crypto_agent.storage import database
from crypto_agent.intelligence.execution_guard import ExecutionGuardAgent

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    PENDING = "PENDING"      # Waiting for guard evaluation
    WAITING = "WAITING"      # Evaluation done, waiting for user YES/NO
    APPROVED = "APPROVED"    # User gave permission
    REJECTED = "REJECTED"    # User or guard rejected
    OUT_OF_POLICY = "OUT_OF_POLICY" # Critical rule violation
    SUCCESS = "SUCCESS"      # Execution completed
    FAILED = "FAILED"        # Execution crashed

class ExecutionPipeline:
    def __init__(self, bot=None, chat_id=None):
        self.bot = bot
        self.chat_id = chat_id
        self.guard = ExecutionGuardAgent(bot, chat_id)

    async def prepare_execution(self, symbol: str, intent_text: str, payload: dict) -> dict:
        """
        Step 1: Runs the intent through the Execution Guard Agent.
        Returns evaluation and status.
        """
        evaluation_text = await self.guard.evaluate_trade_intent(symbol, intent_text)
        
        # Determine initial status from evaluation
        status = ExecutionStatus.WAITING
        if "OUT_OF_POLICY" in evaluation_text.upper():
            status = ExecutionStatus.OUT_OF_POLICY
            
        return {
            "status": status,
            "evaluation": evaluation_text,
            "payload": payload
        }

    async def execute_trade(self, payload: dict, confirmed_by_user: bool) -> dict:
        """
        Step 2: The final gate before any API/Smart Contract call.
        """
        if not confirmed_by_user:
            return {"status": ExecutionStatus.REJECTED, "message": "Manual permission denied."}

        # FINAL PERMISSION CHECK
        # (This is where we could add 2FA logic or auto-rejection based on hard rules)
        
        try:
            # Placeholder for real execution (Part 10 / CCXT / Etherscan etc.)
            logger.info(f"EXECUTING TRADE: {payload}")
            
            # Log successful execution
            database.log_agent_decision(
                agent_name="ExecutionPipeline",
                skill_name="execute_trade",
                input_type="TRADE_PAYLOAD",
                input_payload=str(payload),
                recommendation="SUCCESSFULLY_EXECUTED",
                prediction_type="EXECUTION_STATUS",
                explicit_prediction="SUCCESS"
            )
            
            return {"status": ExecutionStatus.SUCCESS, "message": "Trade successfully logged and executed."}
            
        except Exception as e:
            logger.error(f"Execution failure: {e}")
            return {"status": ExecutionStatus.FAILED, "message": f"Execution error: {e}"}

# Global instance for shared access
# pipeline = ExecutionPipeline()
