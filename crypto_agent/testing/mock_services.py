"""
Mock Services for Testing (Level 38)

Provides realistic mock implementations of all external services
for testing without real API calls.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio


class MockPriceService:
    """Mock price service with realistic price movements"""
    
    def __init__(self, base_prices: Optional[Dict[str, float]] = None):
        self.base_prices = base_prices or {
            'BTC': 97500,
            'ETH': 3400,
            'SOL': 125,
            'BNB': 580,
            'ADA': 0.65,
            'AVAX': 38,
            'MATIC': 0.95,
            'DOT': 8.5,
            'LINK': 18,
            'UNI': 12
        }
        self.volatility = 0.02  # 2% volatility
        self.trend = 0.0  # No trend by default
        
    async def get_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current price with realistic fluctuation"""
        if symbol not in self.base_prices:
            return None
        
        base_price = self.base_prices[symbol]
        
        # Add random walk
        change = random.gauss(self.trend, self.volatility)
        current_price = base_price * (1 + change)
        
        # Update base price for next call
        self.base_prices[symbol] = current_price
        
        # Generate 24h change
        change_24h = random.gauss(0, 3)  # ±3% average
        
        # Generate volume
        volume_24h = base_price * random.uniform(20e9, 50e9)
        
        return {
            'price': current_price,
            'change_24h': change_24h,
            'volume_24h': volume_24h,
            'market_cap': current_price * random.uniform(100e9, 500e9),
            'high_24h': current_price * 1.05,
            'low_24h': current_price * 0.95
        }
    
    def set_trend(self, trend: float):
        """Set price trend (positive = bullish, negative = bearish)"""
        self.trend = trend
    
    def set_volatility(self, volatility: float):
        """Set price volatility"""
        self.volatility = volatility
    
    def reset_prices(self):
        """Reset to base prices"""
        self.base_prices = {
            'BTC': 97500,
            'ETH': 3400,
            'SOL': 125,
            'BNB': 580,
            'ADA': 0.65,
            'AVAX': 38,
            'MATIC': 0.95,
            'DOT': 8.5,
            'LINK': 18,
            'UNI': 12
        }


class MockMarketService:
    """Mock market service with realistic market data"""
    
    def __init__(self):
        self.fear_greed = 50  # Neutral
        self.btc_dominance = 52.5
        
    async def get_fear_greed_index(self) -> Dict[str, Any]:
        """Get Fear & Greed index"""
        # Add some randomness
        self.fear_greed += random.gauss(0, 5)
        self.fear_greed = max(0, min(100, self.fear_greed))
        
        if self.fear_greed < 25:
            classification = "Extreme Fear"
        elif self.fear_greed < 45:
            classification = "Fear"
        elif self.fear_greed < 55:
            classification = "Neutral"
        elif self.fear_greed < 75:
            classification = "Greed"
        else:
            classification = "Extreme Greed"
        
        return {
            'value': int(self.fear_greed),
            'classification': classification,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview"""
        return {
            'total_market_cap': 2.5e12,
            'total_volume_24h': 120e9,
            'btc_dominance': self.btc_dominance,
            'eth_dominance': 18.5,
            'active_cryptocurrencies': 12500,
            'markets': 850
        }
    
    async def get_top_coins(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top coins by market cap"""
        coins = [
            {'rank': 1, 'symbol': 'BTC', 'name': 'Bitcoin', 'price': 97500, 'market_cap': 1.9e12, 'change_24h': 2.5},
            {'rank': 2, 'symbol': 'ETH', 'name': 'Ethereum', 'price': 3400, 'market_cap': 410e9, 'change_24h': 3.2},
            {'rank': 3, 'symbol': 'BNB', 'name': 'BNB', 'price': 580, 'market_cap': 89e9, 'change_24h': 1.8},
            {'rank': 4, 'symbol': 'SOL', 'name': 'Solana', 'price': 125, 'market_cap': 55e9, 'change_24h': 5.1},
            {'rank': 5, 'symbol': 'ADA', 'name': 'Cardano', 'price': 0.65, 'market_cap': 23e9, 'change_24h': -1.2},
            {'rank': 6, 'symbol': 'AVAX', 'name': 'Avalanche', 'price': 38, 'market_cap': 15e9, 'change_24h': 2.8},
            {'rank': 7, 'symbol': 'DOT', 'name': 'Polkadot', 'price': 8.5, 'market_cap': 12e9, 'change_24h': 0.5},
            {'rank': 8, 'symbol': 'MATIC', 'name': 'Polygon', 'price': 0.95, 'market_cap': 9e9, 'change_24h': 1.9},
            {'rank': 9, 'symbol': 'LINK', 'name': 'Chainlink', 'price': 18, 'market_cap': 11e9, 'change_24h': 3.5},
            {'rank': 10, 'symbol': 'UNI', 'name': 'Uniswap', 'price': 12, 'market_cap': 9e9, 'change_24h': -0.8}
        ]
        
        return coins[:limit]
    
    def set_fear_greed(self, value: int):
        """Set Fear & Greed index"""
        self.fear_greed = max(0, min(100, value))


class MockTAService:
    """Mock technical analysis service"""
    
    def __init__(self):
        self.scenarios = {}
    
    async def analyze(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Generate technical analysis"""
        # Check if we have a predefined scenario
        if symbol in self.scenarios:
            return self.scenarios[symbol]
        
        # Generate random but realistic TA
        price = 97500 if symbol == 'BTC' else 3400 if symbol == 'ETH' else 100
        
        rsi = random.uniform(30, 70)
        
        # Determine trend based on RSI
        if rsi > 60:
            trend = 'up'
        elif rsi < 40:
            trend = 'down'
        else:
            trend = 'neutral'
        
        support = price * random.uniform(0.92, 0.97)
        resistance = price * random.uniform(1.03, 1.08)
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'price': price,
            'rsi': rsi,
            'trend': trend,
            'support': support,
            'resistance': resistance,
            'sma_20': price * random.uniform(0.97, 1.03),
            'sma_50': price * random.uniform(0.95, 1.05),
            'sma_200': price * random.uniform(0.90, 1.10),
            'volume_ratio': random.uniform(0.8, 2.0),
            'macd': random.uniform(-100, 100),
            'macd_signal': random.uniform(-100, 100)
        }
    
    def set_scenario(self, symbol: str, scenario: Dict[str, Any]):
        """Set predefined scenario for symbol"""
        self.scenarios[symbol] = scenario
    
    def clear_scenarios(self):
        """Clear all scenarios"""
        self.scenarios = {}


class MockDatabase:
    """Mock database for testing"""
    
    def __init__(self):
        self.positions = []
        self.alerts = []
        self.journal = []
        self.proposals = []
        self.notes = []
        self.next_id = 1
    
    async def get_positions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user positions"""
        return [p for p in self.positions if p['user_id'] == user_id]
    
    async def add_position(
        self,
        user_id: int,
        symbol: str,
        amount: float,
        entry_price: float
    ):
        """Add position"""
        self.positions.append({
            'id': self.next_id,
            'user_id': user_id,
            'symbol': symbol,
            'amount': amount,
            'entry_price': entry_price,
            'created_at': datetime.now().isoformat()
        })
        self.next_id += 1
    
    async def update_position(self, position_id: int, amount: float):
        """Update position amount"""
        for p in self.positions:
            if p['id'] == position_id:
                p['amount'] = amount
                break
    
    async def delete_position(self, position_id: int):
        """Delete position"""
        self.positions = [p for p in self.positions if p['id'] != position_id]
    
    async def create_alert(
        self,
        user_id: int,
        symbol: str,
        target_price: float,
        direction: str,
        message: Optional[str] = None
    ) -> int:
        """Create alert"""
        alert_id = self.next_id
        self.alerts.append({
            'id': alert_id,
            'user_id': user_id,
            'symbol': symbol,
            'target_price': target_price,
            'direction': direction,
            'message': message,
            'active': True,
            'created_at': datetime.now().isoformat()
        })
        self.next_id += 1
        return alert_id
    
    async def get_active_alerts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get active alerts"""
        return [a for a in self.alerts if a['user_id'] == user_id and a['active']]
    
    async def deactivate_alert(self, alert_id: int):
        """Deactivate alert"""
        for a in self.alerts:
            if a['id'] == alert_id:
                a['active'] = False
                break
    
    async def delete_alert(self, alert_id: int):
        """Delete alert"""
        self.alerts = [a for a in self.alerts if a['id'] != alert_id]
    
    async def add_journal_entry(
        self,
        user_id: int,
        entry: str,
        symbol: Optional[str] = None
    ):
        """Add journal entry"""
        self.journal.append({
            'id': self.next_id,
            'user_id': user_id,
            'entry': entry,
            'symbol': symbol,
            'created_at': datetime.now().isoformat()
        })
        self.next_id += 1
    
    async def get_journal_entries(
        self,
        user_id: int,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get journal entries"""
        cutoff = datetime.now() - timedelta(days=days)
        return [
            j for j in self.journal
            if j['user_id'] == user_id
            and datetime.fromisoformat(j['created_at']) > cutoff
        ]
    
    async def add_note(
        self,
        user_id: int,
        note: str,
        category: str = 'general'
    ):
        """Add note"""
        self.notes.append({
            'id': self.next_id,
            'user_id': user_id,
            'note': note,
            'category': category,
            'active': True,
            'created_at': datetime.now().isoformat()
        })
        self.next_id += 1
    
    async def get_all_notes(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all notes"""
        return [n for n in self.notes if n['user_id'] == user_id and n['active']]
    
    async def execute(self, query: str, params: tuple = ()):
        """Execute SQL query (mock)"""
        pass
    
    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows (mock)"""
        return []
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch one row (mock)"""
        return None
    
    def clear_all(self):
        """Clear all data"""
        self.positions = []
        self.alerts = []
        self.journal = []
        self.proposals = []
        self.notes = []
        self.next_id = 1


class MockNewsService:
    """Mock news service"""
    
    def __init__(self):
        self.sentiment = 'neutral'
    
    async def get_news(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get news articles"""
        articles = [
            {
                'title': 'Bitcoin reaches new milestone',
                'source': 'CryptoNews',
                'url': 'https://example.com/article1',
                'published_at': datetime.now().isoformat(),
                'sentiment': 'positive'
            },
            {
                'title': 'Ethereum upgrade scheduled',
                'source': 'CoinDesk',
                'url': 'https://example.com/article2',
                'published_at': datetime.now().isoformat(),
                'sentiment': 'positive'
            },
            {
                'title': 'Market volatility increases',
                'source': 'Bloomberg',
                'url': 'https://example.com/article3',
                'published_at': datetime.now().isoformat(),
                'sentiment': 'negative'
            }
        ]
        
        if symbol:
            # Filter by symbol
            return [a for a in articles if symbol.lower() in a['title'].lower()]
        
        return articles
    
    async def get_sentiment(self) -> Dict[str, Any]:
        """Get overall sentiment"""
        return {
            'sentiment': self.sentiment,
            'score': 0.6 if self.sentiment == 'positive' else 0.4 if self.sentiment == 'negative' else 0.5,
            'sources': 10
        }
    
    def set_sentiment(self, sentiment: str):
        """Set sentiment (positive/negative/neutral)"""
        self.sentiment = sentiment


class MockOnChainService:
    """Mock on-chain data service"""
    
    async def get_network_stats(self, symbol: str) -> Dict[str, Any]:
        """Get network statistics"""
        if symbol == 'BTC':
            return {
                'hash_rate': 450e18,
                'difficulty': 70e12,
                'mempool_size': 150000,
                'avg_fee': 2.5,
                'active_addresses': 950000
            }
        elif symbol == 'ETH':
            return {
                'gas_price': 25,
                'tps': 15,
                'active_addresses': 550000,
                'total_value_locked': 45e9,
                'staking_ratio': 0.22
            }
        
        return {}
    
    async def get_whale_activity(self, symbol: str) -> List[Dict[str, Any]]:
        """Get whale transactions"""
        return [
            {
                'hash': '0x' + '1' * 64,
                'from': '0x' + 'a' * 40,
                'to': '0x' + 'b' * 40,
                'value': 1000,
                'timestamp': datetime.now().isoformat()
            }
        ]
