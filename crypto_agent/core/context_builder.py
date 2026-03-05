import logging
from crypto_agent.storage import database
from crypto_agent.data import prices as price_service
from crypto_agent.data import market as market_service, onchain as onchain_data

logger = logging.getLogger(__name__)

async def get_portfolio_context():
    """Returns formatted string of current portfolio."""
    try:
        positions = database.get_all_positions()
        if not positions:
            return "No positions currently in portfolio."
        
        context = "YOUR PORTFOLIO:\n"
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
        return context
    except Exception as e:
        logger.error(f"Error fetching portfolio context: {e}")
        return "Portfolio data unavailable."

async def get_market_context():
    """Returns market overview and sentiment."""
    try:
        return await market_service.build_market_context_for_claude()
    except Exception as e:
        logger.error(f"Error fetching market context: {e}")
        return "Market data unavailable."

async def get_onchain_context():
    """Returns on-chain intelligence summary."""
    try:
        return await onchain_data.build_onchain_summary()
    except Exception as e:
        logger.error(f"Error fetching on-chain context: {e}")
        return "On-chain data unavailable."

def get_journal_context(limit=5):
    """Returns recent journal entries."""
    try:
        journal = database.get_journal_entries(limit=limit)
        if not journal:
            return "No recent journal entries."
        
        context = "RECENT JOURNAL ENTRIES:\n"
        for entry in journal:
            context += f"- {entry['timestamp']} ({entry['entry_type']}): {entry['content'][:150]}...\n"
        return context
    except Exception as e:
        logger.error(f"Error fetching journal context: {e}")
        return "Journal data unavailable."

def get_alerts_context():
    """Returns active alerts."""
    try:
        alerts = database.get_active_alerts()
        if not alerts:
            return "No active alerts."
        
        context = "YOUR ACTIVE ALERTS:\n"
        for a in alerts:
            context += f"- ID #{a['id']}: {a['symbol']} {a['direction']} ${a['target_price']}\n"
        return context
    except Exception as e:
        logger.error(f"Error fetching alerts context: {e}")
        return "Alerts data unavailable."

def get_beliefs_context(limit=5):
    """Returns current AI belief state."""
    try:
        beliefs = database.get_connection().execute("SELECT belief_key, direction, confidence FROM belief_state").fetchall()
        if not beliefs:
            return "No current beliefs stored."
        
        context = "CURRENT BELIEFS:\n"
        for b in beliefs[:limit]:
            context += f"- {b[0]}: {b[1]} (Confidence: {b[2]*100:.0f}%)\n"
        return context
    except Exception as e:
        logger.error(f"Error fetching beliefs context: {e}")
        return "Belief state unavailable."

def get_reputation_context():
    """Returns formatted airdrop reputation if wallet is linked."""
    try:
        linked_wallet = database.get_scanner_setting('linked_wallet', None)
        if not linked_wallet:
            return ""
            
        metrics = database.get_wallet_metrics(linked_wallet)
        if not metrics:
            return ""
            
        from crypto_agent.airdrop.wallet_scorer import WalletScorer
        scorer = WalletScorer()
        res = scorer.score_wallet(metrics)
        context = f"YOUR AIRDROP REPUTATION: {res['composite_score']}/100 ({res['grade']})\n"
        if res['gaps_to_address']:
            context += f"Recommended actions: {', '.join(res['gaps_to_address'][:2])}\n"
        return context
    except Exception as e:
        logger.error(f"Error fetching reputation context: {e}")
        return ""

async def build_full_context():
    """Legacy wrapper for compatibility - composes all modules."""
    portfolio = await get_portfolio_context()
    market = await get_market_context()
    onchain = await get_onchain_context()
    journal = get_journal_context()
    alerts = get_alerts_context()
    beliefs = get_beliefs_context()
    reputation = get_reputation_context()
    
    context = "--- REAL-TIME CONTEXT ---\n\n"
    context += f"{portfolio}\n\n"
    context += f"{alerts}\n\n"
    context += f"{market}\n\n"
    context += f"{onchain}\n\n"
    context += f"{journal}\n\n"
    context += "--- MY AGENT INTELLIGENCE ---\n"
    context += f"{beliefs}\n"
    if reputation:
        context += f"\n{reputation}"
        
    return context

async def get_feature_context(feature_name: str, symbol: str = None):
    """
    CANONICAL API: Returns context tailored for a specific feature.
    Example: get_feature_context('execution_guard', 'BTC')
    """
    context_parts = []
    
    if feature_name == 'execution_guard':
        context_parts.append(await get_portfolio_context())
        context_parts.append(get_alerts_context())
        context_parts.append(get_journal_context(limit=3))
        context_parts.append(database.get_notes_for_context()) # User rules
    
    elif feature_name == 'research':
        context_parts.append(await get_market_context())
        context_parts.append(await get_onchain_context())
        context_parts.append(get_beliefs_context())
        
    elif feature_name == 'airdrop':
        context_parts.append(get_reputation_context())
        context_parts.append(await get_onchain_context())
        
    else:
        # Default fallback to full context
        return await build_full_context()
        
    return "\n\n".join([p for p in context_parts if p])
