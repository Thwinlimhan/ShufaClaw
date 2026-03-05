# Workflow Engine - Automated Multi-Step Workflows
# Enables complex sequences of actions that run on schedule or triggers

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import json

from crypto_agent import config
from crypto_agent.storage import database, workflow_db
from crypto_agent.data import prices as price_service, market as market_service
from crypto_agent.intelligence import research_agent, portfolio_optimizer
from crypto_agent.autonomous import reporter as briefing_service

logger = logging.getLogger(__name__)

# Configuration constants
STEP_TIMEOUT_SECONDS = 300  # 5 minutes per step
WORKFLOW_MAX_DURATION_SECONDS = 1800  # 30 minutes total

class WorkflowStep:
    """Represents a single step in a workflow."""
    
    def __init__(self, name: str, action: Callable, params: Dict = None):
        """
        Initialize a workflow step.
        
        Args:
            name: Human-readable step name
            action: Async function to execute
            params: Parameters to pass to the action
        """
        if not name or not isinstance(name, str):
            raise ValueError("Step name must be a non-empty string")
        
        if not callable(action):
            raise ValueError("Action must be callable")
        
        self.name = name
        self.action = action
        self.params = params or {}
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None
    
    async def execute(self, context: Dict) -> Any:
        """
        Execute this step with timeout protection.
        
        Args:
            context: Shared context dictionary
            
        Returns:
            Step result
            
        Raises:
            asyncio.TimeoutError: if step exceeds timeout
            Exception: if step execution fails
        """
        self.started_at = datetime.now()
        try:
            logger.info(f"Executing workflow step: {self.name}")
            
            # Execute with timeout protection
            if asyncio.iscoroutinefunction(self.action):
                self.result = await asyncio.wait_for(
                    self.action(context, **self.params),
                    timeout=STEP_TIMEOUT_SECONDS
                )
            else:
                # Run sync function in executor with timeout
                loop = asyncio.get_event_loop()
                self.result = await asyncio.wait_for(
                    loop.run_in_executor(None, self.action, context, **self.params),
                    timeout=STEP_TIMEOUT_SECONDS
                )
            
            self.completed_at = datetime.now()
            duration = (self.completed_at - self.started_at).total_seconds()
            logger.info(f"Step '{self.name}' completed in {duration:.2f}s")
            return self.result
            
        except asyncio.TimeoutError:
            self.error = f"Step timed out after {STEP_TIMEOUT_SECONDS}s"
            self.completed_at = datetime.now()
            logger.error(f"Step '{self.name}' timed out")
            raise
            
        except Exception as e:
            self.error = str(e)
            self.completed_at = datetime.now()
            logger.error(f"Step '{self.name}' failed: {e}", exc_info=True)
            raise

class Workflow:
    """Represents a complete workflow with multiple steps."""
    
    def __init__(self, name: str, description: str, steps: List[WorkflowStep]):
        """
        Initialize a workflow.
        
        Args:
            name: Workflow identifier
            description: Human-readable description
            steps: List of WorkflowStep objects
            
        Raises:
            ValueError: if inputs are invalid
        """
        if not name or not isinstance(name, str):
            raise ValueError("Workflow name must be a non-empty string")
        
        if not description or not isinstance(description, str):
            raise ValueError("Workflow description must be a non-empty string")
        
        if not steps or not isinstance(steps, list):
            raise ValueError("Steps must be a non-empty list")
        
        if not all(isinstance(s, WorkflowStep) for s in steps):
            raise ValueError("All steps must be WorkflowStep instances")
        
        self.name = name
        self.description = description
        self.steps = steps
        self.context = {}  # Shared context between steps
        self.started_at = None
        self.completed_at = None
        self.status = "pending"
    
    async def execute(self, bot=None, chat_id=None) -> Dict:
        """
        Execute all steps in sequence with timeout protection.
        
        Args:
            bot: Telegram bot instance (optional)
            chat_id: Telegram chat ID (optional)
            
        Returns:
            Dict with execution results
        """
        self.started_at = datetime.now()
        self.status = "running"
        self.context['bot'] = bot
        self.context['chat_id'] = chat_id
        
        steps_completed = 0
        error_message = None
        
        try:
            # Overall workflow timeout
            async with asyncio.timeout(WORKFLOW_MAX_DURATION_SECONDS):
                for step in self.steps:
                    try:
                        await step.execute(self.context)
                        steps_completed += 1
                        
                        # Store step result in context for next steps
                        self.context[f"step_{steps_completed}_result"] = step.result
                        
                    except asyncio.TimeoutError:
                        error_message = f"Step '{step.name}' timed out"
                        self.status = "partial" if steps_completed > 0 else "failed"
                        break
                        
                    except Exception as e:
                        error_message = f"Step '{step.name}' failed: {str(e)}"
                        self.status = "partial" if steps_completed > 0 else "failed"
                        break
                
                if steps_completed == len(self.steps):
                    self.status = "success"
            
        except asyncio.TimeoutError:
            error_message = f"Workflow exceeded maximum duration ({WORKFLOW_MAX_DURATION_SECONDS}s)"
            self.status = "partial" if steps_completed > 0 else "failed"
            logger.error(f"Workflow '{self.name}' timed out")
            
        except Exception as e:
            error_message = f"Workflow error: {str(e)}"
            self.status = "failed"
            logger.error(f"Workflow '{self.name}' failed: {e}", exc_info=True)
        
        finally:
            self.completed_at = datetime.now()
            duration = (self.completed_at - self.started_at).total_seconds()
            
            # Log workflow run to database
            try:
                workflow_db.log_workflow_run(
                    workflow_name=self.name,
                    started_at=self.started_at.isoformat(),
                    completed_at=self.completed_at.isoformat(),
                    status=self.status,
                    steps_completed=steps_completed,
                    total_steps=len(self.steps),
                    error_message=error_message,
                    duration_seconds=duration
                )
            except Exception as e:
                logger.error(f"Failed to log workflow run: {e}")
        
        return {
            'status': self.status,
            'steps_completed': steps_completed,
            'total_steps': len(self.steps),
            'duration': duration,
            'error': error_message
        }

class WorkflowEngine:
    """Main workflow engine that manages and executes workflows."""
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.scheduled_workflows: Dict[str, Dict] = {}
        self._register_builtin_workflows()
    
    def _register_builtin_workflows(self):
        """Register all built-in workflows."""
        
        # WORKFLOW 1: Morning Preparation
        morning_prep = Workflow(
            name="morning_preparation",
            description="Prepares data and sends morning briefing",
            steps=[
                WorkflowStep("Warm Cache", self._warm_cache),
                WorkflowStep("Scan Overnight Movements", self._scan_overnight),
                WorkflowStep("Check Near-Miss Alerts", self._check_near_alerts),
                WorkflowStep("Fetch Portfolio Values", self._fetch_portfolio),
                WorkflowStep("Generate Briefing", self._generate_briefing),
                WorkflowStep("Send Briefing", self._send_briefing)
            ]
        )
        self.register_workflow(morning_prep, schedule="daily", time="07:45")
        
        # WORKFLOW 2: Weekly Research Refresh
        weekly_research = Workflow(
            name="weekly_research",
            description="Weekly portfolio and watchlist research",
            steps=[
                WorkflowStep("Get Portfolio Coins", self._get_portfolio_coins),
                WorkflowStep("Get Watchlist Coins", self._get_watchlist_coins),
                WorkflowStep("Research Each Coin", self._research_coins),
                WorkflowStep("Update Insights", self._update_insights),
                WorkflowStep("Generate Week Review", self._generate_week_review),
                WorkflowStep("Send Report", self._send_report)
            ]
        )
        self.register_workflow(weekly_research, schedule="weekly", day="sunday", time="10:00")
        
        # WORKFLOW 3: Risk Review
        risk_review = Workflow(
            name="risk_review",
            description="Daily portfolio risk assessment",
            steps=[
                WorkflowStep("Calculate Current Risk", self._calculate_risk),
                WorkflowStep("Compare to Yesterday", self._compare_risk),
                WorkflowStep("Identify Risk Changes", self._identify_risk_changes),
                WorkflowStep("Generate Risk Alert", self._generate_risk_alert),
                WorkflowStep("Update Risk History", self._update_risk_history)
            ]
        )
        self.register_workflow(risk_review, schedule="daily", time="15:00")
        
        # WORKFLOW 4: Opportunity Screen
        opportunity_screen = Workflow(
            name="opportunity_screen",
            description="Scans for trading opportunities",
            steps=[
                WorkflowStep("Scan Oversold", self._scan_oversold),
                WorkflowStep("Scan High Volume", self._scan_high_volume),
                WorkflowStep("Scan Correlation Breaks", self._scan_correlation_breaks),
                WorkflowStep("Compile Opportunities", self._compile_opportunities),
                WorkflowStep("Rank Opportunities", self._rank_opportunities),
                WorkflowStep("Send Digest", self._send_opportunity_digest)
            ]
        )
        self.register_workflow(opportunity_screen, schedule="daily", time="09:00")
        self.register_workflow(opportunity_screen, schedule="daily", time="21:00")
    
    def register_workflow(self, workflow: Workflow, schedule: str = None, **schedule_params):
        """Register a workflow and optionally schedule it."""
        self.workflows[workflow.name] = workflow
        
        if schedule:
            self.scheduled_workflows[workflow.name] = {
                'schedule': schedule,
                'params': schedule_params,
                'last_run': None,
                'next_run': self._calculate_next_run(schedule, schedule_params)
            }
        
        logger.info(f"Registered workflow: {workflow.name}")
    
    def _calculate_next_run(self, schedule: str, params: Dict) -> datetime:
        """Calculate when a workflow should run next."""
        now = datetime.now()
        
        if schedule == "daily":
            time_str = params.get('time', '00:00')
            hour, minute = map(int, time_str.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time has passed today, schedule for tomorrow
            if next_run <= now:
                next_run += timedelta(days=1)
            
            return next_run
        
        elif schedule == "weekly":
            day = params.get('day', 'monday').lower()
            time_str = params.get('time', '00:00')
            hour, minute = map(int, time_str.split(':'))
            
            days_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            target_day = days_map.get(day, 0)
            current_day = now.weekday()
            
            days_ahead = (target_day - current_day) % 7
            if days_ahead == 0:
                # Same day - check if time has passed
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target_time <= now:
                    days_ahead = 7
            
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            return next_run
        
        return now
    
    async def run_workflow(self, workflow_name: str, bot=None, chat_id=None) -> Dict:
        """Execute a specific workflow by name."""
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        workflow = self.workflows[workflow_name]
        result = await workflow.execute(bot, chat_id)
        
        # Update last run time
        if workflow_name in self.scheduled_workflows:
            self.scheduled_workflows[workflow_name]['last_run'] = datetime.now()
        
        return result
    
    async def check_and_run_scheduled(self, bot=None, chat_id=None):
        """Check if any scheduled workflows need to run."""
        now = datetime.now()
        
        for workflow_name, schedule_info in self.scheduled_workflows.items():
            next_run = schedule_info['next_run']
            
            if next_run and now >= next_run:
                logger.info(f"Running scheduled workflow: {workflow_name}")
                
                try:
                    await self.run_workflow(workflow_name, bot, chat_id)
                    
                    # Calculate next run time
                    schedule_info['next_run'] = self._calculate_next_run(
                        schedule_info['schedule'],
                        schedule_info['params']
                    )
                    
                except Exception as e:
                    logger.error(f"Scheduled workflow '{workflow_name}' failed: {e}")
    
    def get_workflow_status(self) -> List[Dict]:
        """Get status of all workflows."""
        status_list = []
        
        for workflow_name, workflow in self.workflows.items():
            schedule_info = self.scheduled_workflows.get(workflow_name, {})
            last_run_data = workflow_db.get_last_workflow_run(workflow_name)
            
            status = {
                'name': workflow_name,
                'description': workflow.description,
                'scheduled': workflow_name in self.scheduled_workflows,
                'last_run': schedule_info.get('last_run'),
                'next_run': schedule_info.get('next_run'),
                'last_status': last_run_data.get('status') if last_run_data else None,
                'last_duration': last_run_data.get('duration_seconds') if last_run_data else None,
                'last_error': last_run_data.get('error_message') if last_run_data else None
            }
            
            status_list.append(status)
        
        return status_list
    
    # ==================== WORKFLOW STEP IMPLEMENTATIONS ====================
    
    # MORNING PREPARATION STEPS
    
    async def _warm_cache(self, context: Dict) -> Dict:
        """Pre-fetch and cache market data."""
        logger.info("Warming cache with market data...")
        
        # Fetch top coins
        top_coins = await market_service.get_top_cryptos(20)
        
        # Fetch fear & greed
        fng = await price_service.get_fear_greed_index()
        
        # Get portfolio positions
        positions = database.get_all_positions()
        
        # Fetch prices for portfolio coins
        for pos in positions:
            await price_service.get_price(pos['symbol'])
        
        return {
            'top_coins_count': len(top_coins),
            'portfolio_count': len(positions),
            'fng_value': fng.get('value') if fng else None
        }
    
    async def _scan_overnight(self, context: Dict) -> Dict:
        """Scan for significant overnight movements."""
        logger.info("Scanning overnight movements...")
        
        top_coins = await market_service.get_top_cryptos(50)
        
        big_movers = []
        for coin in top_coins:
            if abs(coin.get('change_24h', 0)) > 10:
                big_movers.append({
                    'symbol': coin['symbol'],
                    'change': coin['change_24h'],
                    'price': coin['price']
                })
        
        context['big_movers'] = big_movers
        return {'big_movers_count': len(big_movers)}
    
    async def _check_near_alerts(self, context: Dict) -> Dict:
        """Check for alerts that are close to triggering."""
        logger.info("Checking near-miss alerts...")
        
        alerts = database.get_active_alerts()
        near_misses = []
        
        for alert in alerts:
            price, _ = await price_service.get_price(alert['symbol'])
            if price:
                distance_pct = abs((price - alert['target_price']) / alert['target_price'] * 100)
                
                if distance_pct < 3:  # Within 3%
                    near_misses.append({
                        'symbol': alert['symbol'],
                        'target': alert['target_price'],
                        'current': price,
                        'distance': distance_pct
                    })
        
        context['near_alerts'] = near_misses
        return {'near_alerts_count': len(near_misses)}
    
    async def _fetch_portfolio(self, context: Dict) -> Dict:
        """Fetch current portfolio values."""
        logger.info("Fetching portfolio values...")
        
        positions = database.get_all_positions()
        total_value = 0
        total_pnl = 0
        
        for pos in positions:
            price, _ = await price_service.get_price(pos['symbol'])
            if price:
                value = pos['quantity'] * price
                cost = pos['quantity'] * pos['avg_price']
                pnl = value - cost
                
                total_value += value
                total_pnl += pnl
        
        context['portfolio_value'] = total_value
        context['portfolio_pnl'] = total_pnl
        
        return {
            'total_value': total_value,
            'total_pnl': total_pnl,
            'positions_count': len(positions)
        }
    
    async def _generate_briefing(self, context: Dict) -> str:
        """Generate the morning briefing content."""
        logger.info("Generating morning briefing...")
        
        # This would call your existing briefing service
        # For now, return a placeholder
        return "Morning briefing generated"
    
    async def _send_briefing(self, context: Dict) -> bool:
        """Send the morning briefing."""
        logger.info("Sending morning briefing...")
        
        bot = context.get('bot')
        chat_id = context.get('chat_id')
        
        if bot and chat_id:
            await briefing_service.Reporter.send_morning_briefing(bot, chat_id)
            return True
        
        return False
    
    # WEEKLY RESEARCH STEPS
    
    async def _get_portfolio_coins(self, context: Dict) -> List[str]:
        """Get all coins in portfolio."""
        positions = database.get_all_positions()
        coins = [pos['symbol'] for pos in positions]
        context['portfolio_coins'] = coins
        return coins
    
    async def _get_watchlist_coins(self, context: Dict) -> List[str]:
        """Get all coins in watchlist."""
        watchlist = database.get_research_watchlist()
        coins = [item['symbol'] for item in watchlist]
        context['watchlist_coins'] = coins
        return coins
    
    async def _research_coins(self, context: Dict) -> Dict:
        """Research each coin (lightweight version)."""
        logger.info("Researching coins...")
        
        portfolio_coins = context.get('portfolio_coins', [])
        watchlist_coins = context.get('watchlist_coins', [])
        all_coins = list(set(portfolio_coins + watchlist_coins))
        
        research_results = {}
        
        for symbol in all_coins[:10]:  # Limit to 10 to avoid timeout
            try:
                price, change = await price_service.get_price(symbol)
                research_results[symbol] = {
                    'price': price,
                    'change_24h': change,
                    'researched': True
                }
            except Exception as e:
                logger.error(f"Failed to research {symbol}: {e}")
                research_results[symbol] = {'error': str(e)}
        
        context['research_results'] = research_results
        return research_results
    
    async def _update_insights(self, context: Dict) -> int:
        """Update stored insights based on research."""
        logger.info("Updating insights...")
        
        # Placeholder - would analyze research and update database
        return 0
    
    async def _generate_week_review(self, context: Dict) -> str:
        """Generate weekly review report."""
        logger.info("Generating week review...")
        
        portfolio_coins = context.get('portfolio_coins', [])
        research_results = context.get('research_results', {})
        
        report = "📊 **PORTFOLIO WEEK IN REVIEW**\n\n"
        
        for symbol in portfolio_coins:
            result = research_results.get(symbol, {})
            change = result.get('change_24h', 0)
            emoji = "🟢" if change >= 0 else "🔴"
            
            report += f"{emoji} **{symbol}**: {change:+.1f}%\n"
        
        context['week_review'] = report
        return report
    
    async def _send_report(self, context: Dict) -> bool:
        """Send the weekly report."""
        logger.info("Sending weekly report...")
        
        bot = context.get('bot')
        chat_id = context.get('chat_id')
        report = context.get('week_review', '')
        
        if bot and chat_id and report:
            await bot.send_message(chat_id=chat_id, text=report, parse_mode='Markdown')
            return True
        
        return False
    
    # RISK REVIEW STEPS
    
    async def _calculate_risk(self, context: Dict) -> Dict:
        """Calculate current portfolio risk score."""
        logger.info("Calculating risk score...")
        
        optimizer = portfolio_optimizer.PortfolioOptimizer()
        risk_data = await optimizer.calculate_risk_metrics()
        
        context['current_risk'] = risk_data
        return risk_data
    
    async def _compare_risk(self, context: Dict) -> Dict:
        """Compare current risk to yesterday."""
        logger.info("Comparing risk to yesterday...")
        
        current_risk = context.get('current_risk', {})
        yesterday_risk = database.get_risk_history(days_ago=1)
        
        comparison = {
            'current': current_risk.get('risk_score', 0),
            'yesterday': yesterday_risk.get('risk_score', 0) if yesterday_risk else 0,
            'change': 0
        }
        
        if yesterday_risk:
            comparison['change'] = comparison['current'] - comparison['yesterday']
        
        context['risk_comparison'] = comparison
        return comparison
    
    async def _identify_risk_changes(self, context: Dict) -> List[Dict]:
        """Identify which positions caused risk changes."""
        logger.info("Identifying risk changes...")
        
        # Placeholder - would analyze position-level risk
        return []
    
    async def _generate_risk_alert(self, context: Dict) -> Optional[str]:
        """Generate risk alert if needed."""
        comparison = context.get('risk_comparison', {})
        
        if comparison.get('change', 0) > 10:  # Risk increased by 10+ points
            alert = (
                f"⚠️ **RISK ALERT**\n\n"
                f"Portfolio risk increased significantly:\n"
                f"Yesterday: {comparison['yesterday']:.1f}\n"
                f"Today: {comparison['current']:.1f}\n"
                f"Change: +{comparison['change']:.1f}\n\n"
                f"Review your positions."
            )
            
            bot = context.get('bot')
            chat_id = context.get('chat_id')
            
            if bot and chat_id:
                await bot.send_message(chat_id=chat_id, text=alert, parse_mode='Markdown')
            
            return alert
        
        return None
    
    async def _update_risk_history(self, context: Dict) -> bool:
        """Update risk history in database."""
        logger.info("Updating risk history...")
        
        current_risk = context.get('current_risk', {})
        database.save_risk_history(current_risk)
        
        return True
    
    # OPPORTUNITY SCREEN STEPS
    
    async def _scan_oversold(self, context: Dict) -> List[Dict]:
        """Scan for oversold conditions."""
        logger.info("Scanning for oversold coins...")
        
        # Placeholder - would use technical analysis
        oversold = []
        context['oversold'] = oversold
        return oversold
    
    async def _scan_high_volume(self, context: Dict) -> List[Dict]:
        """Scan for high volume spikes."""
        logger.info("Scanning for high volume...")
        
        high_volume = []
        context['high_volume'] = high_volume
        return high_volume
    
    async def _scan_correlation_breaks(self, context: Dict) -> List[Dict]:
        """Scan for correlation breaks."""
        logger.info("Scanning for correlation breaks...")
        
        breaks = []
        context['correlation_breaks'] = breaks
        return breaks
    
    async def _compile_opportunities(self, context: Dict) -> List[Dict]:
        """Compile all opportunities found."""
        logger.info("Compiling opportunities...")
        
        opportunities = []
        opportunities.extend(context.get('oversold', []))
        opportunities.extend(context.get('high_volume', []))
        opportunities.extend(context.get('correlation_breaks', []))
        
        context['all_opportunities'] = opportunities
        return opportunities
    
    async def _rank_opportunities(self, context: Dict) -> List[Dict]:
        """Rank opportunities by quality."""
        logger.info("Ranking opportunities...")
        
        opportunities = context.get('all_opportunities', [])
        
        # Placeholder - would use Claude to rank
        ranked = sorted(opportunities, key=lambda x: x.get('score', 0), reverse=True)
        
        context['ranked_opportunities'] = ranked
        return ranked
    
    async def _send_opportunity_digest(self, context: Dict) -> bool:
        """Send opportunity digest if quality opportunities found."""
        logger.info("Sending opportunity digest...")
        
        opportunities = context.get('ranked_opportunities', [])
        
        if len(opportunities) >= 2:
            bot = context.get('bot')
            chat_id = context.get('chat_id')
            
            if bot and chat_id:
                msg = "📡 **OPPORTUNITY DIGEST**\n\n"
                msg += f"Found {len(opportunities)} opportunities:\n\n"
                
                for opp in opportunities[:5]:
                    msg += f"• {opp.get('symbol', 'Unknown')}\n"
                
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
                return True
        
        return False

# Global workflow engine instance
workflow_engine = WorkflowEngine()
