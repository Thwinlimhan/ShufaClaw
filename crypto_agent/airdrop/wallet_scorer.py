import logging
from datetime import datetime

# PART 7, PROMPT 2: Wallet Reputation Scorer
# Scores your wallet's "health" across 5 dimensions.
# Protocols use these metrics to filter out bots and reward real users.

class WalletScorer:
    def __init__(self):
        pass

    def score_wallet(self, wallet_data):
        """
        WALLET HEALTH SCORE (0-100)
        5 Dimensions weighted to match how protocols actually filter.
        """
        scores = {}

        # DIMENSION 1: AGE & ACTIVITY (25%)
        age_months = wallet_data.get("age_months", 0)
        active_months = wallet_data.get("active_months_last_12", 0)
        if age_months >= 24:
            age_score = 100
        elif age_months >= 12:
            age_score = 80
        elif age_months >= 6:
            age_score = 50
        else:
            age_score = 20
        activity_bonus = min((active_months / 12) * 100, 100)
        scores["age_activity"] = round((age_score * 0.5 + activity_bonus * 0.5), 1)

        # DIMENSION 2: PROTOCOL DIVERSITY (25%)
        unique_protocols = wallet_data.get("unique_protocols", 0)
        unique_categories = wallet_data.get("unique_categories", 0)
        diversity = min((unique_protocols * unique_categories) / 50 * 100, 100)
        scores["diversity"] = round(diversity, 1)

        # DIMENSION 3: VOLUME & VALUE (20%)
        lifetime_volume = wallet_data.get("lifetime_volume_usd", 0)
        avg_tx_size = wallet_data.get("avg_tx_size_usd", 0)
        vol_score = min((lifetime_volume / 50000) * 100, 100)
        # Penalize tiny identical txns (sybil signal)
        if avg_tx_size < 10:
            vol_score *= 0.3
        scores["volume"] = round(vol_score, 1)

        # DIMENSION 4: FINANCIAL SOPHISTICATION (15%)
        gov_votes = wallet_data.get("governance_votes", 0)
        lp_provided = wallet_data.get("lp_positions", 0)
        staking = wallet_data.get("staking_positions", 0)
        contracts_deployed = wallet_data.get("contracts_deployed", 0)
        sophistication = min(
            (gov_votes * 15 + lp_provided * 20 + staking * 10 + contracts_deployed * 30), 100
        )
        scores["sophistication"] = round(sophistication, 1)

        # DIMENSION 5: SOCIAL PROOF (15%)
        has_ens = wallet_data.get("has_ens", False)
        gitcoin_score = wallet_data.get("gitcoin_passport_score", 0)
        poap_count = wallet_data.get("poap_count", 0)
        social = 0
        if has_ens:
            social += 30
        social += min(gitcoin_score * 2, 40)
        social += min(poap_count * 2, 30)
        scores["social_proof"] = round(min(social, 100), 1)

        # COMPOSITE
        composite = round(
            scores["age_activity"] * 0.25 +
            scores["diversity"] * 0.25 +
            scores["volume"] * 0.20 +
            scores["sophistication"] * 0.15 +
            scores["social_proof"] * 0.15,
            1
        )

        # SYBIL FLAGS
        sybil_flags = []
        if wallet_data.get("identical_amounts_pct", 0) > 50:
            sybil_flags.append("Many identical transaction amounts")
        if wallet_data.get("failed_txns", 0) == 0 and wallet_data.get("total_txns", 0) > 50:
            sybil_flags.append("Zero failed transactions (suspicious)")
        if avg_tx_size < 5 and wallet_data.get("total_txns", 0) > 100:
            sybil_flags.append("Tiny repeated transactions (bot-like)")

        # GAPS TO ADDRESS
        gaps = []
        if not has_ens:
            gaps.append("No ENS name (easy win, ~$5/year)")
        if gov_votes == 0:
            gaps.append("No governance votes (participate in any DAO)")
        if active_months < 6:
            gaps.append(f"Only {active_months}/12 active months (need consistency)")
        if unique_categories < 4:
            gaps.append(f"Only {unique_categories} DeFi categories used (add lending, bridges, etc.)")

        return {
            "composite_score": composite,
            "grade": "Strong" if composite >= 70 else "Good" if composite >= 50 else "Needs Work",
            "breakdown": scores,
            "sybil_flags": sybil_flags,
            "gaps_to_address": gaps
        }


# Test block
if __name__ == "__main__":
    scorer = WalletScorer()

    # Example wallet data
    my_wallet = {
        "age_months": 28,
        "active_months_last_12": 8,
        "unique_protocols": 47,
        "unique_categories": 5,
        "lifetime_volume_usd": 340000,
        "avg_tx_size_usd": 280,
        "governance_votes": 3,
        "lp_positions": 2,
        "staking_positions": 1,
        "contracts_deployed": 0,
        "has_ens": False,
        "gitcoin_passport_score": 15,
        "poap_count": 8,
        "total_txns": 200,
        "failed_txns": 12,
        "identical_amounts_pct": 10
    }

    result = scorer.score_wallet(my_wallet)
    print("--- WALLET REPUTATION ANALYSIS ---")
    print(f"  OVERALL: {result['composite_score']}/100  {result['grade']}")
    print(f"\n  BREAKDOWN:")
    for dim, score in result["breakdown"].items():
        print(f"    {dim}: {score}/100")
    if result["sybil_flags"]:
        print(f"\n  SYBIL FLAGS:")
        for flag in result["sybil_flags"]:
            print(f"    [!] {flag}")
    print(f"\n  GAPS TO ADDRESS:")
    for gap in result["gaps_to_address"]:
        print(f"    - {gap}")
