import asyncio
import httpx
import structlog
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.config import get_settings

# Massive.com API 호출 서비스: Top 3000 유동성 종목 리스트 조회
logger = structlog.get_logger()


class MassiveService:
    def __init__(self):
        self.settings = get_settings()
        # 모든 엔드포인트는 api.massive.com에서 정상 동작
        self.base_url = "https://api.massive.com"
        self.api_key = self.settings.massive_api_key
    
    # Top 티커 리스트 조회
    async def get_top_tickers(
        self,
        limit: int = 1000,
        market: str = "stocks",
        active: bool = True,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            params = {
                "apiKey": self.api_key,
                "market": market,
                "active": "true" if active else "false",
                "limit": str(min(limit, 1000)) 
            }
            
            if cursor:
                params["cursor"] = cursor
            
            url = f"{self.base_url}/v3/reference/tickers"
            
            logger.info(
                "massive_api_call",
                endpoint="/v3/reference/tickers",
                limit=limit,
                cursor=cursor is not None
            )
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                logger.info(
                    "massive_api_call_success",
                    result_count=len(data.get("results", [])),
                    has_next=bool(data.get("next_url"))
                )
                
                return data
                
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500] if e.response.text else "No error detail"
            logger.error(
                "massive_api_call_failed",
                status_code=e.response.status_code,
                response=error_detail,
                url=url,
                params=params
            )
            raise Exception(f"Massive API 호출 실패: {e.response.status_code} - {error_detail}")
        except Exception as e:
            logger.error(
                "massive_api_call_error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise Exception(f"Massive API 호출 중 오류: {str(e)}")
    

    # 개별 티커의 상세 정보 조회 (심볼 이용해 market_cap 등 반환)
    async def get_ticker_details(self, ticker: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/v3/reference/tickers/{ticker}"
            params = {"apiKey": self.api_key}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                result = data.get("results")
                if result and result.get("market_cap"):
                    return result
                return None
                
        except httpx.HTTPStatusError as e:
            logger.warning(
                "ticker_details_failed",
                ticker=ticker,
                status_code=e.response.status_code
            )
            return None
        except Exception as e:
            logger.warning(
                "ticker_details_error",
                ticker=ticker,
                error=str(e)
            )
            return None
    
    # 시가총액 기준 상위 3000개 티커 조회
    async def get_top_3000_tickers(self) -> List[Dict[str, Any]]:
        import asyncio
        
        # 1. 티커 목록 수집: 8000개 (market_cap 비율 고려, 3000개 확보 목표)
        all_tickers = []
        cursor = None
        page = 1
        target_collect = 8000  
        
        logger.info("massive_starting_ticker_collection", target=target_collect)
        
        while len(all_tickers) < target_collect:
            limit = min(1000, target_collect - len(all_tickers))
            data = await self.get_top_tickers(limit=limit, cursor=cursor)
            
            results = data.get("results", [])
            all_tickers.extend(results)
            
            next_url = data.get("next_url")
            if not next_url or len(results) == 0:
                break
            
            cursor = self._extract_cursor_from_url(next_url)
            page += 1
            await asyncio.sleep(0.1)
        
        logger.info(
            "massive_ticker_list_collected",
            total_count=len(all_tickers)
        )
        
        # 2. 각 티커의 market_cap 정보 순차적으로 조회 
        tickers_with_market_cap = []
        batch_size = 10  
        processed_tickers = set()
        
        for i in range(0, len(all_tickers), batch_size):
            batch = all_tickers[i:i + batch_size]
            
            # 중복 제거
            batch_to_process = [
                t for t in batch 
                if t.get("ticker") and t.get("ticker") not in processed_tickers
            ]
            
            if not batch_to_process:
                continue
            
            logger.info(
                "massive_market_cap_batch",
                batch_num=(i // batch_size) + 1,
                total_batches=(len(all_tickers) + batch_size - 1) // batch_size,
                current_with_market_cap=len(tickers_with_market_cap),
                target=3000
            )
            
            # 배치 병렬 처리
            tasks = [
                self.get_ticker_details(ticker.get("ticker", "")) 
                for ticker in batch_to_process
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for ticker_data, result in zip(batch_to_process, results):
                ticker = ticker_data.get("ticker", "")
                processed_tickers.add(ticker)
                
                if isinstance(result, dict) and result.get("market_cap"):
                    tickers_with_market_cap.append(result)
                    
                    # 이미 3000개 모였으면 중단
                    if len(tickers_with_market_cap) >= 3000:
                        break
            
            # 3000개 모였으면 종료
            if len(tickers_with_market_cap) >= 3000:
                break
            
           
            await asyncio.sleep(0.5)
        
        # 3. market_cap 기준 내림차순 정렬
        tickers_with_market_cap.sort(
            key=lambda x: x.get("market_cap", 0) or 0,
            reverse=True
        )
        
        logger.info(
            "massive_top_3000_completed",
            total_collected=len(all_tickers),
            with_market_cap=len(tickers_with_market_cap),
            final_count=min(3000, len(tickers_with_market_cap)),
            method="ticker_details_with_market_cap"
        )
        
        # 4. 상위 3000개 반환
        return tickers_with_market_cap[:3000]  
    
    # 티커의 과거 가격 데이터 조회 (Aggregates API)
    async def get_aggregates(
        self,
        ticker: str,
        days: int = 90,
        multiplier: int = 1,
        timespan: str = "day"
    ) -> Optional[List[Dict[str, Any]]]:
        try:
            # 날짜 계산: 오늘부터 days일 전까지
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            # Massive API 형식: YYYY-MM-DD
            from_str = from_date.strftime("%Y-%m-%d")
            to_str = to_date.strftime("%Y-%m-%d")
            
            # httpx가 자동으로 URL 인코딩 처리
            url = f"{self.base_url}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_str}/{to_str}"
            
            params = {"apiKey": self.api_key}
            
            # 429 Rate Limit 에러는 재시도하지 않고 즉시 실패 처리
            # (correlation_service에서 delay로 Rate Limit 회피)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                
                # 429 Rate Limit 에러 처리 (재시도 없이 즉시 실패)
                if response.status_code == 429:
                    logger.warning(
                        "aggregates_rate_limit",
                        ticker=ticker,
                        message="Rate limit exceeded, skipping"
                    )
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if not results:
                    logger.warning(
                        "aggregates_no_data",
                        ticker=ticker,
                        from_date=from_str,
                        to_date=to_str
                    )
                    return None
                
                # 데이터 정리: timestamp를 날짜 문자열로 추가
                formatted_results = []
                for item in results:
                    timestamp_ms = item.get("t", 0)  # t = timestamp (밀리초)
                    if timestamp_ms:
                        date_obj = datetime.fromtimestamp(timestamp_ms / 1000)
                        date_str = date_obj.strftime("%Y-%m-%d")
                    else:
                        date_str = None
                    
                    formatted_results.append({
                        "timestamp": timestamp_ms,
                        "date": date_str,
                        "open": item.get("o"),      # open
                        "high": item.get("h"),      # high
                        "low": item.get("l"),       # low
                        "close": item.get("c"),     # close
                        "volume": item.get("v"),    # volume
                    })
                
                logger.debug(
                    "aggregates_fetched",
                    ticker=ticker,
                    count=len(formatted_results),
                    from_date=from_str,
                    to_date=to_str
                )
                
                return formatted_results
                
        except httpx.HTTPStatusError as e:
            logger.warning(
                "aggregates_api_failed",
                ticker=ticker,
                status_code=e.response.status_code,
                response=e.response.text[:200] if e.response.text else ""
            )
            return None
        except Exception as e:
            logger.warning(
                "aggregates_api_error",
                ticker=ticker,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    # News API로 특정 종목의 뉴스 조회
    async def get_news(
        self,
        ticker: str,
        limit: int = 10,
        published_utc: Optional[str] = None,
        order: str = "desc",
        sort: str = "published_utc"
    ) -> Optional[List[Dict[str, Any]]]:
        try:
            url = f"{self.base_url}/v2/reference/news"
            
            params = {
                "ticker": ticker.upper(),
                "limit": min(limit, 1000),
                "order": order,
                "sort": sort
            }
            
            if published_utc:
                # Massive.com API는 "published_utc.gte" 형식 사용
                # 예: "2025-11-04" → 2025-11-04 이후 뉴스만
                params["published_utc.gte"] = published_utc
            
            # API 키는 헤더에 포함 
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 429:
                    logger.warning(
                        "news_api_rate_limit",
                        ticker=ticker,
                        message="Rate limit exceeded, skipping"
                    )
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if not results:
                    logger.debug(
                        "news_no_data",
                        ticker=ticker
                    )
                    return None
                
                logger.debug(
                    "news_fetched",
                    ticker=ticker,
                    count=len(results)
                )
                
                return results
                
        except httpx.HTTPStatusError as e:
            logger.warning(
                "news_api_failed",
                ticker=ticker,
                status_code=e.response.status_code,
                response=e.response.text[:200] if e.response.text else ""
            )
            return None
        except Exception as e:
            logger.warning(
                "news_api_error",
                ticker=ticker,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    # 리포트용 뉴스 조회: 특정 기간(start_date ~ end_date)의 종목 뉴스 조회
    async def get_news_by_date_range(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100,
        order: str = "desc",
        sort: str = "published_utc"
    ) -> Optional[List[Dict[str, Any]]]:
        try:
            url = f"{self.base_url}/v2/reference/news"
            
            # 날짜를 YYYY-MM-DD 형식으로 변환
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            params = {
                "ticker": ticker.upper(),
                "limit": min(limit, 1000),
                "order": order,
                "sort": sort,
                "published_utc.gte": start_date_str,  # 시작 날짜 이후
                "published_utc.lte": end_date_str      # 종료 날짜 이전
            }
            
            # API 키는 헤더에 포함
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            logger.info(
                "news_by_date_range_request",
                ticker=ticker,
                start_date=start_date_str,
                end_date=end_date_str,
                limit=limit
            )
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 429:
                    logger.warning(
                        "news_by_date_range_rate_limit",
                        ticker=ticker,
                        start_date=start_date_str,
                        end_date=end_date_str,
                        message="Rate limit exceeded, skipping"
                    )
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if not results:
                    logger.debug(
                        "news_by_date_range_no_data",
                        ticker=ticker,
                        start_date=start_date_str,
                        end_date=end_date_str
                    )
                    return []
                
                logger.info(
                    "news_by_date_range_fetched",
                    ticker=ticker,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    count=len(results)
                )
                
                return results
                
        except httpx.HTTPStatusError as e:
            logger.warning(
                "news_by_date_range_api_failed",
                ticker=ticker,
                start_date=start_date.strftime("%Y-%m-%d") if isinstance(start_date, datetime) else str(start_date),
                end_date=end_date.strftime("%Y-%m-%d") if isinstance(end_date, datetime) else str(end_date),
                status_code=e.response.status_code,
                response=e.response.text[:200] if e.response.text else ""
            )
            return None
        except Exception as e:
            logger.warning(
                "news_by_date_range_api_error",
                ticker=ticker,
                start_date=start_date.strftime("%Y-%m-%d") if isinstance(start_date, datetime) else str(start_date),
                end_date=end_date.strftime("%Y-%m-%d") if isinstance(end_date, datetime) else str(end_date),
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    # next_url에서 cursor 파라미터 추출
    def _extract_cursor_from_url(self, url: str) -> Optional[str]:
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            cursor = params.get("cursor", [None])[0]
            return cursor
        except Exception:
            return None

