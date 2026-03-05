import logging
import asyncio
from datetime import datetime
from crypto_agent import config
from crypto_agent.storage import database
from crypto_agent.data import prices as price_service
from crypto_agent.data import market as market_service
from crypto_agent.data import technical as ta
from crypto_agent.data import news as news_service
from crypto_agent.data import onchain as onchain_service
from crypto_agent.intelligence.analyst import get_ai_response

logger = logging.getLogger(__name__)

class ResearchAgent:
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id

    async def announce_start(self, symbol):
        """Announces the start of deep research."""
        msg = (
            f"🔍 **Starting deep research on {symbol.upper()}...**\n"
            "This will take 2-3 minutes. I'll gather:\n"
            "✓ Price history and technicals\n"
            "✓ On-chain metrics\n"
            "✓ Recent news and sentiment\n"
            "✓ Community activity\n"
            "✓ Fundamental analysis\n\n"
            "I'll send the full report when complete."
        )
        await self.bot.send_message(chat_id=self.chat_id, text=msg, parse_mode='Markdown')

    async def research_coin(self, symbol):
        """Main method to conduct research and report using the unified Snapshot API."""
        from crypto_agent.intelligence.research_snapshot import get_research_snapshot
        
        symbol = symbol.upper()
        await self.announce_start(symbol)
        
        # 1. Fetch unified data structure
        try:
            snapshot = await get_research_snapshot(symbol)
        except Exception as e:
            logger.error(f"Error getting snapshot for {symbol}: {e}")
            snapshot = None

        if not snapshot or not snapshot.get('market_data'):
            await self.bot.send_message(chat_id=self.chat_id, text=f"❌ Could not find reliable data for {symbol}.")
            return

        # 2. Synthesis using the standardized snapshot
        data = snapshot
        news_headlines = "\n".join([f"- {n}" for n in data['news_sentiment']['headlines']])
        
        prompt = (
            f"You are analyzing {symbol} for a professional crypto trader.\n"
            f"Here is all the data gathered from the Research Snapshot:\n\n"
            f"--- MARKET DATA ---\n"
            f"Price: ${data['market_data'].get('price', 'N/A')}\n"
            f"ATH Distance: {data['market_data'].get('ath_distance', 'N/A')}%\n"
            f"Market Cap: ${data['market_data'].get('market_cap', 0)/1e9:.2f}B\n"
            f"24h Vol: ${data['market_data'].get('volume_24h', 0)/1e6:.1f}M\n"
            f"Price Changes: 24h: {data['market_data'].get('change_24h', 'N/A')}%, 7d: {data['market_data'].get('change_7d', 'N/A')}%\n\n"
            
            f"--- TECHNICALS ---\n"
            f"1h RSI: {data['technical'].get('1h', {}).get('rsi', 'N/A') if data['technical'].get('1h') else 'N/A'}\n"
            f"4h RSI: {data['technical'].get('4h', {}).get('rsi', 'N/A') if data['technical'].get('4h') else 'N/A'}\n"
            f"Daily RSI: {data['technical'].get('1d', {}).get('rsi', 'N/A') if data['technical'].get('1d') else 'N/A'}\n\n"
            
            f"--- NEWS & SENTIMENT ---\n"
            f"Fear & Greed Index: {data['news_sentiment'].get('fear_greed_index', 'N/A')}\n"
            f"{news_headlines if news_headlines else 'No recent major headlines.'}\n\n"
            
            f"--- ON-CHAIN & DEFI ---\n"
            f"Protocol TVL: ${data['onchain'].get('tvl', 0)/1e6:.1f}M\n\n"
            
            "Write a comprehensive research report covering:\n"
            "1. EXECUTIVE SUMMARY (3 sentences max): What is this, and what's the current situation?\n"
            "2. TECHNICAL PICTURE: What do the charts say across timeframes?\n"
            "3. FUNDAMENTAL STRENGTH: Does the data support the valuation?\n"
            "4. CATALYSTS & RISKS: What could move this significantly up or down?\n"
            "5. FINAL VERDICT: Must exactly be one of: STRONG_BUY, BUY, NEUTRAL, AVOID, STRONG_AVOID, WATCHLIST, SPECULATIVE, CORE_CANDIDATE\n"
            "6. HORIZON: Must be exactly one of: 24H, 7D, 30D, CYCLE\n"
            "7. CONFIDENCE: Must be a number between 0 and 100\n\n"
            "Ensure sections 5, 6, and 7 are clearly identifiable and strictly follow the formatting constraint."
        )

        report = await get_ai_response([{"role": "user", "content": prompt}])
        
        if report:
            # Send Report to User
            await self.bot.send_message(chat_id=self.chat_id, text=report, parse_mode='Markdown')
            
            # Save to Journal
            # Use appropriate log_entry arguments or standard insert if log_entry isn't directly available
            try:
                 database.add_journal_entry(
                     entry_type='research', 
                     content=f"AUTO RESEARCH REPORT FOR {symbol}:\n\n{report[:1000]}...",
                     symbol=symbol
                 )
            except Exception as e:
                 logger.error(f"Failed to save journal record: {e}")
            
            # Extract structured verdict for logging
            verdict = "NEUTRAL"
            horizon = "7D"
            confidence = 50
            
            for line in report.split('\n'):
                line_u = line.upper()
                if "VERDICT:" in line_u:
                    for v in ['STRONG_BUY', 'BUY', 'NEUTRAL', 'AVOID', 'STRONG_AVOID', 'WATCHLIST', 'SPECULATIVE', 'CORE_CANDIDATE']:
                        if v in line_u:
                            verdict = v
                            break
                elif "HORIZON:" in line_u:
                    for h in ['24H', '7D', '30D', 'CYCLE']:
                        if h in line_u:
                            horizon = h
                            break
                elif "CONFIDENCE:" in line_u:
                     import re
                     match = re.search(r'\d+', line_u)
                     if match:
                         confidence = int(match.group())

            # Log to Agent Decisions
            try:
                database.log_agent_decision(
                    agent_name="DeepResearchAgent",
                    skill_name="research_coin",
                    input_type="SYMBOL",
                    input_payload=f'{{"symbol": "{symbol}"}}',
                    context_snapshot_id=snapshot.get('snapshot_id'),
                    recommendation=report[:250] + "...",
                    prediction_type="EV_CATEGORY",
                    prediction_horizon=horizon,
                    explicit_prediction=verdict,
                    confidence_score=confidence
                )
            except Exception as e:
                logger.error(f"Failed to log agent decision: {e}")

            # Update Watchlist if exists
            try:
                # We need a proper query to update last_researched. This was referenced in original.
                conn = database.get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE research_watchlist SET last_researched = ? WHERE symbol = ?", 
                              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), symbol))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.warning(f"Could not update watchlist: {e}")

        else:
            await self.bot.send_message(chat_id=self.chat_id, text="❌ Research synthesis failed.")

    async def compare_coins(self, symbols_list):
        """Compares multiple coins side-by-side."""
        await self.bot.send_message(chat_id=self.chat_id, text=f"⚔️ **Battle of the Titans: {', '.join(symbols_list)}**\nGathering comparative intelligence...")
        
        gathered_data = []
        for s in symbols_list:
            d = await market_service.get_detailed_coin_data(s)
            if d:
                gathered_data.append(d)
        
        if len(gathered_data) < 2:
            await self.bot.send_message(chat_id=self.chat_id, text="❌ Not enough valid coins to compare.")
            return

        summary = ""
        for d in gathered_data:
            summary += (
                f"- {d['symbol']} ({d['name']}): Price ${d['price']}, 7d: {d['change_7d']:+.1f}%, MC: ${d['market_cap']/1e9:.1f}B, "
                f"ATH Distance: {d['ath_change']:.1f}%\n"
            )
            
        prompt = (
            f"I am comparing these cryptocurrencies:\n{summary}\n\n"
            "Rank them from #1 to #N in terms of current investment opportunity. "
            "For each, provide a 1-sentence rationale highlighting one unique strength or risk. "
            "End with a clear recommendation on which one is best for a 'Swing Trade' (1-4 weeks). "
            "Keep it brief and conversational for Telegram."
        )
        
        comparison = await get_ai_response([{"role": "user", "content": prompt}])
        if comparison:
            await self.bot.send_message(chat_id=self.chat_id, text=f"📊 **COMPARISON REPORT**\n\n{comparison}", parse_mode='Markdown')
        else:
            await self.bot.send_message(chat_id=self.chat_id, text="❌ Comparison analysis failed.")

    async def run_automated_research(self):
        """Runs research for everyone in the watchlist (Weekly)."""
        watchlist = database.get_research_watchlist()
        if not watchlist:
            return
            
        logger.info(f"Running automated weekly research for {len(watchlist)} coins...")
        for item in watchlist:
            if item.get('auto_research') == 1:
                try:
                    await self.bot.send_message(
                        chat_id=self.chat_id, 
                        text=f"🗓️ **WEEKLY AUTO-RESEARCH**\nGenerating scheduled report for **{item['symbol']}**..."
                    )
                    await self.research_coin(item['symbol'])
                    # Sleep a bit to avoid hitting rate limits too fast
                    await asyncio.sleep(60) 
                except Exception as e:
                    logger.error(f"Failed auto-research for {item['symbol']}: {e}")
