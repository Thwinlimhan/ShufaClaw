import logging
from crypto_agent.data import technical as technical_analysis
from crypto_agent.data import market as market_service
from crypto_agent.storage import database
from crypto_agent.data import prices as price_service
from crypto_agent.intelligence.analyst import get_ai_response
from crypto_agent.intelligence import performance_tracker

logger = logging.getLogger(__name__)

def detect_trade_question(message):
    """Detects if a message is asking for a trading decision/advice."""
    keywords = [
        "should i", "thinking about", "buy", "sell", "take profits", 
        "enter", "exit", "position", "worth it", "good time", "looking at",
        "long", "short", "trade"
    ]
    ms_lower = message.lower()
    return any(k in ms_lower for k in keywords)

async def analyze_trade_idea(symbol, user_question):
    """Gathers rich context and asks Claude for a strategic trade analysis."""
    symbol = symbol.upper()
    
    try:
        # 1. Fetch Technical Analysis
        ta_data = await technical_analysis.analyze_coin(symbol, timeframe='4h')
        ta_report = technical_analysis.format_analysis_for_telegram(ta_data) if ta_data else "No TA data available."
        
        # 2. Fetch Market Overview
        market_data = await market_service.build_market_context_for_claude()
        
        # 3. Fetch Portfolio Data for this symbol
        pos = database.get_position(symbol)
        portfolio_info = f"You hold {pos['quantity']} {symbol}." if pos else f"You currently have no position in {symbol}."
        
        # 4. Fetch User Notes for this symbol
        notes = database.get_notes_by_symbol(symbol)
        notes_text = "\n".join([f"- {n['content']}" for n in notes]) if notes else "No specific notes for this symbol."
        
        # 5. Build the massive strategic prompt
        prompt = (
            f"The trader is asking: \"{user_question}\"\n\n"
            f"TECHNICAL ANALYSIS ({symbol} 4H):\n{ta_report}\n\n"
            f"MARKET CONTEXT:\n{market_data}\n\n"
            f"THEIR PORTFOLIO:\n{portfolio_info}\n\n"
            f"THEIR NOTES ABOUT {symbol}:\n{notes_text}\n\n"
            "Based on this actual data, provide a structured trading analysis:\n"
            "1. Technical setup: What do the indicators say about this entry/exit?\n"
            "2. Market context: Is the broader market trend helping or hurting this idea?\n"
            "3. Risk assessment: What are the key levels they might be wrong at?\n"
            "4. A suggested plan: Specific entry/exit/stop levels if they act.\n\n"
            "Be direct and reference real price levels from the data. Keep it under 200 words."
        )
        
        analysis = await get_ai_response([{"role": "user", "content": prompt}])
        
        # --- NEW: Record analysis & identify predictions ---
        if analysis:
            database.log_advice(user_question, analysis[:500], symbol, actionable=1)
            
            # Simple heuristic for prediction extraction
            a_lower = analysis.lower()
            p_type = None
            if any(w in a_lower for w in ["bullish", "buy call", "uptrend continuing", "strong long"]): p_type = "bullish"
            elif any(w in a_lower for w in ["bearish", "sell call", "downtrend persists", "short setup"]): p_type = "bearish"
            
            if p_type and ta_data:
                tracker = performance_tracker.PerformanceTracker()
                tracker.record_prediction(symbol, p_type, ta_data['price'], analysis[:200])

        return analysis

    except Exception as e:
        logger.error(f"Error in analyze_trade_idea: {e}")
        return None

async def compare_assets(symbol1, symbol2):
    """Compares two assets side-by-side."""
    s1, s2 = symbol1.upper(), symbol2.upper()
    
    ta1 = await technical_analysis.analyze_coin(s1, '4h')
    ta2 = await technical_analysis.analyze_coin(s2, '4h')
    
    r1 = technical_analysis.format_analysis_for_telegram(ta1) if ta1 else f"No data for {s1}"
    r2 = technical_analysis.format_analysis_for_telegram(ta2) if ta2 else f"No data for {s2}"
    
    prompt = (
        f"Compare {s1} and {s2} based on this technical data:\n\n"
        f"DATA for {s1}:\n{r1}\n\n"
        f"DATA for {s2}:\n{r2}\n\n"
        "Analyze:\n"
        "1. Which asset shows more relative strength right now?\n"
        "2. Which has a better risk/reward setup?\n\n"
        "Be brief and give a clear winner if one exists."
    )
    
    comparison = await get_ai_response([{"role": "user", "content": prompt}])
    return comparison
