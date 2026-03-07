"""
REST API Server (Level 37)

Exposes all bot features via REST API with authentication,
rate limiting, and TradingView webhook support.
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio
import hashlib
import hmac
import secrets
from enum import Enum
from crypto_agent import config


# ============================================================================
# Request/Response Models
# ============================================================================

class PortfolioResponse(BaseModel):
    """Portfolio data response"""
    total_value: float
    positions: List[Dict[str, Any]]
    pnl_24h: float
    pnl_percent_24h: float


class AlertRequest(BaseModel):
    """Create price alert request"""
    symbol: str
    target_price: float
    direction: str = Field(..., pattern="^(above|below)$")
    message: Optional[str] = None


class AlertResponse(BaseModel):
    """Alert response"""
    alert_id: int
    symbol: str
    target_price: float
    direction: str
    active: bool
    created_at: str


class ProposalRequest(BaseModel):
    """Generate trade proposal request"""
    symbol: str
    timeframe: str = "4h"
    risk_percent: Optional[float] = 1.0


class ProposalResponse(BaseModel):
    """Trade proposal response"""
    proposal_id: str
    symbol: str
    setup_type: str
    direction: str
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: float
    target_3: Optional[float]
    position_size_usd: float
    risk_amount: float
    reward_risk_ratio: float
    win_probability: float
    expected_value: float
    reasoning: str


class TradingViewWebhook(BaseModel):
    """TradingView webhook payload"""
    symbol: str
    action: str = Field(..., pattern="^(buy|sell|close)$")
    price: float
    strategy: Optional[str] = None
    timeframe: Optional[str] = None
    message: Optional[str] = None


class MarketDataResponse(BaseModel):
    """Market data response"""
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    market_cap: Optional[float] = None


class AnalysisRequest(BaseModel):
    """Technical analysis request"""
    symbol: str
    timeframe: str = "4h"


class AnalysisResponse(BaseModel):
    """Technical analysis response"""
    symbol: str
    timeframe: str
    price: float
    rsi: float
    trend: str
    support: float
    resistance: float
    recommendation: str


# ============================================================================
# API Server
# ============================================================================

class APIServer:
    """REST API server for crypto agent"""
    
    def __init__(self, bot_data: Dict, config: Dict):
        self.bot_data = bot_data
        self.config = config
        self.app = self._create_app()
        
        # API keys (in production, store in database)
        self.api_keys = {
            config.get('API_KEY', 'demo_key'): {
                'user_id': config.get('ALLOWED_USER_ID'),
                'rate_limit': 100,  # requests per hour
                'created_at': datetime.now()
            }
        }
        
        # Rate limiting
        self.rate_limits = {}  # key: (api_key, endpoint) -> count
        
    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(
            title="Crypto Agent API",
            description="REST API for crypto trading intelligence bot",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.CORS_ORIGINS,  # In production, specify allowed origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes(app)
        
        return app
    
    def _register_routes(self, app: FastAPI):
        """Register all API routes"""
        
        # Health check
        @app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        # Portfolio endpoints
        @app.get("/portfolio", response_model=PortfolioResponse)
        async def get_portfolio(api_key: str = Depends(self._verify_api_key)):
            return await self._get_portfolio(api_key)
        
        @app.post("/portfolio/position")
        async def add_position(
            symbol: str,
            amount: float,
            entry_price: float,
            api_key: str = Depends(self._verify_api_key)
        ):
            return await self._add_position(api_key, symbol, amount, entry_price)
        
        # Alert endpoints
        @app.post("/alerts", response_model=AlertResponse)
        async def create_alert(
            alert: AlertRequest,
            api_key: str = Depends(self._verify_api_key)
        ):
            return await self._create_alert(api_key, alert)
        
        @app.get("/alerts", response_model=List[AlertResponse])
        async def get_alerts(api_key: str = Depends(self._verify_api_key)):
            return await self._get_alerts(api_key)
        
        @app.delete("/alerts/{alert_id}")
        async def delete_alert(
            alert_id: int,
            api_key: str = Depends(self._verify_api_key)
        ):
            return await self._delete_alert(api_key, alert_id)
        
        # Trade proposal endpoints
        @app.post("/proposals", response_model=ProposalResponse)
        async def generate_proposal(
            request: ProposalRequest,
            api_key: str = Depends(self._verify_api_key)
        ):
            return await self._generate_proposal(api_key, request)
        
        @app.get("/proposals")
        async def get_proposals(api_key: str = Depends(self._verify_api_key)):
            return await self._get_proposals(api_key)
        
        # Market data endpoints
        @app.get("/market/{symbol}", response_model=MarketDataResponse)
        async def get_market_data(
            symbol: str,
            api_key: str = Depends(self._verify_api_key)
        ):
            return await self._get_market_data(api_key, symbol)
        
        @app.get("/market/top/{limit}")
        async def get_top_coins(
            limit: int = 10,
            api_key: str = Depends(self._verify_api_key)
        ):
            return await self._get_top_coins(api_key, limit)
        
        # Analysis endpoints
        @app.post("/analysis", response_model=AnalysisResponse)
        async def analyze_symbol(
            request: AnalysisRequest,
            api_key: str = Depends(self._verify_api_key)
        ):
            return await self._analyze_symbol(api_key, request)
        
        # TradingView webhook
        @app.post("/webhook/tradingview")
        async def tradingview_webhook(
            webhook: TradingViewWebhook,
            request: Request,
            x_webhook_secret: Optional[str] = Header(None)
        ):
            return await self._handle_tradingview_webhook(webhook, x_webhook_secret)
        
        # Journal endpoints
        @app.post("/journal")
        async def add_journal_entry(
            entry: str,
            symbol: Optional[str] = None,
            api_key: str = Depends(self._verify_api_key)
        ):
            return await self._add_journal_entry(api_key, entry, symbol)
        
        @app.get("/journal")
        async def get_journal(
            days: int = 7,
            api_key: str = Depends(self._verify_api_key)
        ):
            return await self._get_journal(api_key, days)
    
    async def _verify_api_key(self, authorization: str = Header(...)) -> str:
        """Verify API key from Authorization header"""
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        api_key = authorization.replace("Bearer ", "")
        
        if api_key not in self.api_keys:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Check rate limit
        key_data = self.api_keys[api_key]
        rate_key = (api_key, datetime.now().strftime("%Y-%m-%d-%H"))
        
        if rate_key not in self.rate_limits:
            self.rate_limits[rate_key] = 0
        
        self.rate_limits[rate_key] += 1
        
        if self.rate_limits[rate_key] > key_data['rate_limit']:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        return api_key
    
    # ========================================================================
    # Portfolio Endpoints
    # ========================================================================
    
    async def _get_portfolio(self, api_key: str) -> PortfolioResponse:
        """Get portfolio data"""
        db = self.bot_data.get('db')
        price_service = self.bot_data.get('price_service')
        
        if not db or not price_service:
            raise HTTPException(status_code=500, detail="Services not available")
        
        user_id = self.api_keys[api_key]['user_id']
        positions = await db.get_positions(user_id)
        
        total_value = 0
        pnl_24h = 0
        
        for pos in positions:
            price_data = await price_service.get_price(pos['symbol'])
            if price_data:
                current_price = price_data['price']
                value = pos['amount'] * current_price
                total_value += value
                
                # Calculate 24h P&L (simplified)
                change_24h = price_data.get('change_24h', 0)
                pnl_24h += value * (change_24h / 100)
        
        pnl_percent_24h = (pnl_24h / total_value * 100) if total_value > 0 else 0
        
        return PortfolioResponse(
            total_value=total_value,
            positions=positions,
            pnl_24h=pnl_24h,
            pnl_percent_24h=pnl_percent_24h
        )
    
    async def _add_position(
        self,
        api_key: str,
        symbol: str,
        amount: float,
        entry_price: float
    ):
        """Add portfolio position"""
        db = self.bot_data.get('db')
        if not db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        user_id = self.api_keys[api_key]['user_id']
        
        await db.add_position(user_id, symbol, amount, entry_price)
        
        return {
            "success": True,
            "message": f"Added {amount} {symbol} at ${entry_price}"
        }
    
    # ========================================================================
    # Alert Endpoints
    # ========================================================================
    
    async def _create_alert(self, api_key: str, alert: AlertRequest) -> AlertResponse:
        """Create price alert"""
        db = self.bot_data.get('db')
        if not db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        user_id = self.api_keys[api_key]['user_id']
        
        alert_id = await db.create_alert(
            user_id,
            alert.symbol,
            alert.target_price,
            alert.direction,
            alert.message
        )
        
        return AlertResponse(
            alert_id=alert_id,
            symbol=alert.symbol,
            target_price=alert.target_price,
            direction=alert.direction,
            active=True,
            created_at=datetime.now().isoformat()
        )
    
    async def _get_alerts(self, api_key: str) -> List[AlertResponse]:
        """Get all active alerts"""
        db = self.bot_data.get('db')
        if not db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        user_id = self.api_keys[api_key]['user_id']
        alerts = await db.get_active_alerts(user_id)
        
        return [
            AlertResponse(
                alert_id=a['id'],
                symbol=a['symbol'],
                target_price=a['target_price'],
                direction=a['direction'],
                active=a['active'],
                created_at=a['created_at']
            )
            for a in alerts
        ]
    
    async def _delete_alert(self, api_key: str, alert_id: int):
        """Delete alert"""
        db = self.bot_data.get('db')
        if not db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        await db.delete_alert(alert_id)
        
        return {"success": True, "message": f"Alert {alert_id} deleted"}
    
    # ========================================================================
    # Trade Proposal Endpoints
    # ========================================================================
    
    async def _generate_proposal(
        self,
        api_key: str,
        request: ProposalRequest
    ) -> ProposalResponse:
        """Generate trade proposal"""
        proposer = self.bot_data.get('trade_proposer')
        if not proposer:
            raise HTTPException(status_code=500, detail="Trade proposer not available")
        
        proposal = await proposer.generate_proposal(
            request.symbol,
            request.timeframe,
            request.risk_percent
        )
        
        if not proposal:
            raise HTTPException(
                status_code=404,
                detail=f"No valid setup found for {request.symbol}"
            )
        
        # Save proposal
        await proposer.save_proposal(proposal)
        
        return ProposalResponse(
            proposal_id=proposal.proposal_id,
            symbol=proposal.symbol,
            setup_type=proposal.setup_type.value,
            direction=proposal.direction,
            entry_price=proposal.entry_price,
            stop_loss=proposal.stop_loss,
            target_1=proposal.target_1,
            target_2=proposal.target_2,
            target_3=proposal.target_3,
            position_size_usd=proposal.position_size_usd,
            risk_amount=proposal.risk_amount,
            reward_risk_ratio=proposal.reward_risk_ratio,
            win_probability=proposal.win_probability,
            expected_value=proposal.expected_value,
            reasoning=proposal.reasoning
        )
    
    async def _get_proposals(self, api_key: str):
        """Get active proposals"""
        proposer = self.bot_data.get('trade_proposer')
        if not proposer:
            raise HTTPException(status_code=500, detail="Trade proposer not available")
        
        proposals = await proposer.get_active_proposals()
        
        return [
            {
                "proposal_id": p.proposal_id,
                "symbol": p.symbol,
                "setup_type": p.setup_type.value,
                "direction": p.direction,
                "entry_price": p.entry_price,
                "stop_loss": p.stop_loss,
                "target_2": p.target_2,
                "reward_risk_ratio": p.reward_risk_ratio,
                "status": p.status.value
            }
            for p in proposals
        ]
    
    # ========================================================================
    # Market Data Endpoints
    # ========================================================================
    
    async def _get_market_data(self, api_key: str, symbol: str) -> MarketDataResponse:
        """Get market data for symbol"""
        price_service = self.bot_data.get('price_service')
        if not price_service:
            raise HTTPException(status_code=500, detail="Price service not available")
        
        data = await price_service.get_price(symbol)
        if not data:
            raise HTTPException(status_code=404, detail=f"Data not found for {symbol}")
        
        return MarketDataResponse(
            symbol=symbol,
            price=data['price'],
            change_24h=data.get('change_24h', 0),
            volume_24h=data.get('volume_24h', 0),
            market_cap=data.get('market_cap')
        )
    
    async def _get_top_coins(self, api_key: str, limit: int):
        """Get top coins by market cap"""
        market_service = self.bot_data.get('market_service')
        if not market_service:
            raise HTTPException(status_code=500, detail="Market service not available")
        
        data = await market_service.get_top_coins(limit)
        return data
    
    # ========================================================================
    # Analysis Endpoints
    # ========================================================================
    
    async def _analyze_symbol(
        self,
        api_key: str,
        request: AnalysisRequest
    ) -> AnalysisResponse:
        """Analyze symbol"""
        ta_service = self.bot_data.get('ta_service')
        price_service = self.bot_data.get('price_service')
        
        if not ta_service or not price_service:
            raise HTTPException(status_code=500, detail="Services not available")
        
        # Get price
        price_data = await price_service.get_price(request.symbol)
        if not price_data:
            raise HTTPException(status_code=404, detail=f"Price not found for {request.symbol}")
        
        # Get TA
        ta = await ta_service.analyze(request.symbol, request.timeframe)
        if not ta:
            raise HTTPException(status_code=404, detail=f"Analysis not available for {request.symbol}")
        
        # Generate recommendation
        rsi = ta.get('rsi', 50)
        trend = ta.get('trend', 'neutral')
        
        if trend == 'up' and rsi < 70:
            recommendation = "BUY"
        elif trend == 'down' and rsi > 30:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"
        
        return AnalysisResponse(
            symbol=request.symbol,
            timeframe=request.timeframe,
            price=price_data['price'],
            rsi=rsi,
            trend=trend,
            support=ta.get('support', price_data['price'] * 0.95),
            resistance=ta.get('resistance', price_data['price'] * 1.05),
            recommendation=recommendation
        )
    
    # ========================================================================
    # TradingView Webhook
    # ========================================================================
    
    async def _handle_tradingview_webhook(
        self,
        webhook: TradingViewWebhook,
        secret: Optional[str]
    ):
        """Handle TradingView webhook"""
        # Verify webhook secret
        expected_secret = self.config.get('TRADINGVIEW_WEBHOOK_SECRET')
        if expected_secret and secret != expected_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        
        # Log webhook
        print(f"TradingView Webhook: {webhook.action} {webhook.symbol} @ ${webhook.price}")
        
        # Execute action
        db = self.bot_data.get('db')
        telegram_bot = self.bot_data.get('telegram_bot')
        user_id = self.config.get('ALLOWED_USER_ID')
        
        if webhook.action == "buy":
            # Add position
            if db:
                await db.add_position(user_id, webhook.symbol, 0, webhook.price)
            
            # Notify user
            if telegram_bot:
                message = f"🔔 TradingView Alert\n\n"
                message += f"Action: BUY {webhook.symbol}\n"
                message += f"Price: ${webhook.price:,.2f}\n"
                if webhook.strategy:
                    message += f"Strategy: {webhook.strategy}\n"
                if webhook.message:
                    message += f"\n{webhook.message}"
                
                await telegram_bot.send_message(chat_id=user_id, text=message)
        
        elif webhook.action == "sell":
            # Update position
            if telegram_bot:
                message = f"🔔 TradingView Alert\n\n"
                message += f"Action: SELL {webhook.symbol}\n"
                message += f"Price: ${webhook.price:,.2f}\n"
                if webhook.strategy:
                    message += f"Strategy: {webhook.strategy}\n"
                if webhook.message:
                    message += f"\n{webhook.message}"
                
                await telegram_bot.send_message(chat_id=user_id, text=message)
        
        return {
            "success": True,
            "action": webhook.action,
            "symbol": webhook.symbol,
            "price": webhook.price
        }
    
    # ========================================================================
    # Journal Endpoints
    # ========================================================================
    
    async def _add_journal_entry(
        self,
        api_key: str,
        entry: str,
        symbol: Optional[str]
    ):
        """Add journal entry"""
        db = self.bot_data.get('db')
        if not db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        user_id = self.api_keys[api_key]['user_id']
        
        await db.add_journal_entry(user_id, entry, symbol)
        
        return {"success": True, "message": "Journal entry added"}
    
    async def _get_journal(self, api_key: str, days: int):
        """Get journal entries"""
        db = self.bot_data.get('db')
        if not db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        user_id = self.api_keys[api_key]['user_id']
        entries = await db.get_journal_entries(user_id, days)
        
        return entries


def create_app(bot_data: Dict, config: Dict) -> FastAPI:
    """Create FastAPI application"""
    server = APIServer(bot_data, config)
    return server.app


async def start_api_server(bot_data: Dict, config: Dict, port: int = 8000):
    """Start API server"""
    import uvicorn
    
    app = create_app(bot_data, config)
    
    config_uvicorn = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    
    server = uvicorn.Server(config_uvicorn)
    await server.serve()
