"""
AI 칼럼 생성 서비스: 핵심 종목별 뉴스 칼럼 생성
- Pass 1: 직접 뉴스 검색
- Pass 2: 상관 종목의 간접 뉴스 검색
- 크롤링 → TextRank 요약 → ChatGPT 칼럼 생성
"""

import asyncio
import structlog
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from app.config import get_settings
from app.services.polygon_service import PolygonService
from app.services.correlation_service import CorrelationService
from app.services.news.text_processor import TextProcessor
from app.services.news.article_scraper import ArticleScraper
from app.services.news.chatgpt_client import ChatGPTClient
from app.models.column_schema import Column
from app.core_stock import CORE_STOCK_ASSETS

logger = structlog.get_logger()


class NewsColumnService:
    """
    핵심 종목별 AI 칼럼 생성 서비스
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.polygon_service = PolygonService()
        self.correlation_service = None
        self.text_processor = TextProcessor()
        self.article_scraper = ArticleScraper()
        self.chatgpt_client = ChatGPTClient()
    
    async def initialize(self, correlation_service: CorrelationService):
        """서비스 초기화"""
        self.correlation_service = correlation_service
    
    async def generate_all_columns(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        핵심 종목(169개)에 대해 AI 칼럼 생성
        
        Args:
            limit: 처리할 최대 종목 수 (None이면 전체)
        
        Returns:
            {
                "success": True,
                "total_tickers": 169,
                "pass1_success": 100,
                "pass2_success": 30,
                "failed": 20
            }
        """
        try:
            # CORE_STOCK_ASSETS (169개) 대상으로 칼럼 생성
            target_tickers = CORE_STOCK_ASSETS.copy()
            
            # limit이 지정되면 제한
            if limit and limit > 0:
                target_tickers = target_tickers[:limit]
            
            logger.info("news_column_generation_started", total_tickers=len(target_tickers))
            
            # Pass 1: 직접 뉴스 검색
            pass1_results = await self._pass1_direct_news(target_tickers)
            
            # Pass 2: 간접 뉴스 검색 (Pass 1에서 실패한 종목만)
            pass2_results = await self._pass2_indirect_news(pass1_results["failed_tickers"])
            
            total_success = pass1_results["success_count"] + pass2_results["success_count"]
            total_failed = len(pass2_results["failed_tickers"])
            
            logger.info(
                "news_column_generation_completed",
                total_tickers=len(target_tickers),
                pass1_success=pass1_results["success_count"],
                pass2_success=pass2_results["success_count"],
                total_success=total_success,
                total_failed=total_failed
            )
            
            return {
                "success": True,
                "total_tickers": len(target_tickers),
                "pass1_success": pass1_results["success_count"],
                "pass2_success": pass2_results["success_count"],
                "total_success": total_success,
                "failed": total_failed,
                "results": pass1_results.get("success_results", [])
            }
            
        except Exception as e:
            logger.error(
                "news_column_generation_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def generate_columns_for_tickers(
        self,
        tickers: List[str],
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        특정 종목 리스트에 대해 AI 칼럼 생성
        
        Args:
            tickers: 처리할 티커 리스트
            limit: 처리할 최대 종목 수 (None이면 전체)
        """
        if not tickers:
            return {
                "success": False,
                "message": "티커 리스트가 비어있습니다.",
                "total_tickers": 0,
                "pass1_success": 0,
                "pass2_success": 0,
                "total_success": 0,
                "failed": 0
            }
        
        # limit이 지정되면 제한
        if limit and limit > 0:
            tickers = tickers[:limit]
        
        logger.info("news_column_generation_started", total_tickers=len(tickers), source="tickers_param")
        
        # Pass 1: 직접 뉴스 검색
        pass1_results = await self._pass1_direct_news(tickers)
        
        # Pass 2: 간접 뉴스 검색 (Pass 1에서 실패한 종목만)
        pass2_results = await self._pass2_indirect_news(pass1_results["failed_tickers"])
        
        total_success = pass1_results["success_count"] + pass2_results["success_count"]
        total_failed = len(pass2_results["failed_tickers"])
        
        # Pass 1과 Pass 2 결과 합치기
        all_results = pass1_results.get("success_results", []) + pass2_results.get("success_results", [])
        
        return {
            "success": True,
            "total_tickers": len(tickers),
            "pass1_success": pass1_results["success_count"],
            "pass2_success": pass2_results["success_count"],
            "total_success": total_success,
            "failed": total_failed,
            "results": all_results
        }
    
    async def _pass1_direct_news(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Pass 1: 직접 뉴스 검색
        각 종목에 대해 Massive.com News API로 직접 뉴스 검색
        
        Args:
            tickers: 처리할 티커 리스트
        """
        success_count = 0
        failed_tickers = []
        success_results = []
        
        # 최근 1일 이내 뉴스만 검색 ("오늘의 뉴스")
        from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        for ticker in tickers:
            try:
                # 뉴스 검색
                news_list = await self.polygon_service.get_news(
                    ticker=ticker,
                    limit=5,
                    published_utc=from_date
                )
                
                if not news_list:
                    failed_tickers.append(ticker)
                    logger.debug("pass1_no_news", ticker=ticker)
                    continue
                
                # 관련성 높은 기사 선택 (우선순위 기반)
                news_article = None
                
                # 1순위: tickers[0]이 검색 종목인 기사 (주 종목)
                for article in news_list:
                    article_tickers = article.get("tickers", [])
                    if article_tickers and article_tickers[0].upper() == ticker.upper():
                        news_article = article
                        logger.debug(
                            "pass1_primary_ticker_found",
                            ticker=ticker,
                            title=article.get("title", "")[:50]
                        )
                        break
                
                # 2순위: tickers 1~2번째에 검색 종목이 있는 기사
                if not news_article:
                    ticker_upper = ticker.upper()
                    for article in news_list:
                        article_tickers = article.get("tickers", [])
                        if len(article_tickers) >= 2:
                            # 대소문자 구분 없이 비교하기 위해 정규화
                            article_tickers_upper = [t.upper() for t in article_tickers]
                            if ticker_upper in article_tickers_upper[:2]:
                                news_article = article
                                # case-insensitive index lookup
                                position = next((idx + 1 for idx, t in enumerate(article_tickers_upper) if t == ticker_upper), 0)
                                logger.debug(
                                    "pass1_secondary_ticker_found",
                                    ticker=ticker,
                                    position=position,
                                    title=article.get("title", "")[:50]
                                )
                                break
                
                # 관련성 낮은 기사만 있으면 Pass 1 실패
                if not news_article:
                    failed_tickers.append(ticker)
                    logger.debug(
                        "pass1_no_relevant_article",
                        ticker=ticker,
                        message="검색 종목이 주요 종목이 아닌 기사만 존재"
                    )
                    continue
                
                # AI 칼럼 생성
                column_data = await self._generate_column_from_news(
                    ticker=ticker,
                    news_article=news_article,
                    source_ticker=ticker
                )
                
                if column_data:
                    success_count += 1
                    success_results.append(column_data)  # 전체 칼럼 데이터 추가
                    logger.info("pass1_success", ticker=ticker, title=column_data.get("title", "")[:50])
                else:
                    failed_tickers.append(ticker)
                    logger.warning("pass1_column_generation_failed", ticker=ticker)
                
                # Rate Limit 회피
                await asyncio.sleep(0.5)
                
            except Exception as e:
                failed_tickers.append(ticker)
                logger.warning(
                    "pass1_error",
                    ticker=ticker,
                    error=str(e)
                )
        
        return {
            "success_count": success_count,
            "failed_tickers": failed_tickers,
            "success_results": success_results
        }
    
    async def _pass2_indirect_news(self, failed_tickers: List[str]) -> Dict[str, Any]:
        """
        Pass 2: 간접 뉴스 검색
        상관 종목의 뉴스를 사용하여 칼럼 생성
        """
        if not failed_tickers:
            return {"success_count": 0, "failed_tickers": [], "success_results": []}
        
        success_count = 0
        still_failed = []
        success_results = []
        
        for ticker in failed_tickers:
            try:
                # 상관 종목 조회 (상위 20개)
                related_tickers = await self.correlation_service.get_related_tickers(
                    ticker=ticker,
                    limit=20
                )
                
                if not related_tickers:
                    still_failed.append(ticker)
                    logger.debug("pass2_no_related_tickers", ticker=ticker)
                    continue
                
                # 상관 종목의 뉴스 검색
                source_ticker = None
                news_article = None
                
                for related in related_tickers:
                    related_ticker = related["ticker"]
                    
                    # 해당 종목의 뉴스 검색
                    news_list = await self.polygon_service.get_news(
                        ticker=related_ticker,
                        limit=3
                    )
                    
                    if news_list:
                        source_ticker = related_ticker
                        news_article = news_list[0]
                        break
                
                if news_article:
                    # AI 칼럼 생성
                    column_data = await self._generate_column_from_news(
                        ticker=ticker,
                        news_article=news_article,
                        source_ticker=source_ticker
                    )
                    
                    if column_data:
                        success_count += 1
                        success_results.append(column_data)  # 전체 칼럼 데이터 추가
                        logger.info(
                            "pass2_success",
                            ticker=ticker,
                            source_ticker=source_ticker,
                            title=column_data.get("title", "")[:50]
                        )
                    else:
                        still_failed.append(ticker)
                else:
                    still_failed.append(ticker)
                
                # Rate Limit 회피
                await asyncio.sleep(0.5)
                
            except Exception as e:
                still_failed.append(ticker)
                logger.warning(
                    "pass2_error",
                    ticker=ticker,
                    error=str(e)
                )
        
        return {
            "success_count": success_count,
            "failed_tickers": still_failed,
            "success_results": success_results
        }
    
    async def _generate_column_from_news(
        self,
        ticker: str,
        news_article: Dict[str, Any],
        source_ticker: str
    ) -> Optional[Dict[str, Any]]:
        """
        뉴스 기사로부터 AI 칼럼 생성
        
        Args:
            ticker: 칼럼을 생성할 종목
            news_article: 뉴스 기사 데이터
            source_ticker: 실제 뉴스가 나온 종목
        
        Returns:
            {
                "content": "...",
                "image_url": "...",
                "source_url": "...",
                "source_ticker": "..."
            }
        """
        try:
            article_url = news_article.get("article_url")
            image_url = news_article.get("image_url")
            title = news_article.get("title", "")
            description = news_article.get("description", "")
            published_at = news_article.get("published_utc", "")
            publisher = news_article.get("publisher", {}).get("name", "Unknown")
            
            if not article_url:
                logger.warning("news_no_article_url", ticker=ticker)
                return None
            
            # 1. 기사 본문 크롤링
            article_text = await self.article_scraper.scrape_article(article_url)
            
            # 크롤링 결과 검증: 너무 짧거나 메뉴 텍스트만 있는 경우
            if not article_text or len(article_text) < 200:
                # 크롤링 실패 또는 불충분 → description 사용
                article_text = description or title
                logger.warning(
                    "scraping_insufficient_using_description",
                    ticker=ticker,
                    scraped_length=len(article_text) if article_text else 0
                )
            
            # 2. 텍스트 전처리 (메타 정보 제거)
            article_text = self.text_processor.clean_article_text(article_text)
            
            # 3. TextRank로 핵심 문장 추출
            key_sentences = self.text_processor.extract_key_sentences(article_text, ratio=0.35)
            
            if not key_sentences:
                key_sentences = article_text[:800]
            
            # 4. ChatGPT로 칼럼 생성
            column_content = await self.chatgpt_client.generate_column(
                ticker=ticker,
                news_title=title,
                key_sentences=key_sentences
            )
            
            if not column_content:
                logger.warning("chatgpt_generation_failed", ticker=ticker)
                return None
            
            # 5. Column 스키마로 반환
            column = Column(
                ticker=ticker,
                title=column_content.title,
                subtitle=column_content.subtitle,
                sections=column_content.sections,
                image_url=image_url,
                source_title=title,
                source_publisher=publisher,
                source_url=article_url,
                source_published_at=published_at,
                generated_at=datetime.utcnow().isoformat(),
                source_ticker=source_ticker if source_ticker != ticker else None
            )
            
            return column.model_dump()
            
        except Exception as e:
            logger.warning(
                "column_generation_error",
                ticker=ticker,
                error=str(e)
            )
            return None

