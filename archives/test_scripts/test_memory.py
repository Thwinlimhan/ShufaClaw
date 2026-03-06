# Test file to see the memory system in action
# Run this with: python test_memory.py

from intelligence.memory import MemorySystem

print("Testing Memory System...\n")

# Create the memory system
memory = MemorySystem()

print("1) Adding a sample trading profile...")
memory.update_trading_profile({
    'preferred_coins': ['BTC', 'ETH', 'SOL'],
    'risk_tolerance': 'medium',
    'typical_position_size': '$5,000',
    'trading_style': 'swingtrader',
    'known_strengths': [
        'Good at identifying ETH oversold bounces',
        'RSI signals on BTC 4h chart have been accurate'
    ],
    'known_weaknesses': [
        'Tends to exit winning trades too early',
        'Altcoin analysis has been less reliable'
    ],
    'recent_lessons': [
        'Wait for volume confirmation before entering breakouts',
        'Don\'t FOMO into pumps without checking resistance levels'
    ]
})

print("\n2) Adding some market insights...")
memory.record_market_insight(
    'BTC', 
    'pattern', 
    'Tends to dip 2-3 days before options expiry',
    confidence=4
)
memory.record_market_insight(
    'ETH',
    'correlation',
    'Follows BTC with 2-4 hour lag on dips',
    confidence=4
)
memory.record_market_insight(
    'BTC',
    'pattern',
    'Strong support at round numbers like $60k, $70k',
    confidence=5
)

print("\n3) Adding a journal entry...")
memory.add_journal_entry(
    'BTC',
    'trade',
    'Bought BTC at $67,500 after RSI showed oversold on 4h chart',
    outcome='win',
    profit_loss=850
)

print("\n" + "="*50)
print("YOUR TRADING PROFILE:")
print("="*50)
print(memory.format_profile_display())

print("\n" + "="*50)
print("MARKET INSIGHTS:")
print("="*50)
print(memory.format_insights_display())

print("\n" + "="*50)
print("PERSONALIZED CONTEXT FOR BTC:")
print("="*50)
print(memory.build_personalized_context('BTC'))

print("\nMemory system test complete!")
print("Database saved to: bot_memory.db")
