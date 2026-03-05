import logging
from typing import Dict, Optional, List

from crypto_agent.data.technical import fetch_klines, calculate_atr
from crypto_agent.storage import database as db

logger = logging.getLogger(__name__)

def calculate_kelly_criterion(win_rate: float, reward_risk_ratio: float, fraction: float = 0.5) -> Dict:
    """
    MODEL 1: KELLY CRITERION
    Formula: K = W - [(1 - W) / R]
    W = Win probability
    R = Reward:Risk ratio
    fraction = "Half Kelly" by default, standard for crypto volatility to reduce drawdown.
    """
    if win_rate <= 0 or win_rate >= 1:
        return {"error": "Win rate must be a decimal between 0 and 1 (e.g., 0.55)."}
    if reward_risk_ratio <= 0:
        return {"error": "Reward:Risk ratio must be greater than 0."}
        
    kelly_pct = win_rate - ((1 - win_rate) / reward_risk_ratio)
    
    if kelly_pct <= 0:
        return {
            "is_viable": False,
            "kelly_raw": 0,
            "recommended_pct": 0,
            "message": "Mathematical Edge is negative. Do not take this trade."
        }
        
    recommended_pct = kelly_pct * fraction * 100
    
    # Cap at 10% max for crypto sanity
    if recommended_pct > 10.0:
        recommended_pct = 10.0
        
    return {
        "is_viable": True,
        "kelly_raw": kelly_pct * 100,
        "fraction": fraction,
        "recommended_pct": recommended_pct,
        "message": "Positive expectancy."
    }

async def volatility_adjusted_sizing(symbol: str, total_capital: float, risk_pct: float = 1.0) -> Dict:
    """
    MODEL 2: VOLATILITY-ADJUSTED SIZING (ATR)
    Base size on the Average True Range.
    If a coin is very volatile, size should decrease to maintain a constant $ risk.
    """
    try:
        klines = await fetch_klines(symbol, "1d", 20)
        if not klines or len(klines) < 15:
            return {"error": f"Insufficient data to calculate ATR for {symbol}."}
            
        closes = [float(k[4]) for k in klines]
        current_price = closes[-1]
        
        atr = calculate_atr(klines, period=14)
        if not atr:
            return {"error": "Failed to calculate ATR."}
            
        # If ATR is returned as a list or scalar, ensure we have a float
        atr_val = atr[-1] if hasattr(atr, '__iter__') else atr
        
        # We specify standard stop loss distance as 2x ATR. (common practice)
        stop_loss_dist = 2 * atr_val
        stop_loss_pct = (stop_loss_dist / current_price)
        
        # $ Risk = Total Capital * (Risk_Pct / 100)
        # Position Size = $ Risk / Stop_Loss_Pct
        dollar_risk = total_capital * (risk_pct / 100)
        
        if stop_loss_pct <= 0: return {"error": "Invalid ATR/Stop Loss calculation."}
            
        position_size_usd = dollar_risk / stop_loss_pct
        position_size_units = position_size_usd / current_price
        
        # Max cap at 30% of total capital
        if position_size_usd > (total_capital * 0.30):
            position_size_usd = total_capital * 0.30
            position_size_units = position_size_usd / current_price
            
        return {
            "symbol": symbol.upper(),
            "capital": total_capital,
            "current_price": current_price,
            "atr": atr_val,
            "atr_pct_daily": (atr_val / current_price) * 100,
            "risk_pct_budget": risk_pct,
            "recommended_stop_dist": stop_loss_pct * 100,
            "position_size_usd": position_size_usd,
            "position_size_units": position_size_units
        }
    except Exception as e:
        logger.error(f"Error in ATR sizing model: {e}")
        return {"error": "Failed to run volatility sizing engine."}

def check_portfolio_heat(total_portfolio_usd: float) -> Dict:
    """
    MODEL 3: PORTFOLIO HEAT MONITOR
    Aggregates active positions to check total correlation and risk exposure.
    """
    try:
        positions = db.get_all_positions()
        
        if not positions:
            return {
                "active_positions": 0,
                "total_invested": 0.0,
                "heat_index": 0.0,
                "status": "Cold - No Positions"
            }
            
        # positions is list of dicts: {"symbol", "quantity", "avg_price", "notes"}
        total_invested = 0.0
        for p in positions:
            qty = p.get("quantity") or 0.0
            price = p.get("avg_price") or 0.0
            total_invested += float(qty) * float(price)
        
        heat_index = (total_invested / total_portfolio_usd) * 100 if total_portfolio_usd else 0
        
        status = "Normal"
        if heat_index > 80:
            status = "🔥 DANGER - Max Exposed (>80%)"
        elif heat_index > 50:
            status = "⚠️ High Portfolio Heat (>50%)"
        elif heat_index < 20:
            status = "🧊 Under-exposed (<20%)"
            
        return {
            "active_positions": len(positions),
            "total_invested": total_invested,
            "portfolio_value": total_portfolio_usd,
            "heat_index": heat_index,
            "status": status
        }
    except Exception as e:
        logger.error(f"Error in heat monitor: {e}")
        return {"error": "Failed to calculate portfolio heat."}


def derive_edge_from_history(limit: int = 50) -> Dict:
    """
    Helper for MODEL 1 using real prediction history.
    Looks at last N resolved predictions and derives:
    - Win rate
    - Average win and loss (in %)
    - Reward:Risk ratio
    """
    try:
        preds = db.get_all_predictions(limit=limit)
        if not preds:
            return {"error": "No prediction history available yet."}

        returns: List[float] = []
        for p in reversed(preds):
            if not p.get("result_24h") or p.get("price_24h") is None:
                continue
            start = p.get("price")
            end = p.get("price_24h")
            if not start or not end:
                continue
            raw_ret = (end - start) / start * 100.0
            direction = (p.get("type") or "").lower()
            if direction == "bearish":
                raw_ret *= -1
            returns.append(raw_ret)

        if len(returns) < 10:
            return {"error": "Need at least 10 resolved predictions to estimate Kelly sizing."}

        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r < 0]
        if not wins or not losses:
            return {"error": "Need both winning and losing trades to estimate edge."}

        win_rate = len(wins) / len(returns)
        avg_win = sum(wins) / len(wins)
        avg_loss = abs(sum(losses) / len(losses))

        if avg_loss == 0:
            return {"error": "Average loss is zero; cannot compute reward:risk ratio."}

        rr = avg_win / avg_loss
        kelly = calculate_kelly_criterion(win_rate, rr)
        if "error" in kelly:
            return kelly

        kelly.update({
            "samples": len(returns),
            "win_rate": win_rate * 100,
            "avg_win": avg_win,
            "avg_loss": -avg_loss,
        })
        return kelly
    except Exception as e:
        logger.error(f"Error deriving edge from history: {e}")
        return {"error": "Failed to derive Kelly inputs from history."}


def evaluate_drawdown_protection(limit: int = 50) -> Dict:
    """
    MODEL 4: DRAWDOWN PROTECTION
    Uses recent prediction outcomes to suggest a sizing multiplier
    based on loss streaks and equity drawdown.
    """
    try:
        preds = db.get_all_predictions(limit=limit)
        if not preds:
            return {"error": "No prediction history available yet."}

        returns: List[float] = []
        equity = 1.0
        peak = 1.0
        max_dd = 0.0

        # Oldest first for equity curve
        for p in reversed(preds):
            if not p.get("result_24h") or p.get("price_24h") is None:
                continue
            start = p.get("price")
            end = p.get("price_24h")
            if not start or not end:
                continue
            r = (end - start) / start * 100.0
            direction = (p.get("type") or "").lower()
            if direction == "bearish":
                r *= -1
            returns.append(r)

            equity *= (1.0 + r / 100.0)
            peak = max(peak, equity)
            dd = (peak - equity) / peak * 100.0
            if dd > max_dd:
                max_dd = dd

        if not returns:
            return {"error": "Not enough resolved predictions to evaluate drawdown."}

        # Current loss streak (from most recent backwards)
        loss_streak = 0
        for r in reversed(returns):
            if r < 0:
                loss_streak += 1
            else:
                break

        current_dd = (peak - equity) / peak * 100.0 if equity < peak else 0.0

        size_multiplier = 1.0
        rule = "Normal sizing — no strong drawdown signal."

        if loss_streak >= 5 or current_dd >= 10.0:
            size_multiplier = 0.25
            rule = "Severe drawdown or 5+ consecutive losses — reduce size by 75% until conditions improve."
        elif loss_streak >= 5 or current_dd >= 7.5:
            size_multiplier = 0.5
            rule = "Meaningful drawdown — reduce size by 50%."
        elif loss_streak >= 3 or current_dd >= 3.0:
            size_multiplier = 0.75
            rule = "Early drawdown phase — reduce size by 25% temporarily."

        return {
            "samples": len(returns),
            "loss_streak": loss_streak,
            "max_drawdown_pct": max_dd,
            "current_drawdown_pct": current_dd,
            "size_multiplier": size_multiplier,
            "rule": rule,
        }
    except Exception as e:
        logger.error(f"Error in drawdown protection model: {e}")
        return {"error": "Failed to evaluate drawdown protection rules."}

def format_sizing_dashboard(kelly=None, volatility=None, heat=None, drawdown: Optional[Dict] = None):
    msg = f"⚖️ **POSITION SIZER & RISK MANAGER**\n\n"
    
    if kelly:
        msg += f"**1. Kelly Criterion (Expectancy Sizing)**\n"
        if "error" in kelly:
            msg += f"❌ {kelly['error']}\n\n"
        elif not kelly['is_viable']:
            msg += f"🚨 **NEGATIVE EDGE.** {kelly['message']}\n\n"
        else:
            msg += f"• Raw Kelly: {kelly['kelly_raw']:.2f}%\n"
            faction_str = "Half-Kelly" if kelly['fraction'] == 0.5 else "Fractional"
            msg += f"• 🎲 Recommended Size ({faction_str}): **{kelly['recommended_pct']:.2f}% of capital**\n\n"
            
    if volatility:
        msg += f"**2. Volatility-Adjusted Target Size (ATR)**\n"
        if "error" in volatility:
            msg += f"❌ {volatility['error']}\n\n"
        else:
            msg += f"• Volatility: **{volatility['atr_pct_daily']:.1f}% daily ATR**\n"
            msg += f"• Allowed Risk: {volatility['risk_pct_budget']:.1f}% of capital\n"
            msg += f"• Recommended Stop (2 ATR): -{volatility['recommended_stop_dist']:.1f}%\n"
            msg += f"• 🎯 Max Size: **${volatility['position_size_usd']:,.2f}** ({volatility['position_size_units']:.4f} {volatility['symbol']})\n\n"
            
    if heat:
        msg += f"**3. Global Portfolio Heat Monitor**\n"
        if "error" in heat:
            msg += f"❌ {heat['error']}\n"
        else:
            msg += f"• Cash vs Deployed: ${heat['portfolio_value'] - heat['total_invested']:,.2f} / ${heat['total_invested']:,.2f}\n"
            msg += f"• Capital Deployed: **{heat['heat_index']:.1f}%**\n"
            msg += f"• State: {heat['status']}\n"
    
    if drawdown:
        msg += f"\n**4. Drawdown Safety Brakes**\n"
        if "error" in drawdown:
            msg += f"❌ {drawdown['error']}\n"
        else:
            msg += (
                f"• Trades analysed: {drawdown.get('samples', 0)} (last window)\n"
                f"• Current loss streak: {drawdown.get('loss_streak', 0)}\n"
                f"• Max drawdown (prediction equity): {drawdown.get('max_drawdown_pct', 0.0):.1f}%\n"
                f"• Current drawdown: {drawdown.get('current_drawdown_pct', 0.0):.1f}%\n"
                f"• Suggested size multiplier: **x{drawdown.get('size_multiplier', 1.0):.2f}**\n"
                f"• Rule: {drawdown.get('rule', '')}\n"
            )

    return msg
