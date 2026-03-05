import logging
import asyncio
from datetime import datetime
from crypto_agent.storage import database as db
from crypto_agent.data import prices as price_service
from crypto_agent.intelligence import analyst

logger = logging.getLogger(__name__)

class PerformanceTracker:
    @staticmethod
    def record_prediction(symbol, pred_type, price, rationale):
        """Records a new prediction for 24h/7d checking."""
        try:
            pred_id = db.create_prediction(symbol, pred_type, price, rationale)
            logger.info(f"Recorded {pred_type} prediction for {symbol} at ${price:,.2f} (ID: {pred_id})")
            return pred_id
        except Exception as e:
            logger.error(f"Failed to record prediction: {e}")
            return None

    @staticmethod
    async def check_pending_predictions():
        """Aggregates all predictions ready for a price check."""
        # 1. Check 24h Predictions
        pending_24h = db.get_pending_predictions_24h()
        if pending_24h:
            logger.info(f"Checking {len(pending_24h)} pending 24h predictions...")
            for p in pending_24h:
                curr_price, _ = await price_service.get_price(p['symbol'])
                if curr_price:
                    # Determine result
                    p_initial = p['price']
                    p_type = p['type'].lower()
                    
                    is_correct = False
                    if p_type == 'bullish' and curr_price > p_initial: is_correct = True
                    elif p_type == 'bearish' and curr_price < p_initial: is_correct = True
                    elif p_type == 'neutral' and abs(curr_price - p_initial) / p_initial < 0.02: is_correct = True # Within 2%
                    
                    result = 'correct' if is_correct else 'incorrect'
                    accuracy = ((curr_price - p_initial) / p_initial) * 100
                    db.update_prediction_result_24h(p['id'], result, curr_price, accuracy)

        # 2. Check 7d Predictions
        pending_7d = db.get_pending_predictions_7d()
        if pending_7d:
            logger.info(f"Checking {len(pending_7d)} pending 7d predictions...")
            for p in pending_7d:
                curr_price, _ = await price_service.get_price(p['symbol'])
                if curr_price:
                    p_initial = p['price']
                    p_type = p['type'].lower()
                    
                    is_correct = False
                    if p_type == 'bullish' and curr_price > p_initial: is_correct = True
                    elif p_type == 'bearish' and curr_price < p_initial: is_correct = True
                    elif p_type == 'neutral' and abs(curr_price - p_initial) / p_initial < 0.05: is_correct = True # Within 5%
                    
                    result = 'correct' if is_correct else 'incorrect'
                    db.update_prediction_result_7d(p['id'], result, curr_price)

    @staticmethod
    def generate_accuracy_report():
        """Creates a formatted report for the user."""
        stats = db.get_prediction_stats()
        
        if stats['total_24h'] == 0:
            return "🎯 **PREDICTION ACCURACY REPORT**\n\nNo predictions have matured yet. Check back in 24 hours!"
            
        acc_24h = (stats['correct_24h'] / stats['total_24h']) * 100
        acc_7d = (stats['correct_7d'] / stats['total_7d'] * 100) if stats['total_7d'] > 0 else 0
        
        msg = (
            f"🎯 **PREDICTION ACCURACY REPORT**\n\n"
            f"Based on **{stats['total_24h']}** predictions matured:\n\n"
            f"**OVERALL:**\n"
            f"24h Accuracy: {acc_24h:.1f}% {'✅' if acc_24h > 50 else '⚠️'}\n"
            f"7d Accuracy: {acc_7d:.1f}% {'✅' if acc_7d > 50 else '⚠️' if stats['total_7d'] > 0 else '⏳'}\n\n"
        )
        
        msg += "**BY DIRECTION:**\n"
        for dr in stats['direction']:
            d_type, total, correct = dr
            d_acc = (correct / total) * 100
            msg += f"• {d_type.capitalize()}: {d_acc:.1f}% ({correct}/{total})\n"
            
        msg += "\n**BY COIN (Top 5):**\n"
        best_coin = ""
        best_coin_acc = 0
        for c in stats['coins']:
            sym, total, correct = c
            c_acc = (correct / total) * 100
            msg += f"• {sym}: {c_acc:.1f}% ({correct}/{total})\n"
            if c_acc > best_coin_acc:
                best_coin_acc = c_acc
                best_coin = sym
                
        if best_coin:
            msg += f"\n💡 **INSIGHT:** Bot's {best_coin} analysis is currently most reliable ({best_coin_acc:.1f}%)."
            
        return msg

    @staticmethod
    async def run_learning_session(bot, chat_id):
        """AI review of its own accuracy to improve."""
        stats = db.get_prediction_stats()
        if stats['total_24h'] < 5: return # Need some data first
        
        report = PerformanceTracker.generate_accuracy_report()
        prompt = (
            f"Here is your prediction accuracy report:\n\n{report}\n\n"
            "Based on this data, what patterns do you notice about when your analysis is reliable vs unreliable? "
            "Suggest 2 specific adjustments to improve accuracy going forward. "
            "Respond like a data scientist. Keep it under 150 words."
        )
        
        advice = await analyst.get_ai_response([{"role": "user", "content": prompt}])
        if advice:
            # Save advice as a permanent note
            db.add_note(f"AI SELF-CORRECTION: {advice}", category='system')
            await bot.send_message(chat_id=chat_id, text=f"🧠 **AI LEARNING SESSION**\n\nI just reviewed my accuracy data:\n\n{advice}\n\n*Applied as a permanent system note.*", parse_mode='Markdown')
