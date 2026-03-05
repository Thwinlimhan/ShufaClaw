"""
Multi-Analyst Debate System - Level 30

Three AI personas debate a trading decision from different perspectives:
- BULL (Momentum Seeker): Aggressive, finds bullish signals
- BEAR (Risk Manager): Conservative, finds bearish signals  
- QUANT (Data Scientist): Numbers-only, statistical edge

The debate provides multiple viewpoints to avoid confirmation bias.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DebateSystem:
    """Orchestrates three-analyst debate on trading decisions"""
    
    def __init__(self, ai_client, market_service, technical_service, 
                 news_service, onchain_service):
        self.ai = ai_client
        self.market = market_service
        self.technical = technical_service
        self.news = news_service
        self.onchain = onchain_service
        
        # Analyst personas
        self.BULL_PROMPT = """You are an aggressive momentum trader.
Your job: Find the STRONGEST possible bull case.
Look for: Strong uptrends, high-volume breakouts, RSI divergences, 
positive news, institutional buying, technical breakouts.
Present your case in exactly 100 words. Be decisive and confident."""

        self.BEAR_PROMPT = """You are a conservative risk manager.
Your job: Find the STRONGEST possible bear case.
Look for: Overbought conditions, resistance levels, macro headwinds,
distribution patterns, negative news, technical warnings.
Present your case in exactly 100 words. Be cautious and protective."""

        self.QUANT_PROMPT = """You are a quantitative analyst who only trusts numbers.
Your job: Calculate what the DATA shows.
Analyze: Historical win rates, expected value, statistical edge,
probability distributions, correlation patterns.
Present findings with confidence levels in exactly 100 words."""

        self.MODERATOR_PROMPT = """You are a neutral moderator synthesizing a debate.
Three analysts presented their cases. Your job:
1. Where do they AGREE? (high confidence areas)
2. Where do they DISAGREE? (uncertainty areas)
3. What's the MOST LIKELY outcome?
4. What's the RECOMMENDED action with clear reasoning?

Be decisive but acknowledge uncertainty. 150 words max."""

    async def run_debate(self, symbol: str, question: Optional[str] = None) -> Dict:
        """
        Run full three-analyst debate
        
        Args:
            symbol: Coin to analyze (e.g., 'BTC')
            question: Optional specific question (e.g., "should I sell at $100k?")
            
        Returns:
            Dict with all analyst positions and synthesis
        """
        try:
            logger.info(f"Starting debate for {symbol}")
            
            # Gather all data
            data = await self._gather_debate_data(symbol)
            
            # Format the question
            if question:
                debate_topic = f"{symbol}: {question}"
            else:
                debate_topic = f"Should I buy, sell, or hold {symbol} right now?"
            
            # Round 1: Opening statements (parallel)
            bull_case = await self._get_analyst_view(
                "BULL", self.BULL_PROMPT, debate_topic, data
            )
            
            bear_case = await self._get_analyst_view(
                "BEAR", self.BEAR_PROMPT, debate_topic, data
            )
            
            quant_case = await self._get_analyst_view(
                "QUANT", self.QUANT_PROMPT, debate_topic, data
            )
            
            # Round 2: Rebuttals
            bull_rebuttal = await self._get_rebuttal(
                "BULL", bull_case, bear_case, data
            )
            
            bear_rebuttal = await self._get_rebuttal(
                "BEAR", bear_case, bull_case, data
            )
            
            quant_evaluation = await self._get_quant_evaluation(
                quant_case, bull_case, bear_case, data
            )
            
            # Round 3: Moderator synthesis
            synthesis = await self._synthesize_debate(
                debate_topic, 
                bull_case, bear_case, quant_case,
                bull_rebuttal, bear_rebuttal, quant_evaluation,
                data
            )
            
            result = {
                'symbol': symbol,
                'question': question or "General analysis",
                'timestamp': datetime.now().isoformat(),
                'data_summary': self._format_data_summary(data),
                'round_1': {
                    'bull': bull_case,
                    'bear': bear_case,
                    'quant': quant_case
                },
                'round_2': {
                    'bull_rebuttal': bull_rebuttal,
                    'bear_rebuttal': bear_rebuttal,
                    'quant_evaluation': quant_evaluation
                },
                'synthesis': synthesis
            }
            
            logger.info(f"Debate completed for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Debate failed for {symbol}: {e}")
            raise

    async def quick_debate(self, symbol: str, question: Optional[str] = None) -> Dict:
        """
        Quick debate: Opening statements + synthesis only (faster)
        
        Args:
            symbol: Coin to analyze
            question: Optional specific question
            
        Returns:
            Dict with opening statements and synthesis
        """
        try:
            logger.info(f"Starting quick debate for {symbol}")
            
            # Gather data
            data = await self._gather_debate_data(symbol)
            
            # Format question
            if question:
                debate_topic = f"{symbol}: {question}"
            else:
                debate_topic = f"Should I buy, sell, or hold {symbol} right now?"
            
            # Opening statements only
            bull_case = await self._get_analyst_view(
                "BULL", self.BULL_PROMPT, debate_topic, data
            )
            
            bear_case = await self._get_analyst_view(
                "BEAR", self.BEAR_PROMPT, debate_topic, data
            )
            
            quant_case = await self._get_analyst_view(
                "QUANT", self.QUANT_PROMPT, debate_topic, data
            )
            
            # Direct synthesis
            synthesis = await self._synthesize_debate(
                debate_topic,
                bull_case, bear_case, quant_case,
                None, None, None,  # No rebuttals
                data
            )
            
            result = {
                'symbol': symbol,
                'question': question or "General analysis",
                'timestamp': datetime.now().isoformat(),
                'mode': 'quick',
                'data_summary': self._format_data_summary(data),
                'analysts': {
                    'bull': bull_case,
                    'bear': bear_case,
                    'quant': quant_case
                },
                'synthesis': synthesis
            }
            
            logger.info(f"Quick debate completed for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Quick debate failed for {symbol}: {e}")
            raise

    async def _gather_debate_data(self, symbol: str) -> Dict:
        """Gather all relevant data for the debate"""
        data = {}
        
        try:
            # Price data
            price_data = await self.market.get_price(symbol)
            data['price'] = price_data
            
            # Technical analysis (multiple timeframes)
            try:
                ta_1h = await self.technical.analyze(symbol, '1h')
                ta_4h = await self.technical.analyze(symbol, '4h')
                ta_1d = await self.technical.analyze(symbol, '1d')
                data['technical'] = {
                    '1h': ta_1h,
                    '4h': ta_4h,
                    '1d': ta_1d
                }
            except Exception as e:
                logger.warning(f"TA failed: {e}")
                data['technical'] = None
            
            # Market overview
            try:
                market_overview = await self.market.get_market_overview()
                data['market'] = market_overview
            except Exception as e:
                logger.warning(f"Market overview failed: {e}")
                data['market'] = None
            
            # News sentiment
            try:
                news = await self.news.get_news_for_symbol(symbol, limit=5)
                data['news'] = news
            except Exception as e:
                logger.warning(f"News failed: {e}")
                data['news'] = None
            
            # On-chain (if ETH or BTC)
            if symbol in ['BTC', 'ETH']:
                try:
                    onchain = await self.onchain.get_summary()
                    data['onchain'] = onchain
                except Exception as e:
                    logger.warning(f"On-chain failed: {e}")
                    data['onchain'] = None
            
            return data
            
        except Exception as e:
            logger.error(f"Data gathering failed: {e}")
            return data

    async def _get_analyst_view(self, analyst: str, prompt: str, 
                                topic: str, data: Dict) -> str:
        """Get one analyst's opening statement"""
        try:
            # Build context from data
            context = self._build_data_context(data)
            
            full_prompt = f"""{prompt}

TOPIC: {topic}

DATA AVAILABLE:
{context}

Your analysis (exactly 100 words):"""

            response = await self.ai.get_completion(full_prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"{analyst} analysis failed: {e}")
            return f"[{analyst} analysis unavailable]"

    async def _get_rebuttal(self, analyst: str, own_case: str, 
                           opposing_case: str, data: Dict) -> str:
        """Get analyst's rebuttal to opposing view"""
        try:
            if analyst == "BULL":
                prompt = f"""You are the BULL analyst. The BEAR analyst said:
"{opposing_case}"

Your rebuttal (50 words): Why is the bear case wrong or overstated?"""
            else:  # BEAR
                prompt = f"""You are the BEAR analyst. The BULL analyst said:
"{own_case}"

Your rebuttal (50 words): Why is the bull case wrong or overstated?"""
            
            response = await self.ai.get_completion(prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"{analyst} rebuttal failed: {e}")
            return f"[{analyst} rebuttal unavailable]"

    async def _get_quant_evaluation(self, quant_case: str, bull_case: str,
                                   bear_case: str, data: Dict) -> str:
        """Get quant's evaluation of both cases"""
        try:
            prompt = f"""You are the QUANT analyst. You've heard:

BULL: {bull_case}
BEAR: {bear_case}

Your evaluation (50 words): Which case does the DATA support more strongly?
Give a probability estimate."""

            response = await self.ai.get_completion(prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Quant evaluation failed: {e}")
            return "[Quant evaluation unavailable]"

    async def _synthesize_debate(self, topic: str, bull: str, bear: str,
                                quant: str, bull_reb: Optional[str],
                                bear_reb: Optional[str], quant_eval: Optional[str],
                                data: Dict) -> str:
        """Moderator synthesizes all viewpoints"""
        try:
            debate_summary = f"""TOPIC: {topic}

BULL ANALYST: {bull}
BEAR ANALYST: {bear}
QUANT ANALYST: {quant}"""

            if bull_reb and bear_reb and quant_eval:
                debate_summary += f"""

BULL REBUTTAL: {bull_reb}
BEAR REBUTTAL: {bear_reb}
QUANT EVALUATION: {quant_eval}"""

            prompt = f"""{self.MODERATOR_PROMPT}

{debate_summary}

Your synthesis (150 words max):"""

            response = await self.ai.get_completion(prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return "[Synthesis unavailable]"

    def _build_data_context(self, data: Dict) -> str:
        """Format data into readable context"""
        context_parts = []
        
        # Price
        if data.get('price'):
            p = data['price']
            context_parts.append(
                f"Price: ${p.get('price', 'N/A')} "
                f"({p.get('change_24h', 'N/A')}% 24h)"
            )
        
        # Technical
        if data.get('technical'):
            ta = data['technical'].get('4h', {})
            if ta:
                context_parts.append(
                    f"RSI(4h): {ta.get('rsi', 'N/A')}, "
                    f"Trend: {ta.get('trend', 'N/A')}"
                )
        
        # Market
        if data.get('market'):
            m = data['market']
            context_parts.append(
                f"Market: {m.get('sentiment', 'N/A')}, "
                f"F&G: {m.get('fear_greed', 'N/A')}"
            )
        
        # News
        if data.get('news'):
            news_count = len(data['news'])
            context_parts.append(f"Recent news: {news_count} articles")
        
        return "\n".join(context_parts) if context_parts else "Limited data available"

    def _format_data_summary(self, data: Dict) -> str:
        """Format data summary for result"""
        summary = []
        
        if data.get('price'):
            p = data['price']
            summary.append(f"Price: ${p.get('price', 'N/A')}")
        
        if data.get('technical'):
            summary.append("Technical: Multi-timeframe analysis included")
        
        if data.get('market'):
            summary.append("Market: Overview included")
        
        if data.get('news'):
            summary.append(f"News: {len(data['news'])} articles analyzed")
        
        return " | ".join(summary) if summary else "Limited data"

    def format_debate_message(self, result: Dict, mode: str = 'full') -> str:
        """
        Format debate result for Telegram
        
        Args:
            result: Debate result dict
            mode: 'full' or 'quick'
            
        Returns:
            Formatted message string
        """
        symbol = result['symbol']
        question = result['question']
        
        msg = f"🎭 **ANALYST DEBATE: {symbol}**\n\n"
        msg += f"**Question:** {question}\n"
        msg += f"**Data:** {result['data_summary']}\n\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if mode == 'full':
            # Round 1
            msg += "**📊 ROUND 1: OPENING STATEMENTS**\n\n"
            msg += f"🐂 **BULL (Momentum Seeker):**\n{result['round_1']['bull']}\n\n"
            msg += f"🐻 **BEAR (Risk Manager):**\n{result['round_1']['bear']}\n\n"
            msg += f"🔢 **QUANT (Data Scientist):**\n{result['round_1']['quant']}\n\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            # Round 2
            msg += "**⚔️ ROUND 2: REBUTTALS**\n\n"
            msg += f"🐂 **BULL responds:**\n{result['round_2']['bull_rebuttal']}\n\n"
            msg += f"🐻 **BEAR responds:**\n{result['round_2']['bear_rebuttal']}\n\n"
            msg += f"🔢 **QUANT evaluates:**\n{result['round_2']['quant_evaluation']}\n\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        else:
            # Quick mode - just opening statements
            msg += "**📊 ANALYST VIEWS**\n\n"
            msg += f"🐂 **BULL:**\n{result['analysts']['bull']}\n\n"
            msg += f"🐻 **BEAR:**\n{result['analysts']['bear']}\n\n"
            msg += f"🔢 **QUANT:**\n{result['analysts']['quant']}\n\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Synthesis
        msg += "**⚖️ MODERATOR SYNTHESIS**\n\n"
        msg += result['synthesis']
        
        return msg
