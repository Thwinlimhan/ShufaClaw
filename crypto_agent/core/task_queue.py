"""
Advanced Task Queue - Level 33

Sophisticated task execution system with:
- Parallel execution of independent tasks
- Dependency graph resolution
- Circuit breakers for failing APIs
- Exponential backoff retry logic
- Timeout handling
- Task prioritization

Solves the problem of slow sequential API calls by running
independent tasks in parallel while respecting dependencies.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class Task:
    """Represents a task to execute"""
    task_id: str
    name: str
    function: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10, higher = more important
    timeout: int = 30  # seconds
    retry_count: int = 3
    retry_delay: float = 2.0  # seconds
    on_failure: Optional[str] = None  # fallback strategy
    
    # Runtime state
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attempts: int = 0


@dataclass
class CircuitBreaker:
    """Circuit breaker for API endpoints"""
    name: str
    failure_threshold: int = 5
    timeout_duration: int = 300  # 5 minutes
    half_open_max_calls: int = 3
    
    # State
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    success_count: int = 0


class TaskQueue:
    """Advanced task queue with parallel execution and circuit breakers"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.execution_history: List[Dict] = []
        
    def add_task(self, task: Task):
        """Add a task to the queue"""
        self.tasks[task.task_id] = task
        logger.debug(f"Added task: {task.task_id}")
    
    def add_circuit_breaker(self, breaker: CircuitBreaker):
        """Add a circuit breaker for an API/service"""
        self.circuit_breakers[breaker.name] = breaker
        logger.debug(f"Added circuit breaker: {breaker.name}")
    
    async def execute_all(self) -> Dict[str, Any]:
        """
        Execute all tasks with dependency resolution and parallel execution
        
        Returns:
            Dict of task_id -> result
        """
        start_time = datetime.now()
        results = {}
        
        try:
            logger.info(f"Starting execution of {len(self.tasks)} tasks")
            
            # Build dependency graph
            dependency_graph = self._build_dependency_graph()
            
            # Execute in waves (tasks with no pending dependencies)
            while self.tasks:
                # Find tasks ready to execute
                ready_tasks = self._get_ready_tasks(dependency_graph, results)
                
                if not ready_tasks:
                    # Check if we're stuck (circular dependency or all failed)
                    pending = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
                    if pending:
                        logger.error(f"Stuck with {len(pending)} pending tasks - possible circular dependency")
                        for task in pending:
                            task.status = TaskStatus.SKIPPED
                            task.error = "Circular dependency or all dependencies failed"
                    break
                
                # Execute ready tasks in parallel
                logger.info(f"Executing {len(ready_tasks)} tasks in parallel")
                task_results = await self._execute_parallel(ready_tasks)
                
                # Store results and remove completed tasks
                for task_id, result in task_results.items():
                    results[task_id] = result
                    if task_id in self.tasks:
                        del self.tasks[task_id]
            
            # Log execution summary
            duration = (datetime.now() - start_time).total_seconds()
            self._log_execution_summary(results, duration)
            
            return results
            
        except Exception as e:
            logger.error(f"Task queue execution failed: {e}")
            return results
    
    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph"""
        graph = {}
        for task_id, task in self.tasks.items():
            graph[task_id] = task.depends_on.copy()
        return graph
    
    def _get_ready_tasks(
        self, 
        dependency_graph: Dict[str, List[str]], 
        completed: Dict[str, Any]
    ) -> List[Task]:
        """Get tasks ready to execute (all dependencies met)"""
        ready = []
        
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            dependencies = dependency_graph.get(task_id, [])
            if all(dep in completed for dep in dependencies):
                ready.append(task)
        
        # Sort by priority (higher first)
        ready.sort(key=lambda t: t.priority, reverse=True)
        
        return ready
    
    async def _execute_parallel(self, tasks: List[Task]) -> Dict[str, Any]:
        """Execute multiple tasks in parallel"""
        # Create coroutines for each task
        coroutines = [self._execute_task(task) for task in tasks]
        
        # Execute all in parallel
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # Map results back to task IDs
        task_results = {}
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                task.status = TaskStatus.FAILED
                task.error = str(result)
                task_results[task.task_id] = None
            else:
                task_results[task.task_id] = result
        
        return task_results
    
    async def _execute_task(self, task: Task) -> Any:
        """Execute a single task with retry logic and circuit breaker"""
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.now()
        
        # Check circuit breaker
        circuit_breaker = self._get_circuit_breaker_for_task(task)
        if circuit_breaker and not self._check_circuit_breaker(circuit_breaker):
            task.status = TaskStatus.SKIPPED
            task.error = f"Circuit breaker open for {circuit_breaker.name}"
            logger.warning(f"Task {task.task_id} skipped - circuit breaker open")
            
            # Try fallback if available
            if task.on_failure:
                return await self._execute_fallback(task)
            return None
        
        # Execute with retries
        for attempt in range(task.retry_count):
            task.attempts = attempt + 1
            
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    task.function(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
                
                # Success
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.end_time = datetime.now()
                
                # Record success in circuit breaker
                if circuit_breaker:
                    self._record_success(circuit_breaker)
                
                logger.debug(f"Task {task.task_id} completed successfully")
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"Task {task.task_id} timed out (attempt {attempt + 1}/{task.retry_count})")
                task.error = f"Timeout after {task.timeout}s"
                
                # Record failure in circuit breaker
                if circuit_breaker:
                    self._record_failure(circuit_breaker)
                
                if attempt < task.retry_count - 1:
                    # Exponential backoff
                    delay = task.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    task.status = TaskStatus.TIMEOUT
                    
            except Exception as e:
                logger.warning(f"Task {task.task_id} failed: {e} (attempt {attempt + 1}/{task.retry_count})")
                task.error = str(e)
                
                # Record failure in circuit breaker
                if circuit_breaker:
                    self._record_failure(circuit_breaker)
                
                if attempt < task.retry_count - 1:
                    # Exponential backoff
                    delay = task.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    task.status = TaskStatus.FAILED
        
        # All retries failed
        task.end_time = datetime.now()
        
        # Try fallback if available
        if task.on_failure:
            return await self._execute_fallback(task)
        
        return None
    
    async def _execute_fallback(self, task: Task) -> Any:
        """Execute fallback strategy"""
        try:
            if task.on_failure == "use_cached":
                logger.info(f"Task {task.task_id} using cached data")
                # In production, fetch from cache
                return {"cached": True, "data": None}
            elif task.on_failure == "skip":
                logger.info(f"Task {task.task_id} skipped")
                return None
            else:
                logger.warning(f"Unknown fallback strategy: {task.on_failure}")
                return None
        except Exception as e:
            logger.error(f"Fallback failed for {task.task_id}: {e}")
            return None
    
    def _get_circuit_breaker_for_task(self, task: Task) -> Optional[CircuitBreaker]:
        """Get circuit breaker for a task (based on function name)"""
        # Extract service name from function
        func_name = task.function.__name__
        
        # Map function to circuit breaker
        # In production, use more sophisticated mapping
        for breaker_name, breaker in self.circuit_breakers.items():
            if breaker_name.lower() in func_name.lower():
                return breaker
        
        return None
    
    def _check_circuit_breaker(self, breaker: CircuitBreaker) -> bool:
        """Check if circuit breaker allows execution"""
        if breaker.state == CircuitState.CLOSED:
            return True
        
        if breaker.state == CircuitState.OPEN:
            # Check if timeout has passed
            if breaker.last_failure_time:
                elapsed = (datetime.now() - breaker.last_failure_time).total_seconds()
                if elapsed >= breaker.timeout_duration:
                    # Move to half-open
                    breaker.state = CircuitState.HALF_OPEN
                    breaker.success_count = 0
                    logger.info(f"Circuit breaker {breaker.name} moved to HALF_OPEN")
                    return True
            return False
        
        if breaker.state == CircuitState.HALF_OPEN:
            # Allow limited calls to test recovery
            if breaker.success_count < breaker.half_open_max_calls:
                return True
            return False
        
        return False
    
    def _record_success(self, breaker: CircuitBreaker):
        """Record successful execution"""
        if breaker.state == CircuitState.HALF_OPEN:
            breaker.success_count += 1
            if breaker.success_count >= breaker.half_open_max_calls:
                # Recovered - close circuit
                breaker.state = CircuitState.CLOSED
                breaker.failure_count = 0
                logger.info(f"Circuit breaker {breaker.name} CLOSED (recovered)")
        elif breaker.state == CircuitState.CLOSED:
            # Reset failure count on success
            breaker.failure_count = 0
    
    def _record_failure(self, breaker: CircuitBreaker):
        """Record failed execution"""
        breaker.failure_count += 1
        breaker.last_failure_time = datetime.now()
        
        if breaker.state == CircuitState.CLOSED:
            if breaker.failure_count >= breaker.failure_threshold:
                # Open circuit
                breaker.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {breaker.name} OPENED (threshold reached)")
        
        elif breaker.state == CircuitState.HALF_OPEN:
            # Failed during testing - reopen
            breaker.state = CircuitState.OPEN
            breaker.success_count = 0
            logger.warning(f"Circuit breaker {breaker.name} REOPENED (test failed)")
    
    def _log_execution_summary(self, results: Dict[str, Any], duration: float):
        """Log execution summary"""
        total = len(results)
        successful = sum(1 for r in results.values() if r is not None)
        failed = total - successful
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_tasks': total,
            'successful': successful,
            'failed': failed,
            'duration_seconds': duration,
            'tasks_per_second': total / duration if duration > 0 else 0
        }
        
        self.execution_history.append(summary)
        
        logger.info(
            f"Execution complete: {successful}/{total} successful "
            f"in {duration:.2f}s ({summary['tasks_per_second']:.1f} tasks/s)"
        )
    
    def get_circuit_breaker_status(self) -> Dict[str, Dict]:
        """Get status of all circuit breakers"""
        status = {}
        for name, breaker in self.circuit_breakers.items():
            status[name] = {
                'state': breaker.state.value,
                'failure_count': breaker.failure_count,
                'last_failure': breaker.last_failure_time.isoformat() if breaker.last_failure_time else None,
                'success_count': breaker.success_count
            }
        return status
    
    def get_execution_stats(self) -> Dict:
        """Get execution statistics"""
        if not self.execution_history:
            return {'executions': 0}
        
        recent = self.execution_history[-10:]  # Last 10 executions
        
        return {
            'total_executions': len(self.execution_history),
            'avg_duration': sum(e['duration_seconds'] for e in recent) / len(recent),
            'avg_success_rate': sum(e['successful'] / e['total_tasks'] for e in recent) / len(recent),
            'avg_tasks_per_second': sum(e['tasks_per_second'] for e in recent) / len(recent),
            'last_execution': self.execution_history[-1] if self.execution_history else None
        }


# Example usage functions
async def example_morning_briefing():
    """Example: Optimized morning briefing data gathering"""
    queue = TaskQueue()
    
    # Add circuit breakers for APIs
    queue.add_circuit_breaker(CircuitBreaker(name="binance", failure_threshold=5))
    queue.add_circuit_breaker(CircuitBreaker(name="coingecko", failure_threshold=5))
    queue.add_circuit_breaker(CircuitBreaker(name="etherscan", failure_threshold=3))
    
    # Define tasks with dependencies
    # These can run in parallel (no dependencies)
    queue.add_task(Task(
        task_id="fetch_btc_price",
        name="Fetch BTC Price",
        function=fetch_price_mock,
        args=("BTC",),
        priority=10,
        timeout=10,
        on_failure="use_cached"
    ))
    
    queue.add_task(Task(
        task_id="fetch_eth_price",
        name="Fetch ETH Price",
        function=fetch_price_mock,
        args=("ETH",),
        priority=10,
        timeout=10,
        on_failure="use_cached"
    ))
    
    queue.add_task(Task(
        task_id="fetch_market_overview",
        name="Fetch Market Overview",
        function=fetch_market_mock,
        priority=8,
        timeout=15,
        on_failure="use_cached"
    ))
    
    queue.add_task(Task(
        task_id="fetch_fear_greed",
        name="Fetch Fear & Greed",
        function=fetch_fear_greed_mock,
        priority=7,
        timeout=10,
        on_failure="skip"
    ))
    
    # This depends on prices being fetched first
    queue.add_task(Task(
        task_id="calculate_portfolio",
        name="Calculate Portfolio Value",
        function=calculate_portfolio_mock,
        depends_on=["fetch_btc_price", "fetch_eth_price"],
        priority=9,
        timeout=5
    ))
    
    # This depends on everything
    queue.add_task(Task(
        task_id="generate_briefing",
        name="Generate AI Briefing",
        function=generate_briefing_mock,
        depends_on=["calculate_portfolio", "fetch_market_overview", "fetch_fear_greed"],
        priority=10,
        timeout=30
    ))
    
    # Execute all
    results = await queue.execute_all()
    
    return results


# Mock functions for testing
async def fetch_price_mock(symbol: str):
    """Mock price fetch"""
    await asyncio.sleep(0.5)  # Simulate API call
    return {symbol: 97500 if symbol == "BTC" else 3100}

async def fetch_market_mock():
    """Mock market data fetch"""
    await asyncio.sleep(1.0)
    return {"market_cap": "2.1T", "volume": "85B"}

async def fetch_fear_greed_mock():
    """Mock fear & greed fetch"""
    await asyncio.sleep(0.8)
    return {"value": 68, "classification": "Greed"}

async def calculate_portfolio_mock():
    """Mock portfolio calculation"""
    await asyncio.sleep(0.2)
    return {"total_value": 58350, "change_24h": 1.8}

async def generate_briefing_mock():
    """Mock briefing generation"""
    await asyncio.sleep(2.0)
    return {"briefing": "Market looking strong..."}
