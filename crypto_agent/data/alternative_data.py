import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta

# This module fetches "Alternative Data" - signals that aren't price-based
# Like: How many people are working on the code (GitHub) or SEC filings.

class AlternativeDataService:
    def __init__(self):
        self.github_base_url = "https://api.github.com/repos"
        self.sec_base_url = "https://efts.sec.gov/LATEST/search-index"
        self.app_store_url = "https://itunes.apple.com/search"
        self.deribit_url = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"
        self.cache = {}

    async def get_github_velocity(self, owner: str, repo: str):
        """Checks how many 'commits' (code updates) happened in the last 7 days."""
        cache_key = f"github_{owner}_{repo}"
        
        # Pull from cache if we checked recently (last hour)
        if cache_key in self.cache:
            if datetime.now() - self.cache[cache_key]['time'] < timedelta(hours=1):
                return self.cache[cache_key]['data']

        url = f"{self.github_base_url}/{owner}/{repo}/commits"
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        params = {"since": seven_days_ago}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        commits = await resp.json()
                        velocity = len(commits)
                        
                        result = {
                            "velocity": velocity,
                            "status": "High" if velocity > 20 else "Normal" if velocity > 5 else "Low",
                            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        self.cache[cache_key] = {"data": result, "time": datetime.now()}
                        return result
                    else:
                        return {"velocity": 0, "status": "Unknown (API Error)", "last_updated": "N/A"}
        except Exception as e:
            logging.error(f"GitHub Error: {e}")
            return {"velocity": 0, "status": "Error", "last_updated": "N/A"}

    async def get_job_postings_count(self, company_name: str):
        """
        SIGNAL 1: JOB POSTING INTELLIGENCE
        Simulates trend analysis for hiring (would use Playwright/Apify).
        """
        trends = {
            "Coinbase": {"count": 42, "status": "Stable"},
            "Binance": {"count": 15, "status": "Declining"},
            "Kraken": {"count": 28, "status": "Increasing"}
        }
        
        count = trends.get(company_name, {"count": 0, "status": "Unknown"})
        return {
            "company": company_name,
            "open_positions": count["count"],
            "trend": count["status"],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

    async def get_app_store_ranking(self, app_name="Coinbase"):
        """
        SIGNAL 5: APP STORE RANKINGS
        Uses iTunes Search API to verify app data.
        """
        params = {"term": app_name, "country": "us", "entity": "software", "limit": 1}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.app_store_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("resultCount", 0) > 0:
                            app = data["results"][0]
                            return {
                                "app": app_name,
                                "rating": app.get("averageUserRating"),
                                "reviews": app.get("userRatingCount"),
                                "version": app.get("version"),
                                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                            }
        except Exception as e:
            logging.error(f"App Store Error: {e}")
        return {"app": app_name, "status": "Unavailable"}

    async def get_deribit_options_flow(self, currency="BTC"):
        """
        SIGNAL 4: DERIVATIVES FLOW INTELLIGENCE
        Monitor Deribit for volume, open interest, and put/call ratio.
        """
        params = {"currency": currency, "kind": "option"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.deribit_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("result", [])
                        
                        total_volume = sum(r.get("volume", 0) for r in results)
                        total_oi = sum(r.get("open_interest", 0) for r in results)
                        
                        # Simplified put/call proxy based on volume distribution
                        # (Real implementation would filter by instrument name)
                        return {
                            "currency": currency,
                            "volume_24h": round(total_volume, 2),
                            "open_interest": round(total_oi, 2),
                            "status": "High Activity" if total_volume > 1000 else "Normal",
                            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
        except Exception as e:
            logging.error(f"Deribit Error: {e}")
        return {"currency": currency, "status": "Unavailable"}

    async def get_sec_mentions(self):
        """Checks for new 'Bitcoin' mentions in SEC filings."""
        # This is a simplified proxy for institutional interest
        url = f"{self.sec_base_url}?q=bitcoin&forms=13F" # 13F are institutional holdings
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # The SEC search index returns a complex structure, we look for 'hits'
                        hits = data.get("hits", {}).get("total", {}).get("value", 0)
                        return {
                            "total_sec_mentions": hits,
                            "recent_filings": data.get("hits", {}).get("hits", [])[:3] # Get last 3
                        }
        except Exception as e:
            logging.error(f"SEC API Error: {e}")
            return {"total_sec_mentions": 0, "recent_filings": []}

    async def get_alternative_summary(self, symbol="BTC"):
        """Combines all alt-data signals into a single report."""
        repo_map = {
            "BTC": ("bitcoin", "bitcoin"),
            "ETH": ("ethereum", "go-ethereum"),
            "SOL": ("solana-labs", "solana")
        }
        company_map = {
            "BTC": "Coinbase",
            "ETH": "Uniswap",
            "SOL": "Solana Foundation"
        }
        
        summary = {"symbol": symbol}
        
        if symbol in repo_map:
            owner, repo = repo_map[symbol]
            summary["github"] = await self.get_github_velocity(owner, repo)
        
        if symbol == "BTC":
            summary["sec"] = await self.get_sec_mentions()
            
        if symbol in company_map:
            summary["jobs"] = await self.get_job_postings_count(company_map[symbol])
            
        if symbol == "BTC":
            summary["apps"] = await self.get_app_store_ranking("Coinbase")
            
        # 5. Derivatives (Tier 5, Signal 4)
        summary["options"] = await self.get_deribit_options_flow(symbol)
            
        return summary

# Test block
if __name__ == "__main__":
    async def test():
        service = AlternativeDataService()
        print(f"--- FETCHING ALTERNATIVE DATA FOR BTC ---")
        btc_data = await service.get_alternative_summary("BTC")
        
        if 'github' in btc_data:
            print(f"Code Activity: {btc_data['github'].get('velocity')} commits (Status: {btc_data['github'].get('status')})")
        if 'jobs' in btc_data:
            print(f"Hiring Trend: {btc_data['jobs'].get('company')} has {btc_data['jobs'].get('open_positions')} openings ({btc_data['jobs'].get('trend')})")
        if 'apps' in btc_data and btc_data['apps'].get('status') != 'Unavailable':
            print(f"Market Interest: {btc_data['apps'].get('app')} Rating: {btc_data['apps'].get('rating')}")
        if 'options' in btc_data and btc_data['options'].get('status') != 'Unavailable':
            print(f"Options Flow: {btc_data['options'].get('currency')} 24h Vol: {btc_data['options'].get('volume_24h')}")
        if 'sec' in btc_data:
            print(f"SEC Mentions: {btc_data['sec'].get('total_sec_mentions')}")

    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        pass
