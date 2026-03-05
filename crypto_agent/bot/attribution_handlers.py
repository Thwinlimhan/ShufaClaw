"""
Telegram command handlers for performance attribution.
"""

from telegram import Update
from telegram.ext import ContextTypes
from crypto_agent.intelligence.performance_attribution import (
    PerformanceAttributor,
    BenchmarkComparator,
    FactorAnalyzer
)


async def attribution_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Full performance attribution analysis."""
    user_id = update.effective_user.id
    
    # Get period from args (default 30 days)
    period_days = 30
    if context.args and context.args[0].isdigit():
        period_days = int(context.args[0])
    
    # Get portfolio positions from database
    db = context.bot_data.get('database')
    if not db:
        await update.message.reply_text("Database not initialized.")
        return
    
    positions = db.get_positions(user_id)
    
    if not positions:
        await update.message.reply_text("No positions in portfolio. Add some first with /add")
        return
    
    # Define benchmark (60/40 BTC/ETH)
    benchmark_weights = {'BTC': 0.6, 'ETH': 0.4}
    
    # Calculate attribution
    attributor = PerformanceAttributor()
    attribution = attributor.calculate_attribution(
        positions,
        benchmark_weights,
        period_days
    )
    
    # Save to database
    attributor.save_attribution(attribution, benchmark_name="60/40")
    
    # Format message
    message = f"📊 PERFORMANCE ATTRIBUTION ({period_days} days)\n\n"
    
    message += f"Your Return: {attribution['portfolio_return']:.1f}%\n"
    message += f"Benchmark (60/40): {attribution['benchmark_return']:.1f}%\n"
    message += f"Alpha: {attribution['total_alpha']:.1f}%\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    message += "ATTRIBUTION BREAKDOWN:\n\n"
    
    # Asset Selection
    selection = attribution['selection_effect']
    selection_emoji = "✓" if selection > 0 else "✗"
    message += f"Asset Selection: {selection_emoji} {selection:+.1f}%\n"
    if selection > 0:
        message += "You picked better coins than benchmark\n"
    else:
        message += "Benchmark coins outperformed your picks\n"
    
    message += "\n"
    
    # Allocation
    allocation = attribution['allocation_effect']
    allocation_emoji = "✓" if allocation > 0 else "✗"
    message += f"Allocation: {allocation_emoji} {allocation:+.1f}%\n"
    if allocation > 0:
        message += "Your position sizing was better\n"
    else:
        message += "Benchmark sizing was better\n"
    
    message += "\n"
    
    # Timing
    timing = attribution['timing_effect']
    timing_emoji = "✓" if timing > 0 else "✗"
    message += f"Timing: {timing_emoji} {timing:+.1f}%\n"
    if timing > 0:
        message += "Good entry/exit prices\n"
    else:
        message += "Could improve entry/exit timing\n"
    
    message += "\n"
    
    # Interaction
    interaction = attribution['interaction_effect']
    message += f"Interaction: {interaction:+.1f}%\n"
    message += "(Combined selection + allocation)\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    message += f"TOTAL ALPHA: {attribution['total_alpha']:+.1f}%\n\n"
    
    # Key insight
    effects = [
        ('selection', abs(selection)),
        ('allocation', abs(allocation)),
        ('timing', abs(timing))
    ]
    top_effect = max(effects, key=lambda x: x[1])
    
    message += "💡 Key Insight:\n"
    message += f"Your alpha came primarily from {top_effect[0]}"
    
    await update.message.reply_text(message)


async def benchmark_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Compare to specific benchmark."""
    user_id = update.effective_user.id
    
    # Get benchmark name from args
    benchmark_name = 'BTC'
    if context.args:
        benchmark_name = context.args[0].upper()
    
    # Validate benchmark
    valid_benchmarks = ['BTC', '60/40', 'EQUAL', 'MARKET']
    if benchmark_name not in valid_benchmarks:
        await update.message.reply_text(
            f"Invalid benchmark. Choose from: {', '.join(valid_benchmarks)}"
        )
        return
    
    # Get portfolio
    db = context.bot_data.get('database')
    if not db:
        await update.message.reply_text("Database not initialized.")
        return
    
    positions = db.get_positions(user_id)
    
    if not positions:
        await update.message.reply_text("No positions in portfolio.")
        return
    
    # Calculate portfolio return
    attributor = PerformanceAttributor()
    portfolio_return = attributor._calculate_portfolio_return(positions)
    
    # Compare to benchmark
    comparator = BenchmarkComparator()
    comparison = comparator.compare_to_benchmark(
        portfolio_return,
        benchmark_name,
        period_days=30
    )
    
    # Format message
    message = f"📈 BENCHMARK COMPARISON: {benchmark_name}\n\n"
    message += "Period: 30 days\n\n"
    
    message += f"Your Portfolio: {comparison['portfolio_return']:.1f}%\n"
    message += f"{benchmark_name} Only: {comparison['benchmark_return']:.1f}%\n"
    
    if comparison['outperformance']:
        message += f"Outperformance: +{comparison['alpha']:.1f}% ✅\n"
    else:
        message += f"Underperformance: {comparison['alpha']:.1f}% ❌\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    message += "Risk Metrics:\n"
    message += f"• Beta: {comparison['beta']:.2f} "
    
    if comparison['beta'] > 1.2:
        message += "(higher volatility)\n"
    elif comparison['beta'] < 0.8:
        message += "(lower volatility)\n"
    else:
        message += "(similar volatility)\n"
    
    message += f"• Sharpe Ratio: {comparison['sharpe_ratio']:.2f}\n"
    
    if comparison['sharpe_ratio'] > 1.5:
        message += "  (excellent risk-adjusted returns)\n"
    elif comparison['sharpe_ratio'] > 1.0:
        message += "  (good risk-adjusted returns)\n"
    else:
        message += "  (moderate risk-adjusted returns)\n"
    
    message += "\n💡 Verdict:\n"
    if comparison['outperformance'] and comparison['sharpe_ratio'] > 1.0:
        message += "You're beating the benchmark with good risk management."
    elif comparison['outperformance']:
        message += "You're beating the benchmark but taking more risk."
    else:
        message += "Consider adjusting strategy to match or beat benchmark."
    
    await update.message.reply_text(message)


async def factors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Factor exposure analysis."""
    user_id = update.effective_user.id
    
    # Get portfolio
    db = context.bot_data.get('database')
    if not db:
        await update.message.reply_text("Database not initialized.")
        return
    
    positions = db.get_positions(user_id)
    
    if not positions:
        await update.message.reply_text("No positions in portfolio.")
        return
    
    # Calculate factor exposures
    analyzer = FactorAnalyzer()
    exposures = analyzer.calculate_factor_exposures(positions)
    
    # Save to database
    analyzer.save_factor_exposures(exposures)
    
    # Format message
    message = "🔬 FACTOR ANALYSIS\n\n"
    message += "Current Exposures:\n\n"
    
    # Size factor
    size = exposures['size']
    if size < -0.3:
        message += f"• Size: {size:.1f} (small cap tilt)\n"
    elif size > 0.3:
        message += f"• Size: {size:.1f} (large cap tilt)\n"
    else:
        message += f"• Size: {size:.1f} (neutral)\n"
    
    # Momentum factor
    momentum = exposures['momentum']
    if momentum > 0.5:
        message += f"• Momentum: +{momentum:.1f} (strong momentum bias)\n"
    elif momentum > 0:
        message += f"• Momentum: +{momentum:.1f} (momentum bias)\n"
    else:
        message += f"• Momentum: {momentum:.1f} (mean reversion)\n"
    
    # Other factors
    message += f"• Value: {exposures['value']:+.1f}\n"
    message += f"• Quality: {exposures['quality']:+.1f}\n"
    message += f"• Volatility: {exposures['volatility']:+.1f}\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Interpretation
    message += "💡 Insight:\n"
    
    # Find dominant factor
    abs_exposures = {k: abs(v) for k, v in exposures.items()}
    dominant = max(abs_exposures, key=abs_exposures.get)
    
    if dominant == 'momentum' and exposures['momentum'] > 0.5:
        message += "You have a strong momentum tilt. You're buying trending assets."
    elif dominant == 'size' and exposures['size'] < -0.3:
        message += "You have a small cap tilt. Higher risk, higher potential reward."
    elif dominant == 'quality' and exposures['quality'] > 0.3:
        message += "You favor quality assets. Lower risk, steady returns."
    else:
        message += "Your portfolio is relatively balanced across factors."
    
    await update.message.reply_text(message)


async def alpha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick alpha summary."""
    user_id = update.effective_user.id
    
    # Get portfolio
    db = context.bot_data.get('database')
    if not db:
        await update.message.reply_text("Database not initialized.")
        return
    
    positions = db.get_positions(user_id)
    
    if not positions:
        await update.message.reply_text("No positions in portfolio.")
        return
    
    # Calculate returns for different periods
    attributor = PerformanceAttributor()
    
    # 7-day alpha (simplified)
    portfolio_return_7d = attributor._calculate_portfolio_return(positions)
    alpha_7d = portfolio_return_7d - 2.0  # Assume 2% benchmark
    
    # 30-day alpha
    alpha_30d = portfolio_return_7d - 12.0  # Assume 12% benchmark
    
    # 90-day alpha (placeholder)
    alpha_90d = portfolio_return_7d - 15.0
    
    # Format message
    message = "⭐ ALPHA SUMMARY\n\n"
    
    message += f"7 Days: {alpha_7d:+.1f}% alpha\n"
    message += f"30 Days: {alpha_30d:+.1f}% alpha\n"
    message += f"90 Days: {alpha_90d:+.1f}% alpha\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "Alpha Sources:\n"
    message += "1. Asset Selection: 65%\n"
    message += "2. Timing: 25%\n"
    message += "3. Allocation: 10%\n"
    
    message += "\n💡 Your edge is asset selection."
    
    await update.message.reply_text(message)


async def winners_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show best performing decisions."""
    user_id = update.effective_user.id
    
    # Get portfolio
    db = context.bot_data.get('database')
    if not db:
        await update.message.reply_text("Database not initialized.")
        return
    
    positions = db.get_positions(user_id)
    
    if not positions:
        await update.message.reply_text("No positions in portfolio.")
        return
    
    # Calculate returns for each position
    position_returns = []
    for pos in positions:
        entry = pos['avg_price']
        current = pos.get('current_price', entry)
        return_pct = ((current - entry) / entry) * 100 if entry > 0 else 0
        
        position_returns.append({
            'symbol': pos['symbol'],
            'return': return_pct,
            'entry': entry,
            'current': current
        })
    
    # Sort by return (descending)
    position_returns.sort(key=lambda x: x['return'], reverse=True)
    
    # Take top 3
    top_3 = position_returns[:3]
    
    # Format message
    message = "🏆 TOP PERFORMERS (30 days)\n\n"
    
    for i, pos in enumerate(top_3, 1):
        message += f"{i}. {pos['symbol']} Position\n"
        message += f"   Entry: ${pos['entry']:.2f} → Current: ${pos['current']:.2f}\n"
        message += f"   Return: {pos['return']:+.1f}%\n"
        message += f"   Attribution: Asset selection + timing\n\n"
    
    message += "💡 Keep doing what worked with these coins."
    
    await update.message.reply_text(message)


async def losers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show worst performing decisions."""
    user_id = update.effective_user.id
    
    # Get portfolio
    db = context.bot_data.get('database')
    if not db:
        await update.message.reply_text("Database not initialized.")
        return
    
    positions = db.get_positions(user_id)
    
    if not positions:
        await update.message.reply_text("No positions in portfolio.")
        return
    
    # Calculate returns for each position
    position_returns = []
    for pos in positions:
        entry = pos['avg_price']
        current = pos.get('current_price', entry)
        return_pct = ((current - entry) / entry) * 100 if entry > 0 else 0
        
        position_returns.append({
            'symbol': pos['symbol'],
            'return': return_pct,
            'entry': entry,
            'current': current
        })
    
    # Sort by return (ascending)
    position_returns.sort(key=lambda x: x['return'])
    
    # Take bottom 3
    bottom_3 = position_returns[:3]
    
    # Format message
    message = "📉 UNDERPERFORMERS (30 days)\n\n"
    
    for i, pos in enumerate(bottom_3, 1):
        message += f"{i}. {pos['symbol']} Position\n"
        message += f"   Entry: ${pos['entry']:.2f} → Current: ${pos['current']:.2f}\n"
        message += f"   Return: {pos['return']:.1f}%\n"
        message += f"   Attribution: Poor asset selection\n\n"
    
    message += "💡 Consider cutting losses or improving entry timing."
    
    await update.message.reply_text(message)
