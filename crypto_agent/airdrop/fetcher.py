import aiohttp
import asyncio
import logging
import time
from datetime import datetime
from crypto_agent import config
from crypto_agent.storage import database

logger = logging.getLogger(__name__)

ETHERSCAN_BASE = "https://api.etherscan.io/api"

# Small common protocol mapping (Address -> Name)
# In production, this would be a large JSON or SQL table
PROTOCOL_MAP = {
    "0x881d9c2f22932485121473062318fe39b054fc21": "MetaMask Swap",
    "0x00000000006c3852cbef3e08e8df289169ede581": "OpenSea (Opensea Seaport)",
    "0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b": "Uniswap V3 Router",
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2 Router",
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": "Uniswap Universal Router",
    "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3 Swap Router",
    "0x1111111254eeb25477b68fb85ed929f73a960582": "1inch v5 Router",
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff": "0x Exchange Proxy",
    "0x397ff44b08f3631d23f3922485579973952f168d": "Maestro Bot Router",
    "0x0000000000a39bb2eeb17b1059f5f2c52aa7390f": "Blur Marketplace",
    "0x70d8976b927891cf2c3af8013d3080ff4ca7470c": "Aave V3 Pool",
    "0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9": "Aave V2 Pool",
}

async def fetch_wallet_onchain_metrics(address):
    """
    Fetches raw on-chain data for a wallet and converts it into reputation metrics.
    Only supports Ethereum via Etherscan for now.
    """
    if not address or not config.ETHERSCAN_API_KEY:
        return None

    metrics = {
        "wallet_address": address.lower(),
        "age_months": 0,
        "active_months_last_12": 0,
        "unique_protocols": 0,
        "unique_categories": 0,
        "lifetime_volume_usd": 0,
        "avg_tx_size_usd": 0,
        "governance_votes": 0,
        "lp_positions": 0,
        "staking_positions": 0,
        "contracts_deployed": 0,
        "has_ens": 0,
        "gitcoin_passport_score": 0,
        "poap_count": 0,
        "total_txns": 0,
        "failed_txns": 0,
        "identical_amounts_pct": 0
    }

    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 999999999,
        "page": 1,
        "offset": 500, # Scan up to 500 txns
        "sort": "asc",
        "apikey": config.ETHERSCAN_API_KEY
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(ETHERSCAN_BASE, params=params) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                if data["status"] != "1":
                    return None
                
                txns = data["result"]
                metrics["total_txns"] = len(txns)
                
                if not txns:
                    return metrics

                # Initial Calculations
                first_tx_time = int(txns[0]["timeStamp"])
                metrics["age_months"] = int((time.time() - first_tx_time) / (30 * 24 * 3600))
                
                # Active months & Unique Protocols
                active_months_set = set()
                protocols_set = set()
                failed_count = 0
                total_value_wei = 0
                amounts = []
                
                now_ts = time.time()
                one_year_ago = now_ts - (365 * 24 * 3600)

                for tx in txns:
                    ts = int(tx["timeStamp"])
                    dt = datetime.fromtimestamp(ts)
                    
                    # Track months
                    if ts > one_year_ago:
                        active_months_set.add(f"{dt.year}-{dt.month}")
                    
                    # Track failed
                    if tx.get("isError") == "1":
                        failed_count += 1
                        continue
                    
                    # Track Protocols
                    to_addr = tx.get("to", "").lower()
                    if to_addr in PROTOCOL_MAP:
                        protocols_set.add(PROTOCOL_MAP[to_addr])
                    
                    # Track Volume (Only native ETH here, simplified)
                    val = int(tx.get("value", 0))
                    total_value_wei += val
                    amounts.append(val)
                    
                    # Contract creation
                    if not to_addr or to_addr == "0x":
                        metrics["contracts_deployed"] += 1

                metrics["active_months_last_12"] = len(active_months_set)
                metrics["unique_protocols"] = len(protocols_set)
                metrics["failed_txns"] = failed_count
                
                # Volume (Rough approximation, using $2500 ETH price)
                # In real scenario, we'd fetch price at each timestamp
                eth_price = 2500 
                metrics["lifetime_volume_usd"] = (total_value_wei / 1e18) * eth_price
                if metrics["total_txns"] > 0:
                    metrics["avg_tx_size_usd"] = metrics["lifetime_volume_usd"] / metrics["total_txns"]
                
                # Identical amounts (Sybil signal)
                if len(amounts) > 10:
                    from collections import Counter
                    counts = Counter(amounts)
                    # Most frequent non-zero amount
                    most_common = counts.most_common(1)
                    if most_common and most_common[0][0] > 0:
                        metrics["identical_amounts_pct"] = (most_common[0][1] / len(amounts)) * 100
                
                # Categories (Simplified)
                categories = set()
                if metrics["unique_protocols"] > 0: categories.add("DEX")
                if "Uniswap" in str(protocols_set): categories.add("Swap")
                if "Aave" in str(protocols_set): categories.add("Lending")
                metrics["unique_categories"] = len(categories)

                # Check ENS
                ens_params = {
                    "module": "account",
                    "action": "getensname",
                    "address": address,
                    "apikey": config.ETHERSCAN_API_KEY
                }
                async with session.get(ETHERSCAN_BASE, params=ens_params) as ens_res:
                    ens_data = await ens_res.json()
                    if ens_data.get("status") == "1" and ens_data.get("result"):
                        metrics["has_ens"] = 1

        except Exception as e:
            logger.error(f"Error fetching on-chain metrics: {e}")
            return None

    # Save to DB
    database.save_wallet_metrics(metrics)
    return metrics

async def main():
    # Test
    test_addr = "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8" # Example whale address
    print(f"Fetching metrics for {test_addr}...")
    res = await fetch_wallet_onchain_metrics(test_addr)
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
