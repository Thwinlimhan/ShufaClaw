import logging
import asyncio
from datetime import datetime
import pytz
from crypto_agent.storage import database
from crypto_agent.data import prices as price_service, market as market_service
from crypto_agent.intelligence.analyst import get_ai_response
from crypto_agent import config

logger = logging.getLogger(__name__)

class MarketScanner:
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id
        # Use Myanmar Time as per project defaults
        self.tz = pytz.timezone('Asia/Yangon')

    async def run_scan(self):
        """Orchestrates all scanning tasks."""
        status = database.get_scanner_setting('status', 'on')
        if status == 'off':
            return

        logger.info("Executing periodic market scan...")
        
        try:
            # 1. Take Snapshot and Monitor Market Structure (Scan 3)
            await self.monitor_market_structure()
            
            # 2. Fetch market data for movers (Scan 1)
            await self.scan_movers()
            
            # 3. Correlation Breaks (Scan 4)
            await self.check_correlations()
            
            # 4. Portfolio Health (Scan 5)
            await self.check_portfolio_health()

            # 5. Opportunity Scans (Hourly and 4-hourly)
            now = datetime.now(self.tz)
            if now.minute < 5:  # Hourly checks
                await self.scan_oversold_coins()
                await self.scan_funding_extremes()
                await self.scan_90day_highs()
                
                if now.hour % 4 == 0:  # 4-hourly checks
                    await self.scan_rotation()
            
            # 6. Portfolio News (Every 30 mins)
            if now.minute % 30 == 0:
                await self.scan_portfolio_news()
            
        except Exception as e:
            logger.error(f"Error during market scan: {e}")

    async def scan_oversold_coins(self):
        """Opportunity Scan 1: RSI < 35, Above 200 SMA, Vol Declining."""
        if database.get_scanner_setting('scan_oversold') == 'off': return
        
        # Get top 50, but filter to top 30
        coins = await market_service.get_top_cryptos(50)
        top_30_symbols = [c['symbol'] for c in coins[:30]]
        
        from crypto_agent.data import technical as ta
        
        for symbol in top_30_symbols:
            try:
                # 4h RSI check
                analysis = await ta.analyze_coin(symbol, '4h')
                if not analysis or analysis['rsi'] is None or analysis['rsi'] >= 35:
                    continue
                
                # Use daily for 200 SMA
                daily_analysis = await ta.analyze_coin(symbol, '1d')
                if not daily_analysis or not daily_analysis['sma200']:
                    continue
                
                # Condition: Price > 200 SMA (Uptrend)
                if analysis['price'] < daily_analysis['sma200']:
                    continue
                
                # Condition: Volume declining (last 3 4h bars average < 20 bar average)
                klines = await ta.fetch_klines(symbol, '4h', 30)
                if len(klines) < 20: continue
                volumes = [float(k[5]) for k in klines]
                recent_vol = sum(volumes[-3:]) / 3
                avg_vol = sum(volumes[-20:]) / 20
                
                if recent_vol < avg_vol:
                    if not database.was_recently_alerted('opportunity', f"oversold_{symbol}", hours=24):
                        msg = (
                            f"💡 **OPPORTUNITY RADAR**\n\n"
                            f"**{symbol}** showing oversold on 4h\n"
                            f"RSI: {analysis['rsi']:.1f} (Oversold)\n"
                            f"Still above 200 SMA: Yes ✅\n"
                            f"Volume: Declining ✅\n\n"
                            f"Historically, {symbol} at these levels with this setup often sees a bounce.\n"
                            f"/ta {symbol} 4h for full analysis"
                        )
                        await self.notify(msg, 'opportunity', f"oversold_{symbol}")
            except Exception as e:
                logger.error(f"Error scanning oversold for {symbol}: {e}")

    async def scan_funding_extremes(self):
        """Opportunity Scan 2: Funding rate extremes."""
        if database.get_scanner_setting('scan_funding') == 'off': return
        
        symbols = ['BTC', 'ETH', 'SOL']
        for symbol in symbols:
            rate = await price_service.get_funding_rate(symbol)
            if rate is None: continue
            
            # Annualized rate approx
            # overheated > 0.08% per 8h
            if rate > 0.0008:
                if not database.was_recently_alerted('funding', f"high_{symbol}", hours=12):
                    msg = f"⚠ **{symbol} FUNDING ALERT**\n\nFunding rate extremely elevated at **{rate*100:.3f}%**. Long squeeze risk is high."
                    await self.notify(msg, 'funding', f"high_{symbol}")
            
            # negative < -0.04% per 8h
            elif rate < -0.0004:
                if not database.was_recently_alerted('funding', f"low_{symbol}", hours=12):
                    msg = f"🚀 **{symbol} FUNDING ALERT**\n\nFunding rate deeply negative at **{rate*100:.3f}%**. Short squeeze conditions building."
                    await self.notify(msg, 'funding', f"low_{symbol}")

    async def scan_90day_highs(self):
        """Opportunity Scan 3: Break of 90-day high."""
        if database.get_scanner_setting('scan_ath') == 'off': return
        
        coins = await market_service.get_top_cryptos(20)
        symbols = [c['symbol'] for c in coins]
        
        from crypto_agent.data import technical as ta
        for symbol in symbols:
            klines = await ta.fetch_klines(symbol, '1d', 91)
            if len(klines) < 90: continue
            
            closes = [float(k[4]) for k in klines]
            current_price = closes[-1]
            prev_90d_high = max(closes[:-1])
            
            if current_price > prev_90d_high:
                if not database.was_recently_alerted('ath', symbol, hours=48):
                    msg = (
                        f"🚀 **90-DAY HIGH BREAKOUT**\n\n"
                        f"**{symbol}** just broke its 90-day high at **${current_price:,.2f}**.\n"
                        "Price discovery territory — momentum often continues when ATHs are cleared."
                    )
                    await self.notify(msg, 'ath', symbol)

    async def scan_rotation(self):
        """Opportunity Scan 4: Sector rotation detection (Every 4h)."""
        if database.get_scanner_setting('scan_rotation') == 'off': return
        
        sectors = {
            'Layer 1s': ['BTC', 'ETH', 'SOL', 'ADA', 'AVAX'],
            'DeFi': ['UNI', 'AAVE', 'COMP', 'MKR', 'CRV'],
            'AI tokens': ['FET', 'TAO', 'RENDER', 'NEAR'], # Swapped AGIX/OCEAN for FET/RENDER/NEAR common ones
            'Gaming': ['AXS', 'SAND', 'MANA', 'IMX'],
            'Layer 2s': ['MATIC', 'ARB', 'OP', 'ZKSYNC']
        }
        
        sector_perf = {}
        all_coins = []
        for s_coins in sectors.values():
            all_coins.extend(s_coins)
            
        prices = await price_service.get_multiple_prices(all_coins)
        
        market_total_ch = 0
        count = 0
        
        for name, s_coins in sectors.items():
            total_ch = 0
            valid_count = 0
            for symbol in s_coins:
                if symbol in prices:
                    total_ch += prices[symbol]['change_24h']
                    valid_count += 1
                    market_total_ch += prices[symbol]['change_24h']
                    count += 1
            if valid_count > 0:
                sector_perf[name] = total_ch / valid_count
        
        if count == 0: return
        market_avg = market_total_ch / count
        
        for name, avg in sector_perf.items():
            # If sector is significantly outperforming (2x average gain and > 3% gain)
            if market_avg > 0 and avg > (market_avg * 2) and avg > 3:
                if not database.was_recently_alerted('rotation', name, hours=24):
                    msg = (
                        f"🔄 **SECTOR ROTATION ALERT**\n\n"
                        f"**{name}** tokens are outperforming, up avg **{avg:.1f}%** today "
                        f"while overall market average is {market_avg:.1f}%.\n"
                        f"Sector rotation into {name} narrative detected."
                    )
                    await self.notify(msg, 'rotation', name)
                    
    async def scan_portfolio_news(self):
        """Checks for significant news about portfolio holdings."""
        if database.get_scanner_setting('scan_news') == 'off': return
        
        positions = database.get_all_positions()
        if not positions: return
        
        from crypto_agent.data import news as news_service
        
        for pos in positions:
            symbol = pos['symbol']
            # Find news for this symbol
            news_items = await news_service.get_news_for_symbol(symbol, limit=5)
            if not news_items: continue
            
            # Check if we've already alerted on this recently
            # We use the title of the top news item as the unique key for this coin's news event
            news_key = f"news_{symbol}_{news_items[0]['title'][:30]}"
            if not database.was_recently_alerted('news_alert', news_key, hours=24):
                # Analyze sentiment for these articles
                sentiment = await news_service.analyze_news_sentiment(news_items)
                if not sentiment: continue
                
                # Only alert if sentiment is not Neutral or if it's high impact
                is_significant = sentiment['sentiment'] in ['VERY_BULLISH', 'BULLISH', 'BEARISH', 'VERY_BEARISH']
                
                if is_significant:
                    emoji = "📈" if "BULLISH" in sentiment['sentiment'] else "📉"
                    mood = sentiment['sentiment'].replace("_", " ")
                    msg = (
                        f"📰 **NEWS ALERT — YOUR PORTFOLIO**\n\n"
                        f"**{symbol}** mentioned in {len(news_items)} new articles.\n"
                        f"Sentiment: **{mood}** {emoji}\n\n"
                        f"🔥 **Top Story:** \"{sentiment['top_story']}\"\n\n"
                        f"💡 Use `/news {symbol}` for full breakdown."
                    )
                    await self.notify(msg, 'news_alert', news_key)

    async def monitor_market_structure(self):
        """Scan 3: Is Fear & Greed, dominance, or market cap shifting fast?"""
        overview = await price_service.get_market_overview()
        fng = await price_service.get_fear_greed_index()
        
        if not overview or not fng: return
        
        # Save current snapshot for future comparisons
        database.save_market_snapshot(overview['total_market_cap_usd'], overview['btc_dominance'], fng['value'])
        
        # Check Market Cap Drop (> 3% in 1h approx)
        snap_1h = database.get_snapshot_n_hours_ago(1)
        if snap_1h:
            old_cap = snap_1h['cap']
            new_cap = overview['total_market_cap_usd']
            if old_cap > 0:
                drop_pct = ((old_cap - new_cap) / old_cap) * 100
                if drop_pct >= 3:
                    if not database.was_recently_alerted('market_structure', 'total_cap'):
                        msg = (
                            f"📉 **MARKET CAP ALERT**\n\n"
                            f"Total market cap has dropped **{drop_pct:.1f}%** in the last hour.\n"
                            f"Current: ${new_cap/1e12:.2f}T\n\n"
                            "This sudden drop suggests a broad market sell-off."
                        )
                        await self.notify(msg, 'market_structure', 'total_cap')

        # Check F&G Shift (> 10 points in 2h)
        snap_2h = database.get_snapshot_n_hours_ago(2)
        if snap_2h:
            old_fng = snap_2h['fng']
            new_fng = fng['value']
            if abs(new_fng - old_fng) >= 10:
                if not database.was_recently_alerted('market_structure', 'fng'):
                    dir_str = "improved" if new_fng > old_fng else "declined"
                    msg = (
                        f"🧠 **SENTIMENT SHIFT**\n\n"
                        f"Fear & Greed Index {dir_str} by {abs(new_fng - old_fng)} points in 2 hours.\n"
                        f"Prev: {old_fng} -> Now: {new_fng}\n\n"
                        "Rapid sentiment shifts often lead to high volatility."
                    )
                    await self.notify(msg, 'market_structure', 'fng')

        # Check BTC Dominance (> 1% in 4h)
        snap_4h = database.get_snapshot_n_hours_ago(4)
        if snap_4h:
            old_dom = snap_4h['btc_dom']
            new_dom = overview['btc_dominance']
            if abs(new_dom - old_dom) >= 1:
                if not database.was_recently_alerted('market_structure', 'btc_dom'):
                    msg = (
                        f"📊 **DOMINANCE SHIFT**\n\n"
                        f"BTC Dominance changed by **{abs(new_dom - old_dom):.1f}%** in 4 hours.\n"
                        f"Current: {new_dom:.1f}%\n\n"
                        "This usually indicates capital rotation between BTC and Alts."
                    )
                    await self.notify(msg, 'market_structure', 'btc_dom')

    async def scan_movers(self):
        """Scan 1: Look for coins moving > 8% (top 100) or > 5% (portfolio)."""
        coins = await market_service.get_market_data_for_scanning(100)
        if not coins: return
        
        portfolio = {p['symbol']: p for p in database.get_all_positions()}
        
        for coin in coins:
            symbol = coin['symbol']
            ch1h = coin['change_1h']
            price = coin['price']
            
            is_mover = False
            threshold = 8
            if symbol in portfolio:
                threshold = 5
            
            if abs(ch1h) >= threshold:
                if not database.was_recently_alerted('big_mover', symbol):
                    # AI Analysis
                    prompt = (
                        f"{symbol} just moved {ch1h:.1f}% in one hour. "
                        f"Current price: ${price:,.4f}. Volume is active.\n"
                        "In 2 sentences, what are the most likely reasons and should this be on my radar?"
                    )
                    ai_take = await get_ai_response([{"role": "user", "content": prompt}])
                    
                    emoji = "📈" if ch1h > 0 else "📉"
                    rel = "Yes" if symbol in portfolio else "No"
                    
                    msg = (
                        f"🚨 **SIGNIFICANT MOVE DETECTED**\n\n"
                        f"{emoji} **{symbol} {ch1h:+.1f}%** in last hour\n"
                        f"Current: ${price:,.4f}\n\n"
                        f"🤖 **AI Take:** {ai_take or 'Market volatility detected.'}\n\n"
                        f"Related to portfolio? {rel}\n"
                        f"Want full analysis? `/analyze {symbol}`"
                    )
                    await self.notify(msg, 'big_mover', symbol, claude_analysis=ai_take)

    async def check_correlations(self):
        """Scan 4: BTC performing well while ETH isn't (or vice versa)."""
        if database.was_recently_alerted('correlation_break', 'BTC_ETH', hours=12):
            return
            
        btc_p, btc_ch = await price_service.get_price('BTC')
        eth_p, eth_ch = await price_service.get_price('ETH')
        
        if btc_ch is not None and eth_ch is not None:
            # Check for > 2% divergence
            if (btc_ch > 2 and eth_ch < 0) or (btc_ch < -2 and eth_ch > 0):
                msg = (
                    "📉 **CORRELATION BREAK**\n\n"
                    f"BTC/ETH correlation breaking down — BTC {btc_ch:+.1f}% while ETH {eth_ch:+.1f}%.\n"
                    "Possible rotation signal or underlying weakness in one asset."
                )
                await self.notify(msg, 'correlation_break', 'BTC_ETH')

    async def check_portfolio_health(self):
        """Scan 5: Check if individual positions or total portfolio are dropping fast."""
        positions = database.get_all_positions()
        if not positions: return
        
        total_value = 0
        total_prev_value = 0
        
        for p in positions:
            price, ch24 = await price_service.get_price(p['symbol'])
            if price:
                cur_val = p['quantity'] * price
                total_value += cur_val
                prev_val = cur_val / (1 + (ch24/100)) if ch24 else cur_val
                total_prev_value += prev_val
                
                # Check individual drop > 7%
                if ch24 <= -7:
                    if not database.was_recently_alerted('portfolio_health', p['symbol'], hours=12):
                        msg = f"⚠️ **POSITION ALERT**\n\nYour **{p['symbol']}** position is down **{ch24:.1f}%** from yesterday."
                        await self.notify(msg, 'portfolio_health', p['symbol'])

        if total_prev_value > 0:
            total_ch = ((total_value - total_prev_value) / total_prev_value) * 100
            # Check total portfolio drop > 5%
            if total_ch <= -5:
                if not database.was_recently_alerted('portfolio_risk', 'total', hours=12):
                    msg = (
                        f"🚨 **PORTFOLIO RISK ALERT**\n\n"
                        f"Your total portfolio value is down **{total_ch:.1f}%** from yesterday.\n"
                        f"Current Value: ${total_value:,.2f}"
                    )
                    await self.notify(msg, 'portfolio_risk', 'total')

    async def notify(self, message, scan_type, symbol, claude_analysis=None):
        """Sends notification ensuring night-mode and duplicate filters."""
        # Sensitivity check would go here if we had detailed logic for it
        
        # Night mode: midnight to 7am Myanmar Time
        now = datetime.now(self.tz)
        is_night = now.hour >= 0 and now.hour < 7
        
        # Only notify critical at night
        is_critical = scan_type in ['portfolio_risk', 'market_structure']
        
        if is_night and not is_critical:
            # Drop but log as not notified
            database.log_scanner_event(scan_type, symbol, message, was_notified=0, claude_analysis=claude_analysis)
            return

        # Log and send
        database.log_scanner_event(scan_type, symbol, message, was_notified=1, claude_analysis=claude_analysis)
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send scanner notification: {e}")
