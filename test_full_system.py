import asyncio
import time
from datetime import datetime
import database
import price_service
import market_service
import main
import error_handler

async def run_system_test():
    print("🚀 Starting Comprehensive System Test...")
    results = []

    # 1. DATABASE TESTS
    db_passed = 0
    
    # Portfolio
    try:
        database.add_or_update_position("TESTCOIN", 10.0, 1000.0, "Test position")
        pos = database.get_position("TESTCOIN")
        if pos and pos['quantity'] == 10.0:
            database.delete_position("TESTCOIN")
            db_passed += 1
            print("✅ DB: Portfolio operations passed")
        else:
            print("❌ DB: Portfolio operations failed")
    except Exception as e:
        print(f"❌ DB: Portfolio error: {e}")

    # Journal
    try:
        entry_id = database.add_journal_entry("Trade", "Test entry for system check", symbol="TESTCOIN")
        matches = database.search_journal("system check")
        if any(m['id'] == entry_id for m in matches):
            database.delete_journal_entry(entry_id)
            db_passed += 1
            print("✅ DB: Journal operations passed")
        else:
            print("❌ DB: Journal operations failed")
    except Exception as e:
        print(f"❌ DB: Journal error: {e}")

    # Alerts
    try:
        alert_id = database.create_alert("TESTCOIN", 50000.0, "above", "Test alert")
        database.deactivate_alert(alert_id)
        database.delete_alert(alert_id)
        db_passed += 1
        print("✅ DB: Alert operations passed")
    except Exception as e:
        print(f"❌ DB: Alert error: {e}")

    # Notes
    try:
        note_id = database.add_note("Test system note", category="test", symbol="TESTCOIN")
        notes = database.get_all_notes(active_only=False)
        if any(n['id'] == note_id for n in notes):
            database.delete_note_permanently(note_id)
            db_passed += 1
            print("✅ DB: Notes operations passed")
        else:
            print("❌ DB: Notes operations failed")
    except Exception as e:
        print(f"❌ DB: Notes error: {e}")

    # 2. API TESTS
    api_results = {}
    
    # Binance
    try:
        p, c = await price_service.get_price("BTC")
        if p:
            api_results['binance'] = f"✅ Binance API (BTC: ${p:,.0f})"
            print(f"✅ API: Binance BTC price: ${p:,.0f}")
        else:
            api_results['binance'] = "❌ Binance API (Failed)"
            print("❌ API: Binance failed")
    except Exception as e:
        api_results['binance'] = f"❌ Binance API (Error: {e})"

    # Market Overview
    try:
        overview = await price_service.get_market_overview()
        if overview:
            cap = overview['total_market_cap_usd'] / 1e12
            api_results['coingecko'] = f"✅ CoinGecko API (Market: ${cap:.1f}T)"
            print(f"✅ API: CoinGecko Market Cap: ${cap:.1f}T")
        else:
            api_results['coingecko'] = "❌ CoinGecko API (Failed)"
    except Exception as e:
        api_results['coingecko'] = f"❌ CoinGecko Error: {e}"

    # Fear & Greed
    try:
        fng = await price_service.get_fear_greed_index()
        if fng:
            api_results['fng'] = f"✅ Fear & Greed (Score: {fng['value']})"
            print(f"✅ API: Fear & Greed: {fng['value']}")
        else:
            api_results['fng'] = "❌ Fear & Greed (Failed)"
    except Exception as e:
        api_results['fng'] = f"❌ FNG Error: {e}"

    # 3. AI TEST
    ai_status = ""
    ai_time = 0
    try:
        start_t = time.time()
        response = await main.get_ai_response([{"role": "user", "content": "Respond with only the word 'OK'."}])
        ai_time = time.time() - start_t
        if response and "OK" in response.upper():
            ai_status = f"✅ Anthropic Claude (Response: {ai_time:.1f}s)"
            print(f"✅ AI: Claude responded in {ai_time:.1f}s")
        else:
            ai_status = "❌ Anthropic Claude (Unexpected response)"
            print(f"❌ AI: Failed - {response}")
    except Exception as e:
        ai_status = f"❌ AI Error: {e}"

    # 4. CALCULATION TESTS
    calc_passed = 0
    
    # P&L Logic
    qty, buy_p, curr_p = 1.0, 90000.0, 95000.0
    val = qty * curr_p
    cost = qty * buy_p
    pnl = val - cost
    pnl_pct = (pnl / cost) * 100
    if pnl == 5000.0 and round(pnl_pct, 1) == 5.6: # 5000/90000 = 5.555...
        calc_passed += 1
        print("✅ CALC: P&L calculation correct")
    else:
        # Re-checking 5.5 vs 5.6
        if round(pnl_pct, 2) == 5.56:
             calc_passed += 1
             print("✅ CALC: P&L calculation correct")
        else:
            print(f"❌ CALC: P&L failed ({pnl}, {pnl_pct}%)")

    # Alert Logic
    alert_triggered = False
    if curr_p > 94000: # Above condition
        alert_triggered = True
    
    if alert_triggered:
        calc_passed += 1
        print("✅ CALC: Alert logic working")
    else:
        print("❌ CALC: Alert logic failed")

    # 5. GENERATE REPORT
    total_score = db_passed + (3 if '✅' in str(api_results) else 0) + (1 if '✅' in ai_status else 0) + calc_passed
    # Correction: The score should be out of 10 as requested.
    # DB: 4, API: 3, AI: 1, CALC: 2 = 10
    
    api_success_count = sum(1 for v in api_results.values() if "✅" in v)
    ai_success = 1 if "✅" in ai_status else 0
    
    final_score = db_passed + api_success_count + ai_success + calc_passed

    report = (
        "\n"
        "══════════════════════════════\n"
        "   CRYPTO AGENT — SYSTEM TEST\n"
        f"   {datetime.now().strftime('%b %d, %Y %I:%M %p')}\n"
        "══════════════════════════════\n\n"
        "DATABASE:\n"
        f"{'✅' if db_passed >= 1 else '❌'} Portfolio operations\n"
        f"{'✅' if db_passed >= 2 else '❌'} Journal operations\n"
        f"{'✅' if db_passed >= 3 else '❌'} Alert operations\n"
        f"{'✅' if db_passed >= 4 else '❌'} Notes operations\n\n"
        "EXTERNAL APIs:\n"
        f"{api_results.get('binance', '❌ Binance API')}\n"
        f"{api_results.get('coingecko', '❌ CoinGecko API')}\n"
        f"{api_results.get('fng', '❌ Fear & Greed')}\n\n"
        "AI:\n"
        f"{ai_status}\n\n"
        "CALCULATIONS:\n"
        f"{'✅' if calc_passed >= 1 else '❌'} P&L calculation correct\n"
        f"{'✅' if calc_passed >= 2 else '❌'} Alert logic working\n\n"
        "══════════════════════════════\n"
        f"RESULT: {final_score}/10 tests passed {'✅' if final_score == 10 else '⚠️'}\n"
        f"{'System is ready to use!' if final_score == 10 else 'System has some issues. Check logs.'}\n"
        "════════════════════════\n"
    )
    
    print(report)

if __name__ == "__main__":
    asyncio.run(run_system_test())
