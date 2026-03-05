"""
Crypto Academy Core (Level 39)

Main learning system with 3 paths: Beginner, Intermediate, Advanced
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class Difficulty(Enum):
    """Lesson difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class Lesson:
    """Individual lesson"""
    lesson_id: str
    title: str
    difficulty: Difficulty
    content: str
    key_points: List[str]
    examples: List[str]
    quiz_questions: List[str]  # Question IDs
    estimated_time: int  # minutes
    prerequisites: List[str]  # Lesson IDs
    next_lessons: List[str]  # Lesson IDs


@dataclass
class LearningPath:
    """Learning path with multiple lessons"""
    path_id: str
    name: str
    description: str
    difficulty: Difficulty
    lessons: List[Lesson]
    total_lessons: int
    estimated_hours: int


class CryptoAcademy:
    """
    Personal Crypto Academy with adaptive learning.
    
    3 Learning Paths:
    - Beginner: Crypto basics, wallets, exchanges
    - Intermediate: Technical analysis, risk management
    - Advanced: Advanced strategies, derivatives, DeFi
    """
    
    def __init__(self, db):
        self.db = db
        self.paths = self._initialize_paths()
    
    def _initialize_paths(self) -> Dict[str, LearningPath]:
        """Initialize all learning paths"""
        return {
            'beginner': self._create_beginner_path(),
            'intermediate': self._create_intermediate_path(),
            'advanced': self._create_advanced_path()
        }
    
    def _create_beginner_path(self) -> LearningPath:
        """Create beginner learning path"""
        lessons = [
            Lesson(
                lesson_id="b01",
                title="What is Cryptocurrency?",
                difficulty=Difficulty.BEGINNER,
                content="""
# What is Cryptocurrency?

Cryptocurrency is digital money that uses cryptography for security.

## Key Concepts:

1. **Decentralized**: No central authority controls it
2. **Blockchain**: Public ledger recording all transactions
3. **Digital**: Exists only electronically
4. **Secure**: Protected by cryptography

## How It Works:

When you send crypto:
1. Transaction is broadcast to network
2. Miners/validators verify it
3. Transaction added to blockchain
4. Recipient receives crypto

## Popular Cryptocurrencies:

- **Bitcoin (BTC)**: First and largest cryptocurrency
- **Ethereum (ETH)**: Platform for smart contracts
- **Others**: Thousands of altcoins exist
                """,
                key_points=[
                    "Cryptocurrency is digital money",
                    "Uses blockchain technology",
                    "Decentralized and secure",
                    "Bitcoin was the first cryptocurrency"
                ],
                examples=[
                    "Bitcoin: Digital gold, store of value",
                    "Ethereum: Platform for decentralized apps",
                    "Stablecoins: Pegged to USD (like USDT)"
                ],
                quiz_questions=["q_b01_1", "q_b01_2", "q_b01_3"],
                estimated_time=15,
                prerequisites=[],
                next_lessons=["b02"]
            ),
            Lesson(
                lesson_id="b02",
                title="Wallets and Security",
                difficulty=Difficulty.BEGINNER,
                content="""
# Wallets and Security

A crypto wallet stores your private keys (passwords) to access your crypto.

## Types of Wallets:

1. **Hot Wallets** (Online)
   - Exchange wallets (Coinbase, Binance)
   - Mobile apps (Trust Wallet, MetaMask)
   - Convenient but less secure

2. **Cold Wallets** (Offline)
   - Hardware wallets (Ledger, Trezor)
   - Paper wallets
   - Most secure option

## Security Best Practices:

1. **Never share your private key**
2. **Use 2FA (Two-Factor Authentication)**
3. **Write down seed phrase offline**
4. **Beware of phishing scams**
5. **Use hardware wallet for large amounts**

## Common Mistakes:

- Storing keys on computer/phone
- Clicking suspicious links
- Sharing seed phrase
- Not backing up wallet
                """,
                key_points=[
                    "Wallets store your private keys",
                    "Hot wallets are convenient, cold wallets are secure",
                    "Never share your private key or seed phrase",
                    "Use 2FA and hardware wallets"
                ],
                examples=[
                    "Hot wallet: MetaMask for daily use",
                    "Cold wallet: Ledger for long-term storage",
                    "Seed phrase: 12-24 words to recover wallet"
                ],
                quiz_questions=["q_b02_1", "q_b02_2", "q_b02_3"],
                estimated_time=20,
                prerequisites=["b01"],
                next_lessons=["b03"]
            ),
            Lesson(
                lesson_id="b03",
                title="Buying Your First Crypto",
                difficulty=Difficulty.BEGINNER,
                content="""
# Buying Your First Crypto

Step-by-step guide to buying cryptocurrency.

## Step 1: Choose an Exchange

Popular exchanges:
- **Coinbase**: Beginner-friendly, US-based
- **Binance**: Largest exchange, many coins
- **Kraken**: Good security, advanced features

## Step 2: Verify Your Identity (KYC)

Most exchanges require:
- Government ID
- Proof of address
- Selfie verification

## Step 3: Deposit Funds

Options:
- Bank transfer (cheapest)
- Debit/credit card (instant but fees)
- Wire transfer (for large amounts)

## Step 4: Place Your Order

Two types:
1. **Market Order**: Buy immediately at current price
2. **Limit Order**: Set your price, wait for match

## Step 5: Secure Your Crypto

- Leave on exchange (convenient but risky)
- Transfer to personal wallet (more secure)

## Fees to Know:

- Trading fees: 0.1-0.5% per trade
- Withdrawal fees: Varies by coin
- Network fees: Paid to miners
                """,
                key_points=[
                    "Choose a reputable exchange",
                    "Complete KYC verification",
                    "Understand market vs limit orders",
                    "Consider fees when trading"
                ],
                examples=[
                    "Market order: Buy BTC at $97,500 right now",
                    "Limit order: Buy BTC only if price drops to $95,000",
                    "Withdrawal: Move BTC from exchange to your wallet"
                ],
                quiz_questions=["q_b03_1", "q_b03_2", "q_b03_3"],
                estimated_time=25,
                prerequisites=["b02"],
                next_lessons=["b04"]
            ),
            Lesson(
                lesson_id="b04",
                title="Understanding Market Basics",
                difficulty=Difficulty.BEGINNER,
                content="""
# Understanding Market Basics

Learn to read crypto markets and prices.

## Price Charts:

**Candlestick Chart**: Most common
- Green candle: Price went up
- Red candle: Price went down
- Body: Open to close price
- Wicks: High and low price

## Key Metrics:

1. **Market Cap**: Total value of all coins
   - Formula: Price × Circulating Supply
   - Indicates size and stability

2. **Volume**: Amount traded in 24 hours
   - High volume = more liquidity
   - Low volume = harder to buy/sell

3. **Circulating Supply**: Coins currently available
4. **Total Supply**: Maximum coins that will exist

## Market Sentiment:

- **Bull Market**: Prices rising, optimism
- **Bear Market**: Prices falling, pessimism
- **Sideways**: No clear direction

## Reading the Market:

- Check 24h change percentage
- Look at volume (is it increasing?)
- Compare to Bitcoin (market leader)
- Check Fear & Greed Index
                """,
                key_points=[
                    "Candlesticks show price movement",
                    "Market cap indicates coin size",
                    "Volume shows trading activity",
                    "Bull markets rise, bear markets fall"
                ],
                examples=[
                    "BTC market cap: $1.9T (largest)",
                    "High volume: $50B+ traded daily",
                    "Bull market: BTC $20k → $69k in 2021"
                ],
                quiz_questions=["q_b04_1", "q_b04_2", "q_b04_3"],
                estimated_time=20,
                prerequisites=["b03"],
                next_lessons=["b05"]
            ),
            Lesson(
                lesson_id="b05",
                title="Risk Management Basics",
                difficulty=Difficulty.BEGINNER,
                content="""
# Risk Management Basics

Protect your capital with smart risk management.

## Golden Rules:

1. **Only invest what you can afford to lose**
2. **Never put all eggs in one basket**
3. **Don't invest borrowed money**
4. **Have an exit strategy**

## Position Sizing:

**The 1-2% Rule**:
- Risk only 1-2% of portfolio per trade
- Example: $10,000 portfolio → Risk $100-200 per trade

## Diversification:

Don't put everything in one coin:
- 40-50%: Bitcoin (safest)
- 30-40%: Ethereum (second safest)
- 20-30%: Altcoins (higher risk/reward)

## Stop Losses:

Set a price where you'll sell to limit losses:
- Example: Buy BTC at $95,000
- Set stop loss at $90,000 (5% loss)
- Protects you from bigger losses

## Emotional Control:

- **FOMO** (Fear of Missing Out): Don't chase pumps
- **FUD** (Fear, Uncertainty, Doubt): Don't panic sell
- **Stick to your plan**: Have rules and follow them

## Common Mistakes:

- Investing rent money
- Buying at all-time highs
- Selling in panic
- No stop losses
- Over-trading
                """,
                key_points=[
                    "Only risk 1-2% per trade",
                    "Diversify across multiple coins",
                    "Use stop losses to limit losses",
                    "Control emotions (FOMO and FUD)"
                ],
                examples=[
                    "Good: Risk $100 on $10,000 portfolio",
                    "Bad: Risk $5,000 on $10,000 portfolio",
                    "Stop loss: Sell BTC at $90k if bought at $95k"
                ],
                quiz_questions=["q_b05_1", "q_b05_2", "q_b05_3"],
                estimated_time=25,
                prerequisites=["b04"],
                next_lessons=[]
            )
        ]
        
        return LearningPath(
            path_id="beginner",
            name="Crypto Fundamentals",
            description="Learn cryptocurrency basics from scratch",
            difficulty=Difficulty.BEGINNER,
            lessons=lessons,
            total_lessons=len(lessons),
            estimated_hours=2
        )
    
    def _create_intermediate_path(self) -> LearningPath:
        """Create intermediate learning path"""
        lessons = [
            Lesson(
                lesson_id="i01",
                title="Technical Analysis Fundamentals",
                difficulty=Difficulty.INTERMEDIATE,
                content="""
# Technical Analysis Fundamentals

Learn to read charts and identify trading opportunities.

## What is Technical Analysis?

Analyzing price charts to predict future movements based on:
- Historical price patterns
- Trading volume
- Technical indicators

## Key Concepts:

1. **Support**: Price level where buying pressure stops decline
2. **Resistance**: Price level where selling pressure stops rise
3. **Trend**: Overall direction (up, down, sideways)

## Chart Patterns:

**Bullish Patterns**:
- Higher highs and higher lows
- Breakout above resistance
- Cup and handle

**Bearish Patterns**:
- Lower highs and lower lows
- Breakdown below support
- Head and shoulders

## Timeframes:

- **1h/4h**: Day trading
- **1D**: Swing trading
- **1W**: Position trading

## Volume Analysis:

- High volume + price increase = Strong move
- Low volume + price increase = Weak move
- Volume confirms price action
                """,
                key_points=[
                    "Support and resistance are key levels",
                    "Trends show market direction",
                    "Volume confirms price movements",
                    "Different timeframes for different strategies"
                ],
                examples=[
                    "Support: BTC bounces at $90k multiple times",
                    "Resistance: BTC rejected at $100k three times",
                    "Uptrend: Series of higher highs and higher lows"
                ],
                quiz_questions=["q_i01_1", "q_i01_2", "q_i01_3"],
                estimated_time=30,
                prerequisites=[],
                next_lessons=["i02"]
            ),
            Lesson(
                lesson_id="i02",
                title="Essential Trading Indicators",
                difficulty=Difficulty.INTERMEDIATE,
                content="""
# Essential Trading Indicators

Master the most important technical indicators.

## 1. RSI (Relative Strength Index)

Measures momentum (0-100):
- **Below 30**: Oversold (potential buy)
- **Above 70**: Overbought (potential sell)
- **50**: Neutral

## 2. Moving Averages

Average price over time:
- **SMA 20**: Short-term trend
- **SMA 50**: Medium-term trend
- **SMA 200**: Long-term trend

**Golden Cross**: 50 SMA crosses above 200 SMA (bullish)
**Death Cross**: 50 SMA crosses below 200 SMA (bearish)

## 3. MACD (Moving Average Convergence Divergence)

Shows trend and momentum:
- **MACD line above signal**: Bullish
- **MACD line below signal**: Bearish
- **Histogram**: Strength of trend

## 4. Bollinger Bands

Volatility indicator:
- Price at upper band: Overbought
- Price at lower band: Oversold
- Bands squeeze: Breakout coming

## Using Multiple Indicators:

Don't rely on one indicator:
- RSI + MACD: Confirm momentum
- MA + Volume: Confirm trend
- Multiple timeframes: Confirm direction
                """,
                key_points=[
                    "RSI shows overbought/oversold conditions",
                    "Moving averages identify trends",
                    "MACD shows momentum changes",
                    "Use multiple indicators together"
                ],
                examples=[
                    "RSI 25 + Price at support = Strong buy signal",
                    "Golden cross + High volume = Bullish confirmation",
                    "MACD crossover + RSI rising = Momentum building"
                ],
                quiz_questions=["q_i02_1", "q_i02_2", "q_i02_3"],
                estimated_time=35,
                prerequisites=["i01"],
                next_lessons=["i03"]
            ),
            Lesson(
                lesson_id="i03",
                title="Trade Planning and Execution",
                difficulty=Difficulty.INTERMEDIATE,
                content="""
# Trade Planning and Execution

Learn to plan and execute profitable trades.

## The Trading Plan:

Every trade needs:
1. **Entry**: Where to buy
2. **Stop Loss**: Where to exit if wrong
3. **Target**: Where to take profit
4. **Position Size**: How much to risk

## Entry Strategies:

**Breakout Entry**:
- Wait for price to break resistance
- Enter on confirmation (volume + close above)

**Pullback Entry**:
- Wait for price to pull back to support
- Enter when bounce confirmed

**Reversal Entry**:
- Wait for trend change signals
- Enter on confirmation (RSI divergence, etc.)

## Setting Stop Losses:

Place below key levels:
- Below support for longs
- Above resistance for shorts
- 2-5% from entry typically

## Setting Targets:

Use risk/reward ratio:
- **Minimum 2:1**: Risk $100 to make $200
- **Ideal 3:1**: Risk $100 to make $300

Calculate:
- Entry: $95,000
- Stop: $90,000 (risk $5,000)
- Target: $105,000 (reward $10,000)
- R:R = 2:1 ✓

## Scaling Out:

Take profits in stages:
- 33% at Target 1 (2:1)
- 33% at Target 2 (3:1)
- 33% at Target 3 (5:1)

## Trade Journal:

Record every trade:
- Entry/exit prices
- Reason for trade
- What worked/didn't work
- Emotions felt
                """,
                key_points=[
                    "Every trade needs entry, stop, and target",
                    "Minimum 2:1 risk/reward ratio",
                    "Scale out at multiple targets",
                    "Keep a trade journal"
                ],
                examples=[
                    "Good trade: Risk $500 to make $1,500 (3:1)",
                    "Bad trade: Risk $1,000 to make $500 (0.5:1)",
                    "Scaling: Sell 33% at each target level"
                ],
                quiz_questions=["q_i03_1", "q_i03_2", "q_i03_3"],
                estimated_time=30,
                prerequisites=["i02"],
                next_lessons=["i04"]
            ),
            Lesson(
                lesson_id="i04",
                title="Psychology of Trading",
                difficulty=Difficulty.INTERMEDIATE,
                content="""
# Psychology of Trading

Master your emotions to become a better trader.

## Common Psychological Traps:

1. **FOMO (Fear of Missing Out)**
   - Chasing pumps
   - Buying at tops
   - Solution: Stick to your plan

2. **Revenge Trading**
   - Trading to recover losses
   - Taking bigger risks
   - Solution: Take a break after losses

3. **Overconfidence**
   - After winning streak
   - Taking excessive risk
   - Solution: Stay humble, follow rules

4. **Analysis Paralysis**
   - Too much information
   - Can't make decisions
   - Solution: Simplify your strategy

## Emotional Discipline:

**Before Trading**:
- Have a clear plan
- Know your entry/exit
- Accept potential loss

**During Trading**:
- Don't watch every tick
- Trust your analysis
- Don't move stop loss

**After Trading**:
- Review objectively
- Learn from mistakes
- Don't dwell on losses

## Building Good Habits:

1. **Trade with a plan**: No impulsive trades
2. **Risk management**: Always use stop losses
3. **Position sizing**: Never risk too much
4. **Take breaks**: Don't overtrade
5. **Stay healthy**: Sleep, exercise, eat well

## Dealing with Losses:

Losses are part of trading:
- Even pros lose 40-50% of trades
- Focus on overall profitability
- Learn from each loss
- Don't let emotions control you

## The 90/90/90 Rule:

90% of traders lose 90% of their money in 90 days.

Why?
- No plan
- Poor risk management
- Emotional trading
- Overtrading

Don't be part of this statistic!
                """,
                key_points=[
                    "Control emotions (FOMO, revenge trading)",
                    "Stick to your trading plan",
                    "Losses are normal, learn from them",
                    "Build disciplined trading habits"
                ],
                examples=[
                    "FOMO: Buying BTC at $69k because everyone else is",
                    "Revenge: Doubling position size after a loss",
                    "Discipline: Following stop loss even when painful"
                ],
                quiz_questions=["q_i04_1", "q_i04_2", "q_i04_3"],
                estimated_time=25,
                prerequisites=["i03"],
                next_lessons=[]
            )
        ]
        
        return LearningPath(
            path_id="intermediate",
            name="Technical Trading",
            description="Master technical analysis and trading strategies",
            difficulty=Difficulty.INTERMEDIATE,
            lessons=lessons,
            total_lessons=len(lessons),
            estimated_hours=2
        )
    
    def _create_advanced_path(self) -> LearningPath:
        """Create advanced learning path"""
        lessons = [
            Lesson(
                lesson_id="a01",
                title="Advanced Chart Patterns",
                difficulty=Difficulty.ADVANCED,
                content="""
# Advanced Chart Patterns

Master complex patterns for high-probability setups.

## Continuation Patterns:

**1. Bull Flag**
- Strong move up (flagpole)
- Consolidation (flag)
- Breakout continuation
- Target: Flagpole height added to breakout

**2. Ascending Triangle**
- Flat resistance
- Rising support
- Bullish breakout expected
- Target: Triangle height

**3. Cup and Handle**
- Rounded bottom (cup)
- Small pullback (handle)
- Breakout above rim
- Target: Cup depth

## Reversal Patterns:

**1. Head and Shoulders**
- Left shoulder, head, right shoulder
- Neckline break = reversal
- Target: Head to neckline distance

**2. Double Top/Bottom**
- Two peaks/troughs at same level
- Break of middle support/resistance
- Strong reversal signal

**3. Rising/Falling Wedge**
- Converging trendlines
- Rising wedge = bearish
- Falling wedge = bullish

## Pattern Trading Rules:

1. **Wait for confirmation**: Don't trade before breakout
2. **Volume matters**: Breakout needs volume
3. **Measure target**: Use pattern height
4. **Set stop loss**: Below pattern low
5. **Be patient**: Patterns take time to form
                """,
                key_points=[
                    "Continuation patterns suggest trend continues",
                    "Reversal patterns suggest trend changes",
                    "Wait for breakout confirmation",
                    "Use pattern height to set targets"
                ],
                examples=[
                    "Bull flag: BTC rallies $90k→$100k, consolidates, breaks to $110k",
                    "Head & shoulders: Three peaks, neckline break signals reversal",
                    "Cup & handle: Rounded bottom + small pullback = bullish"
                ],
                quiz_questions=["q_a01_1", "q_a01_2", "q_a01_3"],
                estimated_time=40,
                prerequisites=[],
                next_lessons=["a02"]
            ),
            Lesson(
                lesson_id="a02",
                title="Multi-Timeframe Analysis",
                difficulty=Difficulty.ADVANCED,
                content="""
# Multi-Timeframe Analysis

Align multiple timeframes for high-conviction trades.

## The Timeframe Hierarchy:

**Higher Timeframe** (1D, 1W):
- Shows overall trend
- Key support/resistance
- Major patterns

**Middle Timeframe** (4H):
- Entry timing
- Swing structure
- Confirmation signals

**Lower Timeframe** (1H):
- Precise entry
- Stop loss placement
- Quick confirmation

## Top-Down Analysis:

**Step 1: Weekly Chart**
- Identify major trend
- Mark key levels
- Note major patterns

**Step 2: Daily Chart**
- Confirm trend direction
- Find entry zones
- Check indicators

**Step 3: 4H Chart**
- Time your entry
- Set stop loss
- Confirm with indicators

**Step 4: 1H Chart**
- Execute entry
- Fine-tune stop
- Monitor position

## Alignment Rules:

**High Probability Setup**:
- Weekly: Uptrend
- Daily: Pullback to support
- 4H: Reversal pattern
- 1H: Entry signal

**Low Probability Setup**:
- Weekly: Downtrend
- Daily: Resistance overhead
- 4H: Bearish pattern
- 1H: Trying to buy

## Timeframe Conflicts:

When timeframes disagree:
- Higher timeframe wins
- Wait for alignment
- Reduce position size
- Tighter stop loss

## Practical Example:

**BTC Analysis**:
1. Weekly: Uptrend, above 200 MA
2. Daily: Pullback to 50 MA (support)
3. 4H: RSI oversold, bullish divergence
4. 1H: Hammer candle, volume spike

Result: High-probability long setup!
                """,
                key_points=[
                    "Higher timeframes show overall trend",
                    "Lower timeframes show entry timing",
                    "Align multiple timeframes for confirmation",
                    "Higher timeframe always wins conflicts"
                ],
                examples=[
                    "Aligned: Weekly up, Daily pullback, 4H reversal = BUY",
                    "Conflicted: Weekly down, Daily up = WAIT",
                    "Top-down: Start weekly, end hourly for entry"
                ],
                quiz_questions=["q_a02_1", "q_a02_2", "q_a02_3"],
                estimated_time=35,
                prerequisites=["a01"],
                next_lessons=["a03"]
            ),
            Lesson(
                lesson_id="a03",
                title="Position Sizing and Kelly Criterion",
                difficulty=Difficulty.ADVANCED,
                content="""
# Position Sizing and Kelly Criterion

Optimize position sizes mathematically for maximum growth.

## Kelly Criterion Formula:

**Kelly % = (Win Rate × Avg Win - Loss Rate × Avg Loss) / Avg Win**

Example:
- Win rate: 60%
- Avg win: 3R
- Loss rate: 40%
- Avg loss: 1R

Kelly = (0.6 × 3 - 0.4 × 1) / 3 = 0.47 = 47%

## Half Kelly (Recommended):

Full Kelly is aggressive, use Half Kelly:
- Half Kelly = 23.5% per trade
- More conservative
- Reduces volatility
- Still optimal growth

## Volatility-Based Sizing:

Adjust for coin volatility:

**Formula**: Position Size = Risk Amount / (ATR × Multiplier)

Example:
- Risk: $1,000
- BTC ATR: $2,000
- Multiplier: 2

Position = $1,000 / ($2,000 × 2) = 0.25 BTC

## Portfolio Heat:

Total risk across all positions:

**Rule**: Never exceed 6% total portfolio heat

Example:
- 3 positions open
- Each risking 2%
- Total heat: 6% ✓

## Scaling Strategies:

**Pyramid Up** (Winning trade):
- Add to winners
- Each add smaller than last
- Move stop to breakeven

**Scale Out** (Taking profits):
- Sell 33% at each target
- Lock in profits
- Let winners run

## Risk of Ruin:

Probability of losing entire account:

With proper sizing:
- 1% risk per trade: <1% ruin chance
- 5% risk per trade: 13% ruin chance
- 10% risk per trade: 40% ruin chance

Never risk more than 2% per trade!
                """,
                key_points=[
                    "Kelly Criterion optimizes position size",
                    "Use Half Kelly for safety",
                    "Adjust for volatility (ATR)",
                    "Never exceed 6% total portfolio heat"
                ],
                examples=[
                    "Kelly: 60% win rate, 3:1 R:R = 47% position",
                    "Half Kelly: 23.5% position (more conservative)",
                    "Portfolio heat: 3 trades × 2% = 6% total risk"
                ],
                quiz_questions=["q_a03_1", "q_a03_2", "q_a03_3"],
                estimated_time=40,
                prerequisites=["a02"],
                next_lessons=[]
            )
        ]
        
        return LearningPath(
            path_id="advanced",
            name="Advanced Strategies",
            description="Master advanced trading techniques and risk management",
            difficulty=Difficulty.ADVANCED,
            lessons=lessons,
            total_lessons=len(lessons),
            estimated_hours=2
        )
    
    def get_path(self, path_id: str) -> Optional[LearningPath]:
        """Get learning path by ID"""
        return self.paths.get(path_id)
    
    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        """Get specific lesson by ID"""
        for path in self.paths.values():
            for lesson in path.lessons:
                if lesson.lesson_id == lesson_id:
                    return lesson
        return None
    
    def get_all_paths(self) -> List[LearningPath]:
        """Get all learning paths"""
        return list(self.paths.values())
    
    async def start_lesson(self, user_id: int, lesson_id: str):
        """Mark lesson as started"""
        await self.db.execute("""
            INSERT OR REPLACE INTO lesson_progress
            (user_id, lesson_id, status, started_at)
            VALUES (?, ?, 'in_progress', ?)
        """, (user_id, lesson_id, datetime.now().isoformat()))
    
    async def complete_lesson(self, user_id: int, lesson_id: str, quiz_score: float):
        """Mark lesson as completed"""
        await self.db.execute("""
            UPDATE lesson_progress
            SET status = 'completed',
                completed_at = ?,
                quiz_score = ?
            WHERE user_id = ? AND lesson_id = ?
        """, (datetime.now().isoformat(), quiz_score, user_id, lesson_id))
    
    async def get_user_progress(self, user_id: int, path_id: str) -> Dict[str, Any]:
        """Get user's progress in a learning path"""
        path = self.get_path(path_id)
        if not path:
            return {}
        
        rows = await self.db.fetch_all("""
            SELECT lesson_id, status, quiz_score, started_at, completed_at
            FROM lesson_progress
            WHERE user_id = ?
        """, (user_id,))
        
        progress = {row['lesson_id']: row for row in rows}
        
        completed = sum(1 for lesson in path.lessons if progress.get(lesson.lesson_id, {}).get('status') == 'completed')
        
        return {
            'path_id': path_id,
            'total_lessons': path.total_lessons,
            'completed_lessons': completed,
            'progress_percent': (completed / path.total_lessons * 100) if path.total_lessons > 0 else 0,
            'lessons': progress
        }
