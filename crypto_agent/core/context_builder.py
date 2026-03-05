import logging
from crypto_agent.storage import database
from crypto_agent.data import prices as price_service
from crypto_agent.data import market as market_service, onchain as onchain_data

logger = logging.getLogger(__name__)

async def build_full_context():
    """Builds a comprehensive summary of portfolio, market, and alerts."""
    context = "--- REAL-TIME CONTEXT ---\n"
    
    try:
        # 1. Portfolio Data
        positions = database.get_all_positions()
        if positions:
            context += "\nYOUR PORTFOLIO:\n"
            total_value = 0
            for p in positions:
                price, _ = await price_service.get_price(p['symbol'])
                if price:
                    val = p['quantity'] * price
                    total_value += val
                    context += f"- {p['symbol']}: {p['quantity']} coins (avg ${p['avg_price']}, current ${price})\n"
                else:
                    context += f"- {p['symbol']}: {p['quantity']} coins (avg ${p['avg_price']})\n"
            context += f"Total Portfolio Value: ${total_value:,.2f}\n"
        
        # 3. Active Alerts
        alerts = database.get_active_alerts()
        if alerts:
            context += "\nYOUR ACTIVE ALERTS:\n"
            for a in alerts:
                context += f"- ID #{a['id']}: {a['symbol']} {a['direction']} ${a['target_price']}\n"

        # 2. Market Overview
        market_summary = await market_service.build_market_context_for_claude()
        context += f"\n{market_summary}\n"

        # NEW: On-chain Intelligence
        onchain_summary = await onchain_data.build_onchain_summary()
        context += f"\n{onchain_summary}\n"

        # 4. Recent Journal Entries
        journal = database.get_journal_entries(limit=5)
        if journal:
            context += "\nRECENT JOURNAL ENTRIES:\n"
            for entry in journal:
                context += f"- {entry['timestamp']} ({entry['entry_type']}): {entry['content'][:150]}...\n"
                
        # 5. Permanent Notes & Rules
        notes_context = database.get_notes_for_context()
        if notes_context:
            context += f"\n{notes_context}\n"

        # --- LIVING AGENT BRAIN STATE ---
        context += "\n--- MY AGENT INTELLIGENCE ---\n"
        
        # 6. Belief State
        beliefs = database.get_connection().execute("SELECT belief_key, direction, confidence FROM belief_state").fetchall()
        if beliefs:
            context += "\nCURRENT BELIEFS:\n"
            for b in beliefs[:5]: # Top 5
                context += f"- {b[0]}: {b[1]} (Confidence: {b[2]*100:.0f}%)\n"
        
        # 7. Evolution Progress
        stats = database.get_connection().execute("SELECT AVG(metric_value) FROM evolution_log WHERE metric_name = 'prediction_accuracy'").fetchone()
        if stats and stats[0] is not None:
            context += f"\nCurrent Self-Evolved Accuracy: {stats[0]*100:.1f}%\n"

        # 8. Airdrop Reputation
        linked_wallet = database.get_scanner_setting('linked_wallet', None)
        if linked_wallet:
            metrics = database.get_wallet_metrics(linked_wallet)
            if metrics:
                from crypto_agent.airdrop.wallet_scorer import WalletScorer
                scorer = WalletScorer()
                res = scorer.score_wallet(metrics)
                context += f"\nYOUR AIRDROP REPUTATION: {res['composite_score']}/100 ({res['grade']})\n"
                if res['gaps_to_address']:
                    context += f"Recommended actions: {', '.join(res['gaps_to_address'][:2])}\n"

    except Exception as e:
        logger.error(f"Error building full context: {e}")
        context += "\n(Note: Some real-time data is currently unavailable)\n"
        
    return context
