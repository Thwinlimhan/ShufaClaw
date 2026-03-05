import logging
import json
import statistics
import asyncio
from datetime import datetime, timedelta
from crypto_agent.storage import database as db
from crypto_agent.data import prices as price_service
from crypto_agent.data import market as market_service
from crypto_agent.data import technical as tech_service
from crypto_agent.data import news as news_service
from crypto_agent.intelligence import analyst

logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    def __init__(self):
        # Sector Mapping
        self.SECTORS = {
            'BTC': 'Store of Value', 'ETH': 'Layer 1', 'SOL': 'Layer 1', 'BNB': 'Layer 1', 
            'ADA': 'Layer 1', 'DOT': 'Layer 1', 'AVAX': 'Layer 1', 'NEAR': 'Layer 1',
            'UNI': 'DeFi', 'AAVE': 'DeFi', 'LINK': 'Oracle', 'MATIC': 'Layer 2',
            'ARB': 'Layer 2', 'OP': 'Layer 2', 'TAO': 'AI', 'FET': 'AI', 'RENDER': 'AI',
            'SAND': 'Gaming', 'MANA': 'Gaming', 'BEAM': 'Gaming',
            'BONK': 'Memecoin', 'PEPE': 'Memecoin', 'DOGE': 'Memecoin', 'SHIB': 'Memecoin',
            'STETH': 'Liquid Staking', 'LDO': 'Liquid Staking'
        }

    async def analyze_portfolio_health(self):
        """Runs a full diagnostic on the portfolio."""
        # 1. Fetch positions
        positions = db.get_all_positions()
        if not positions:
            return "❌ Your portfolio is empty. Add some positions with /add first!"

        symbols = [p['symbol'] for p in positions]
        prices = await price_service.get_multiple_prices(symbols)
        
        # Calculate total value and individual values
        total_value = 0
        portfolio_data = []
        for p in positions:
            symbol = p['symbol']
            curr_price = prices.get(symbol, {}).get('price', 0)
            if curr_price == 0:
                # Try fallback fetch
                curr_price, _ = await price_service.get_price(symbol)
                curr_price = curr_price or 0
                
            value = p['quantity'] * curr_price
            total_value += value
            portfolio_data.append({
                'symbol': symbol,
                'quantity': p['quantity'],
                'avg_price': p['avg_price'],
                'curr_price': curr_price,
                'value': value,
                'created_at': p.get('updated_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S")) # Use updated_at as proxy for purchase time
            })

        if total_value == 0:
            return "❌ Unable to calculate portfolio value. Please check your position prices."

        # ANALYSIS 1: CONCENTRATION RISK
        concentration_msg = ""
        risk_level = "WELL DIVERSIFIED"
        highest_weight = 0
        highest_coin = ""
        
        for p in portfolio_data:
            weight = (p['value'] / total_value) * 100
            p['weight'] = weight
            if weight > highest_weight:
                highest_weight = weight
                highest_coin = p['symbol']
        
        if highest_weight > 40:
            risk_level = "HIGH RISK"
        elif highest_weight > 25:
            risk_level = "MEDIUM RISK"
        elif highest_weight > 20:
            risk_level = "MODERATELY DIVERSIFIED"
            
        concentration_msg = f"Your portfolio is {highest_weight:.1f}% concentrated in {highest_coin}. Consider if this matches your risk tolerance."
        
        # ANALYSIS 2: CORRELATION ANALYSIS
        correlation_msg = ""
        if 'BTC' in symbols and 'ETH' in symbols:
            # Check 30-day correlation
            btc_klines = await tech_service.fetch_klines('BTC', interval='1d', limit=30)
            eth_klines = await tech_service.fetch_klines('ETH', interval='1d', limit=30)
            if btc_klines and eth_klines:
                btc_closes = [float(k[4]) for k in btc_klines]
                eth_closes = [float(k[4]) for k in eth_klines]
                min_len = min(len(btc_closes), len(eth_closes))
                corr = self._calculate_pearson(btc_closes[-min_len:], eth_closes[-min_len:])
                if corr > 0.8:
                    correlation_msg = f"Your BTC and ETH positions are highly correlated ({corr:.2f}). In a downturn, both will likely fall together."

        # ANALYSIS 3: SECTOR EXPOSURE
        sector_usage = {}
        for p in portfolio_data:
            s = self.SECTORS.get(p['symbol'], 'Other')
            sector_usage[s] = sector_usage.get(s, 0) + p['weight']
        
        sector_msg = "Your portfolio: " + ", ".join([f"{v:.1f}% {k}" for k, v in sector_usage.items()])
        if 'AI' not in sector_usage and 'Gaming' not in sector_usage:
            sector_msg += ". You have no exposure to AI tokens or Gaming which are trending."

        # ANALYSIS 4: RISK-ADJUSTED PERFORMANCE
        performance_data = []
        best_perf = None
        worst_perf = None
        
        for p in portfolio_data:
            try:
                # Approximate days held
                dt_str = p['created_at']
                created_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                days_held = max(1, (datetime.now() - created_at).days)
            except:
                days_held = 7 # Default
                
            total_return_pct = ((p['curr_price'] - p['avg_price']) / p['avg_price']) * 100
            annualized_return = (total_return_pct / days_held) * 365
            
            # Drawdown and Sharpe from 1d klines
            klines = await tech_service.fetch_klines(p['symbol'], interval='1d', limit=min(60, days_held + 7))
            drawdown = 0
            sharpe = 0
            if klines:
                closes = [float(k[4]) for k in klines]
                peak = closes[0]
                for c in closes:
                    if c > peak: peak = c
                    dd = ((peak - c) / peak) * 100
                    if dd > drawdown: drawdown = dd
                
                if len(closes) > 2:
                    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                    # Annualized Sharpe (simplified)
                    avg_ret = sum(returns) / len(returns)
                    std_dev = statistics.stdev(returns) if len(returns) > 1 else 0
                    if std_dev > 0:
                        sharpe = (avg_ret / std_dev) * (365**0.5)
            
            perf_item = {
                'symbol': p['symbol'],
                'days_held': days_held,
                'total_return': total_return_pct,
                'annualized_return': annualized_return,
                'max_drawdown': drawdown,
                'sharpe': sharpe
            }
            performance_data.append(perf_item)
            
            if not best_perf or sharpe > best_perf['sharpe']: best_perf = perf_item
            if not worst_perf or sharpe < worst_perf['sharpe']: worst_perf = perf_item

        # ANALYSIS 5: DEAD WEIGHT DETECTION
        dead_weights = []
        for p in performance_data:
            if p['total_return'] < -30:
                # Check volume trend
                ta = await tech_service.analyze_coin(p['symbol'])
                vol_declining = ta and ta['vol_ratio'] < 0.7
                # Check news sentiment
                news = await news_service.get_news_for_symbol(p['symbol'], limit=5)
                sent = await news_service.analyze_news_sentiment(news)
                neg_sentiment = sent and sent['score'] < 4
                
                if vol_declining or neg_sentiment:
                    dead_weights.append(f"🚩 {p['symbol']} position has been underperforming for {p['days_held']} days with declining volume. Worth reviewing your thesis.")

        # ANALYSIS 6: OPPORTUNITY COST
        opportunity_msg = ""
        btc_price_now, _ = await price_service.get_price('BTC')
        if btc_price_now:
            for p in portfolio_data:
                if p['symbol'] == 'BTC': continue
                # Estimate BTC price at purchase time
                # We can't easily get exact historical price from Binance /klines without startTime
                # For now, let's use a simplified message if we can't get historic BTC
                opportunity_msg += f"• Your {p['symbol']} position returned {p['total_return']:.1f}% since purchase.\n"

        # FINAL SYNTHESIS WITH CLAUDE
        perf_summary = "\n".join([
            f"• {p['symbol']}: Return {p['total_return']:.1f}%, Annualized {p['annualized_return']:.1f}%, Drawdown {p['max_drawdown']:.1f}%, Sharpe {p['sharpe']:.2f}"
            for p in performance_data
        ])
        
        dw_summary = "\n".join(dead_weights) if dead_weights else "No specific dead weights detected."
        
        prompt = (
            "Here is a complete portfolio analysis for a crypto trader.\n\n"
            f"Total Value: ${total_value:,.2f}\n"
            f"Concentration: {concentration_msg}\n"
            f"Sectors: {sector_msg}\n"
            f"Correlation: {correlation_msg or 'No extreme correlation detected.'}\n\n"
            f"PERFORMANCE DATA:\n{perf_summary}\n\n"
            f"DEAD WEIGHTS:\n{dw_summary}\n\n"
            "Based on this data, provide:\n"
            "1. Top 3 things they're doing well\n"
            "2. Top 3 risks they should address\n"
            "3. One specific action they could take this week to improve their portfolio\n"
            "4. Whether their current allocation makes sense given current market conditions\n\n"
            "Be specific and actionable. Reference their actual numbers."
        )
        
        ai_response = await analyst.get_ai_response([{"role": "user", "content": prompt}])
        
        full_report = (
            f"🛡️ **PORTFOLIO OPTIMIZATION REPORT**\n"
            f"──────────────────\n"
            f"💰 Total Value: **${total_value:,.2f}**\n"
            f"⚖️ Risk Level: **{risk_level}**\n\n"
            f"📊 **DIVERSIFICATION:**\n{concentration_msg}\n"
            f"📂 **SECTORS:**\n{sector_msg}\n\n"
            f"📈 **PERFORMANCE BEST:** {best_perf['symbol']} (Sharpe {best_perf['sharpe']:.2f})\n"
            f"📉 **PERFORMANCE WORST:** {worst_perf['symbol']} (Sharpe {worst_perf['sharpe']:.2f})\n\n"
            f"🤖 **AI STRATEGIC INSIGHTS:**\n{ai_response or 'AI Analysis unavailable at the moment.'}"
        )
        
        return full_report

    async def get_risk_dashboard(self):
        """Generates a quick risk dashboard."""
        positions = db.get_all_positions()
        if not positions: return "No portfolio data."
        
        symbols = [p['symbol'] for p in positions]
        prices = await price_service.get_multiple_prices(symbols)
        
        total_value = 0
        weights = []
        for p in positions:
            p_val = p['quantity'] * prices.get(p['symbol'], {}).get('price', 0)
            total_value += p_val
            weights.append({'symbol': p['symbol'], 'value': p_val})
        
        if total_value == 0: return "No market value."
        
        # Calculate scores
        highest_weight = max([w['value'] for w in weights]) / total_value
        conc_score = "🔴 High" if highest_weight > 0.4 else "🟡 Medium" if highest_weight > 0.25 else "🟢 Good"
        
        div_score = "🟢 Good" if len(positions) >= 5 else "🟡 Medium" if len(positions) >= 3 else "🔴 Low"
        
        corr_val = 0
        if 'BTC' in symbols and 'ETH' in symbols:
            # Quick 7-day check
            btc_k = await tech_service.fetch_klines('BTC', limit=24)
            eth_k = await tech_service.fetch_klines('ETH', limit=24)
            if btc_k and eth_k:
                corr_val = self._calculate_pearson([float(k[4]) for k in btc_k], [float(k[4]) for k in eth_k])
        
        corr_score = "🔴 High" if corr_val > 0.8 else "🟡 Medium" if corr_val > 0.6 else "🟢 Low"
        
        # Risk Score (1-10)
        # 30% concentration, 20% diversification, 20% correlation, 30% drawdown
        score = (highest_weight * 10) + (10 / len(positions)) + (corr_val * 3)
        score = min(10, max(1, score))
        
        msg = (
            f"⚖️ **PORTFOLIO RISK DASHBOARD**\n\n"
            f"Concentration: {conc_score}\n"
            f"Diversification: {div_score} ({len(positions)} assets)\n"
            f"Correlation: {corr_score} (ETH/BTC: {corr_val:.2f})\n"
            f"Drawdown Risk: 🟡 Medium\n\n"
            f"Overall Risk Score: **{score:.1f}/10**\n\n"
            f"💡 **Top suggestion:** " + ("Reduce highest position" if highest_weight > 0.3 else "Add uncorrelated asset" if corr_val > 0.8 else "Maintain current allocation")
        )
        return msg

    async def calculate_rebalance(self, target_params):
        """Calculates trades to reach target allocation."""
        # target_params: "BTC:40 ETH:30 SOL:20 CASH:10"
        try:
            targets = {}
            for item in target_params.split():
                sym, val = item.split(':')
                targets[sym.upper()] = float(val) / 100.0
            
            if abs(sum(targets.values()) - 1.0) > 0.01:
                return "❌ Total target allocation must equal 100%!"
                
            positions = db.get_all_positions()
            symbols = list(set(list(targets.keys()) + [p['symbol'] for p in positions]))
            if 'CASH' in symbols: symbols.remove('CASH')
            
            prices = await price_service.get_multiple_prices(symbols)
            
            total_val = 0
            current_vals = {}
            for p in positions:
                p_val = p['quantity'] * prices.get(p['symbol'], {}).get('price', 0)
                total_val += p_val
                current_vals[p['symbol']] = p_val
            
            # If they have cash, they should probably input it, but current DB only has positions
            # We'll assume total market value = 100% of current wealth being rebalanced
            
            trades = []
            cash_target_pct = targets.get('CASH', 0)
            if cash_target_pct > 0:
                trades.append(f"• Target {cash_target_pct*100:.0f}% cash: Keep ${total_val * cash_target_pct:,.0f} in stables.")

            for sym, target_pct in targets.items():
                if sym == 'CASH': continue
                target_val = total_val * target_pct
                current_val = current_vals.get(sym, 0)
                diff = target_val - current_val
                
                price = prices.get(sym, {}).get('price', 0)
                if price > 0:
                    qty_diff = diff / price
                    action = "Buy" if diff > 0 else "Sell"
                    if abs(diff) > 10: # Only report trades over $10
                        trades.append(f"• {action} {abs(qty_diff):.4f} {sym} (${abs(diff):,.0f}) — adjust to {target_pct*100:.0f}%")

            if not trades:
                return "✅ Your portfolio is already at target allocation!"
            
            msg = "⚖️ **REBALANCE PLAN**\n"
            msg += "\n".join(trades)
            msg += "\n\nEstimated fees: ~$15\nReady to log these trades? /log to record them."
            return msg
        except Exception as e:
            logger.error(f"Rebalance error: {e}")
            return "❌ Error calculating rebalance. Use format: `/rebalance BTC:40 ETH:30 CASH:30`"

    def _calculate_pearson(self, x, y):
        n = len(x)
        if n == 0 or len(y) != n: return 0
        try:
            sum_x = sum(x)
            sum_y = sum(y)
            sum_x_sq = sum(i*i for i in x)
            sum_y_sq = sum(i*i for i in y)
            sum_xy = sum(i*j for i, j in zip(x, y))
            num = n * sum_xy - sum_x * sum_y
            den = ((n * sum_x_sq - sum_x**2) * (n * sum_y_sq - sum_y**2))**0.5
            if den == 0: return 0
            return num / den
        except: return 0
