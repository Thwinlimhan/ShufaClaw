"""
Options Intelligence Module - Level 29
Monitors options markets from Deribit for trading signals.
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)


@dataclass
class OptionsData:
    """Options market data structure."""
    symbol: str
    put_call_ratio: float
    max_pain: float
    current_price: float
    iv_current: float
    iv_30d_avg: float
    gamma_exposure: float
    unusual_activity: List[Dict]
    timestamp: datetime


class OptionsMonitor:
    """Monitor options markets for trading signals."""
    
    def __init__(self):
        self.base_url = "https://www.deribit.com/api/v2/public"
        self.cache = {}
        self.cache_duration = 3600  # 1 hour
        
    def get_options_data(self, currency: str = "BTC") -> Optional[OptionsData]:
        """
        Fetch comprehensive options data for a currency.
        
        Args:
            currency: BTC, ETH, or SOL
            
        Returns:
            OptionsData object or None if error
        """
        try:
            # Check cache
            cache_key = f"options_{currency}"
            if cache_key in self.cache:
                cached_time, cached_data = self.cache[cache_key]
                if (datetime.now() - cached_time).seconds < self.cache_duration:
                    return cached_data
            
            # Fetch current price
            current_price = self._get_current_price(currency)
            if not current_price:
                return None
            
            # Fetch options book summary
            book_summary = self._get_book_summary(currency)
            if not book_summary:
                return None
            
            # Calculate metrics
            put_call_ratio = self._calculate_put_call_ratio(book_summary)
            max_pain = self._calculate_max_pain(book_summary, current_price)
            iv_current, iv_30d_avg = self._calculate_iv_metrics(book_summary)
            gamma_exposure = self._calculate_gamma_exposure(book_summary, current_price)
            unusual_activity = self._detect_unusual_activity(book_summary)
            
            data = OptionsData(
                symbol=currency,
                put_call_ratio=put_call_ratio,
                max_pain=max_pain,
                current_price=current_price,
                iv_current=iv_current,
                iv_30d_avg=iv_30d_avg,
                gamma_exposure=gamma_exposure,
                unusual_activity=unusual_activity,
                timestamp=datetime.now()
            )
            
            # Cache result
            self.cache[cache_key] = (datetime.now(), data)
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching options data for {currency}: {e}")
            return None
    
    def _get_current_price(self, currency: str) -> Optional[float]:
        """Get current spot price from Deribit index."""
        try:
            url = f"{self.base_url}/get_index_price"
            params = {"index_name": f"{currency.lower()}_usd"}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("result", {}).get("index_price")
        except Exception as e:
            logger.error(f"Error fetching price for {currency}: {e}")
            return None
    
    def _get_book_summary(self, currency: str) -> Optional[List[Dict]]:
        """Get options book summary from Deribit."""
        try:
            url = f"{self.base_url}/get_book_summary_by_currency"
            params = {
                "currency": currency,
                "kind": "option"
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("result", [])
        except Exception as e:
            logger.error(f"Error fetching book summary for {currency}: {e}")
            return None
    
    def _calculate_put_call_ratio(self, book_summary: List[Dict]) -> float:
        """
        Calculate put/call ratio from open interest.
        
        Returns:
            Ratio where <0.7 = very bullish, >1.3 = very bearish
        """
        try:
            total_put_oi = 0
            total_call_oi = 0
            
            for instrument in book_summary:
                instrument_name = instrument.get("instrument_name", "")
                open_interest = instrument.get("open_interest", 0)
                
                if "-P" in instrument_name:  # Put option
                    total_put_oi += open_interest
                elif "-C" in instrument_name:  # Call option
                    total_call_oi += open_interest
            
            if total_call_oi == 0:
                return 0.0
            
            return total_put_oi / total_call_oi
            
        except Exception as e:
            logger.error(f"Error calculating put/call ratio: {e}")
            return 1.0
    
    def _calculate_max_pain(self, book_summary: List[Dict], current_price: float) -> float:
        """
        Calculate max pain - strike where most options expire worthless.
        
        Returns:
            Strike price with maximum pain
        """
        try:
            # Group by strike and expiry
            strikes = {}
            
            for instrument in book_summary:
                instrument_name = instrument.get("instrument_name", "")
                open_interest = instrument.get("open_interest", 0)
                
                # Parse strike from instrument name (e.g., BTC-28FEB25-95000-C)
                parts = instrument_name.split("-")
                if len(parts) >= 4:
                    try:
                        strike = float(parts[2])
                        option_type = parts[3]  # C or P
                        
                        if strike not in strikes:
                            strikes[strike] = {"calls": 0, "puts": 0}
                        
                        if option_type == "C":
                            strikes[strike]["calls"] += open_interest
                        else:
                            strikes[strike]["puts"] += open_interest
                    except ValueError:
                        continue
            
            # Calculate pain at each strike
            max_pain_strike = current_price
            max_pain_value = float('inf')
            
            for strike, oi in strikes.items():
                # Calculate total value lost if price settles at this strike
                call_pain = sum(
                    max(0, strike - s) * strikes[s]["calls"]
                    for s in strikes if s < strike
                )
                put_pain = sum(
                    max(0, s - strike) * strikes[s]["puts"]
                    for s in strikes if s > strike
                )
                total_pain = call_pain + put_pain
                
                if total_pain < max_pain_value:
                    max_pain_value = total_pain
                    max_pain_strike = strike
            
            return max_pain_strike
            
        except Exception as e:
            logger.error(f"Error calculating max pain: {e}")
            return current_price
    
    def _calculate_iv_metrics(self, book_summary: List[Dict]) -> Tuple[float, float]:
        """
        Calculate current IV and 30-day average.
        
        Returns:
            (current_iv, 30d_average_iv)
        """
        try:
            ivs = []
            
            for instrument in book_summary:
                mark_iv = instrument.get("mark_iv")
                if mark_iv and mark_iv > 0:
                    ivs.append(mark_iv)
            
            if not ivs:
                return 0.0, 0.0
            
            current_iv = statistics.mean(ivs)
            # For 30d average, we'd need historical data
            # For now, use current as approximation
            iv_30d_avg = current_iv
            
            return current_iv, iv_30d_avg
            
        except Exception as e:
            logger.error(f"Error calculating IV metrics: {e}")
            return 0.0, 0.0
    
    def _calculate_gamma_exposure(self, book_summary: List[Dict], current_price: float) -> float:
        """
        Calculate gamma exposure (GEX).
        Positive = price moves amplified, Negative = dampened.
        
        Returns:
            Gamma exposure value
        """
        try:
            total_gamma = 0
            
            for instrument in book_summary:
                instrument_name = instrument.get("instrument_name", "")
                open_interest = instrument.get("open_interest", 0)
                greeks = instrument.get("greeks", {})
                gamma = greeks.get("gamma", 0)
                
                # Parse strike
                parts = instrument_name.split("-")
                if len(parts) >= 4:
                    try:
                        strike = float(parts[2])
                        option_type = parts[3]
                        
                        # Weight gamma by proximity to current price
                        distance = abs(strike - current_price) / current_price
                        weight = max(0, 1 - distance * 2)  # Decay with distance
                        
                        # Calls add positive gamma, puts add negative
                        multiplier = 1 if option_type == "C" else -1
                        total_gamma += gamma * open_interest * weight * multiplier
                        
                    except ValueError:
                        continue
            
            return total_gamma
            
        except Exception as e:
            logger.error(f"Error calculating gamma exposure: {e}")
            return 0.0
    
    def _detect_unusual_activity(self, book_summary: List[Dict]) -> List[Dict]:
        """
        Detect unusual options activity (large trades, IV spikes).
        
        Returns:
            List of unusual activity events
        """
        unusual = []
        
        try:
            for instrument in book_summary:
                instrument_name = instrument.get("instrument_name", "")
                volume_usd = instrument.get("volume_usd", 0)
                mark_iv = instrument.get("mark_iv", 0)
                
                # Large volume threshold: $5M
                if volume_usd > 5_000_000:
                    unusual.append({
                        "type": "large_volume",
                        "instrument": instrument_name,
                        "volume_usd": volume_usd,
                        "description": f"${volume_usd/1_000_000:.1f}M volume"
                    })
                
                # High IV threshold: >150%
                if mark_iv > 1.5:
                    unusual.append({
                        "type": "high_iv",
                        "instrument": instrument_name,
                        "iv": mark_iv * 100,
                        "description": f"IV spike to {mark_iv*100:.0f}%"
                    })
            
        except Exception as e:
            logger.error(f"Error detecting unusual activity: {e}")
        
        return unusual
    
    def interpret_put_call_ratio(self, ratio: float) -> str:
        """Interpret put/call ratio sentiment."""
        if ratio < 0.5:
            return "EXTREMELY BULLISH (contrarian top signal)"
        elif ratio < 0.7:
            return "VERY BULLISH"
        elif ratio < 0.9:
            return "MILDLY BULLISH"
        elif ratio <= 1.1:
            return "NEUTRAL"
        elif ratio <= 1.3:
            return "MILDLY BEARISH"
        elif ratio <= 1.5:
            return "VERY BEARISH"
        else:
            return "EXTREMELY BEARISH (contrarian bottom signal)"
    
    def format_options_report(self, data: OptionsData) -> str:
        """Format options data into readable report."""
        try:
            # Put/Call interpretation
            pc_sentiment = self.interpret_put_call_ratio(data.put_call_ratio)
            
            # Max pain distance
            pain_distance = ((data.max_pain - data.current_price) / data.current_price) * 100
            pain_direction = "above" if pain_distance > 0 else "below"
            
            # IV comparison
            iv_comparison = "EXPENSIVE" if data.iv_current > data.iv_30d_avg else "CHEAP"
            iv_diff = ((data.iv_current - data.iv_30d_avg) / data.iv_30d_avg) * 100
            
            # Gamma interpretation
            gex_interpretation = "AMPLIFIED (volatile)" if data.gamma_exposure > 0 else "DAMPENED (stable)"
            
            report = f"""📊 OPTIONS INTELLIGENCE — {data.symbol}

💰 Current Price: ${data.current_price:,.0f}

📈 PUT/CALL RATIO: {data.put_call_ratio:.2f}
   Sentiment: {pc_sentiment}

🎯 MAX PAIN: ${data.max_pain:,.0f}
   Distance: {abs(pain_distance):.1f}% {pain_direction} current
   {"⚠️ Price may gravitate toward max pain near expiry" if abs(pain_distance) > 3 else "✓ Near max pain level"}

📊 IMPLIED VOLATILITY:
   Current: {data.iv_current*100:.1f}%
   30d Avg: {data.iv_30d_avg*100:.1f}%
   Status: {iv_comparison} ({iv_diff:+.1f}%)
   {"💡 Options expensive - potential to sell" if iv_comparison == "EXPENSIVE" else "💡 Options cheap - potential to buy"}

⚡ GAMMA EXPOSURE: {data.gamma_exposure:.2f}
   Effect: {gex_interpretation}
"""
            
            # Add unusual activity if any
            if data.unusual_activity:
                report += "\n🚨 UNUSUAL ACTIVITY:\n"
                for activity in data.unusual_activity[:3]:  # Top 3
                    report += f"   • {activity['description']} - {activity['instrument']}\n"
            
            report += f"\n⏰ Updated: {data.timestamp.strftime('%H:%M:%S')}"
            
            return report
            
        except Exception as e:
            logger.error(f"Error formatting options report: {e}")
            return f"Error formatting report for {data.symbol}"
    
    def get_max_pain_only(self, currency: str = "BTC") -> Optional[float]:
        """Quick max pain lookup."""
        data = self.get_options_data(currency)
        return data.max_pain if data else None
    
    def get_iv_only(self, currency: str = "BTC") -> Optional[float]:
        """Quick IV lookup."""
        data = self.get_options_data(currency)
        return data.iv_current if data else None
    
    def check_for_alerts(self, data: OptionsData) -> List[str]:
        """
        Check if any alert conditions are met.
        
        Returns:
            List of alert messages
        """
        alerts = []
        
        try:
            # Extreme put/call ratios
            if data.put_call_ratio < 0.5:
                alerts.append(f"⚠️ EXTREME BULLISH SENTIMENT: P/C ratio {data.put_call_ratio:.2f} - potential top signal")
            elif data.put_call_ratio > 1.5:
                alerts.append(f"⚠️ EXTREME BEARISH SENTIMENT: P/C ratio {data.put_call_ratio:.2f} - potential bottom signal")
            
            # Large unusual activity
            large_activity = [a for a in data.unusual_activity if a.get("volume_usd", 0) > 10_000_000]
            if large_activity:
                for activity in large_activity[:2]:
                    alerts.append(f"🚨 LARGE OPTIONS TRADE: {activity['description']}")
            
            # Extreme IV
            if data.iv_current > 2.0:
                alerts.append(f"⚡ EXTREME IV: {data.iv_current*100:.0f}% - high volatility expected")
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
        
        return alerts


# Singleton instance
_monitor = None

def get_options_monitor() -> OptionsMonitor:
    """Get singleton options monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = OptionsMonitor()
    return _monitor
