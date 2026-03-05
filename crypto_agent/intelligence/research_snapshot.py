import logging
import asyncio
import json
from datetime import datetime
from crypto_agent.storage import database
from crypto_agent.data import prices as price_service
from crypto_agent.data import market as market_service
from crypto_agent.data import technical as ta
from crypto_agent.data import news as news_service
from crypto_agent.data import onchain as onchain_service
# These might not exist yet but we will import safely or mock
try:
    from crypto_agent.data.institutional import tracker as inst_tracker
except ImportError:
    inst_tracker = None

try:
    from crypto_agent.data.social import social_intelligence as social_service
except ImportError:
    social_service = None

logger = logging.getLogger(__name__)

async def get_research_snapshot(symbol: str) -> dict:
    """
    Returns a structured snapshot of all relevant intelligence for a symbol.
    Internally gathers data from multiple services and persists the snapshot.
    """
    symbol = symbol.upper()
    
    # 1. Gather all data in parallel to save time
    tasks = {
        'market': market_service.get_detailed_coin_data(symbol),
        'ta_1h': ta.analyze_coin(symbol, '1h'),
        'ta_4h': ta.analyze_coin(symbol, '4h'),
        'ta_1d': ta.analyze_coin(symbol, '1d'),
        'news': news_service.get_news_for_symbol(symbol, limit=5),
        'sentiment': news_service.get_fear_greed_index()
    }
    
    # Try to fetch alternative data if available
    if social_service:
        tasks['social'] = social_service.get_fomo_score() # Generic market sentiment proxy
        
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    
    gathered = {}
    for i, key in enumerate(tasks.keys()):
        result = results[i]
        gathered[key] = result if not isinstance(result, Exception) else None
        if isinstance(result, Exception):
            logger.warning(f"Error fetching snapshot data for {symbol} ({key}): {result}")

    detailed_market = gathered.get('market')
    if not detailed_market:
        logger.error(f"Cannot build snapshot for {symbol} - missing core market data.")
        return None

    # 2. Gather On-chain & DeFi (Requires coin ID from market data)
    onchain_data = None
    defi_tvl = 0
    if detailed_market:
        coin_id = detailed_market.get('id')
        try:
            defi_tvl = await onchain_service.get_protocol_tvl(coin_id)
        except Exception as e:
            logger.debug(f"Could not fetch TVL for {symbol}: {e}")
            
        # Simplified onchain context if it's an ETH token
        if 'ethereum' in detailed_market.get('platforms', {}):
            contract = detailed_market['platforms']['ethereum']
            try:
                onchain_data = await onchain_service.get_contract_activity(contract)
            except Exception:
                pass

    # 3. Smart Money / Institutional (if available)
    smart_money = None
    if inst_tracker:
        try:
            smart_money = await inst_tracker.get_deribit_dvol() # Proxy for institutional fear
        except Exception:
            pass

    # 4. Construct the structured Research Snapshot
    snapshot = {
        'metadata': {
            'symbol': symbol,
            'name': detailed_market.get('name'),
            'chain': list(detailed_market.get('platforms', {}).keys())[0] if detailed_market.get('platforms') else 'native',
            'timestamp': datetime.now().isoformat()
        },
        'market_data': {
            'price': detailed_market.get('price'),
            'market_cap': detailed_market.get('market_cap'),
            'fdv': detailed_market.get('fdv'),
            'volume_24h': detailed_market.get('total_volume'),
            'change_24h': detailed_market.get('change_24h'),
            'change_7d': detailed_market.get('change_7d'),
            'ath_distance': detailed_market.get('ath_change')
        },
        'technical': {
            '1h': gathered.get('ta_1h'),
            '4h': gathered.get('ta_4h'),
            '1d': gathered.get('ta_1d')
        },
        'onchain': {
            'tvl': defi_tvl,
            'contract_activity': onchain_data
        },
        'news_sentiment': {
            'headlines': [n.get('title') for n in (gathered.get('news') or [])],
            'fear_greed_index': gathered.get('sentiment', {}).get('value')
        },
        'alt_data': {
            'social_fomo': gathered.get('social')
        },
        'smart_money': smart_money,
        'risk_flags': [] # Can be populated by a separate risk engine later
    }

    # Generate a brief text summary for logging and agent consumption
    price = snapshot['market_data']['price']
    ta_1d_rsi = snapshot['technical'].get('1d', {}).get('rsi', 'N/A') if snapshot['technical'].get('1d') else 'N/A'
    summary_text = f"Price: ${price} | 1D RSI: {ta_1d_rsi} | 24h: {snapshot['market_data']['change_24h']}%"

    # 5. Persist the snapshot in the database
    snapshot_payload_json = json.dumps(snapshot, default=str)
    
    # Check if we need to track delta
    last_snap = database.get_latest_research_snapshot(symbol)
    if last_snap:
        # We could calculate delta here and add to snapshot, but for now we just save it.
        pass

    snapshot_id = database.save_research_snapshot(
        symbol=symbol,
        snapshot_payload=snapshot_payload_json,
        source_version="1.0",
        risk_flags=json.dumps(snapshot['risk_flags']),
        summary_text=summary_text
    )
    
    # Attach the DB ID to the returned snapshot so agents can reference it in decisions
    snapshot['snapshot_id'] = snapshot_id
    
    return snapshot
