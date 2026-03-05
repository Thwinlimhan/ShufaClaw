import aiohttp
import asyncio
import logging
from datetime import datetime

# TIER 6: Cross-Market Arbitrage Intelligence
# This module identifies mispricings and premiums across different venues.

class ArbitrageScanner:
    def __init__(self):
        self.binance_spot = "https://api.binance.com/api/v3/ticker/price"
        self.binance_perp = "https://fapi.binance.com/fapi/v1/ticker/price"
        self.coinbase_url = "https://api.coinbase.com/v2/prices"
        self.gateio_url = "https://api.gateio.ws/api/v4/spot/tickers"
        
    async def get_futures_basis(self, symbol="BTC"):
        """SCANNER 1: FUTURES BASIS TRACKER (Spot vs Perp)"""
        try:
            async with aiohttp.ClientSession() as session:
                # Fetch Spot and Perp simultaneously
                async with session.get(f"{self.binance_spot}?symbol={symbol}USDT") as r1, \
                           session.get(f"{self.binance_perp}?symbol={symbol}USDT") as r2:
                    
                    spot_price = float((await r1.json())['price'])
                    perp_price = float((await r2.json())['price'])
                    
                    basis = perp_price - spot_price
                    basis_pct = (basis / spot_price) * 100
                    
                    return {
                        "symbol": symbol,
                        "spot": spot_price,
                        "perp": perp_price,
                        "basis_usd": round(basis, 2),
                        "basis_pct": round(basis_pct, 4),
                        "sentiment": "Contango (Bullish)" if basis > 0 else "Backwardation (Bearish)"
                    }
        except Exception as e:
            logging.error(f"Basis Error: {e}")
            return {"status": "Error", "message": "Could not calculate basis"}

    async def get_exchange_premium(self, symbol="BTC"):
        """SCANNER 2: CROSS-EXCHANGE PREMIUM (Coinbase vs Binance)"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.binance_spot}?symbol={symbol}USDT") as r1, \
                           session.get(f"{self.coinbase_url}/{symbol}-USD/spot") as r2:
                    
                    binance_price = float((await r1.json())['price'])
                    coinbase_price = float((await r2.json())['data']['amount'])
                    
                    premium = coinbase_price - binance_price
                    premium_pct = (premium / binance_price) * 100
                    
                    return {
                        "symbol": symbol,
                        "binance": binance_price,
                        "coinbase": coinbase_price,
                        "premium_usd": round(premium, 2),
                        "premium_pct": round(premium_pct, 4),
                        "interpretation": "US Institutional Buying" if premium_pct > 0.05 else "Neutral"
                    }
        except Exception as e:
            logging.error(f"Premium Error: {e}")
            return {"status": "Error", "message": "Could not calculate premium"}

    async def monitor_stablecoin_pegs(self):
        """SCANNER 4: STABLECOIN PEG MONITOR (USDT/USDC)"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.binance_spot}?symbol=USDTUSDC") as r:
                    if r.status == 200:
                        price = float((await r.json())['price'])
                        depeg_detected = abs(1.0 - price) > 0.003
                        return {
                            "pair": "USDT/USDC",
                            "price": price,
                            "status": "DANGER: DEPEG" if depeg_detected else "Stable",
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            logging.error(f"Peg Monitor Error: {e}")
        return {"pair": "USDT/USDC", "status": "Error", "price": 1.0}

    async def get_full_arbitrage_report(self, symbol="BTC"):
        """Runs all arbitrage scans for a unified briefing."""
        basis = await self.get_futures_basis(symbol)
        premium = await self.get_exchange_premium(symbol)
        peg = await self.monitor_stablecoin_pegs()
        
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "basis": basis,
            "premium": premium,
            "stable_peg": peg
        }

# Test execution
if __name__ == "__main__":
    async def run_test():
        scanner = ArbitrageScanner()
        print(f"--- RUNNING ARBITRAGE SCAN FOR BTC ---")
        report = await scanner.get_full_arbitrage_report("BTC")
        
        if report['basis'].get('symbol'):
            print(f"Basis: {report['basis']['basis_pct']}% ({report['basis']['sentiment']})")
        else:
            print("Basis: Unavailable")
            
        if report['premium'].get('symbol'):
            print(f"Coinbase Premium: {report['premium']['premium_pct']}%")
        else:
            print("Coinbase Premium: Unavailable")
            
        print(f"Stable Peg: {report['stable_peg']['status']} ({report['stable_peg'].get('price', 'N/A')})")

    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        pass
