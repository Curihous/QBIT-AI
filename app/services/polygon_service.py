"""
Polygon.io API 호출 서비스: Top 3000 유동성 종목 리스트 조회
"""
import httpx
import structlog
from typing import Optional, List, Dict, Any
from app.config import get_settings

logger = structlog.get_logger()


class PolygonService:
    """
    Polygon.io API를 호출하여 주식 데이터를 가져오는 서비스
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://api.polygon.io"
        self.api_key = self.settings.polygon_api_key
    
    async def get_top_tickers(
        self,
        limit: int = 1000,
        market: str = "stocks",
        active: bool = True,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Top 티커 리스트 조회 (목록만)
        
        Args:
            limit: 한 번에 가져올 최대 개수 (최대 1000)
            market: 시장 유형 (stocks)
            active: 활성 종목만 (True)
            cursor: 페이지네이션 커서 (다음 페이지 조회용)
        
        Returns:
            {
                "results": [...],
                "next_url": "..." or None
            }
        """
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
                "polygon_api_call",
                endpoint="/v3/reference/tickers",
                limit=limit,
                cursor=cursor is not None
            )
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                logger.info(
                    "polygon_api_call_success",
                    result_count=len(data.get("results", [])),
                    has_next=bool(data.get("next_url"))
                )
                
                return data
                
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500] if e.response.text else "No error detail"
            logger.error(
                "polygon_api_call_failed",
                status_code=e.response.status_code,
                response=error_detail,
                url=url,
                params=params
            )
            raise Exception(f"Polygon API 호출 실패: {e.response.status_code} - {error_detail}")
        except Exception as e:
            logger.error(
                "polygon_api_call_error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise Exception(f"Polygon API 호출 중 오류: {str(e)}")
    
    async def get_top_tickers_screener(
        self,
        limit: int = 1000,
        order_by: str = "marketCap",
        sort: str = "desc",
        next_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Stocks Screener API로 시가총액 기준 Top 티커 리스트 조회
        
        Args:
            limit: 한 번에 가져올 최대 개수 (최대 1000)
            order_by: 정렬 기준 (marketCap)
            sort: 정렬 순서 (desc: 내림차순, asc: 오름차순)
            next_url: 페이지네이션을 위한 다음 페이지 URL
        
        Returns:
            {
                "results": [...],
                "next_url": "..." or None
            }
        """
        try:
            url = f"{self.base_url}/v1/market/stocks/screener"
            
            if next_url:
                # next_url이 있으면 해당 URL 사용 (이미 파라미터 포함됨)
                full_url = next_url
                # next_url에 apiKey가 없으면 추가
                if "apiKey" not in full_url:
                    separator = "&" if "?" in full_url else "?"
                    full_url = f"{full_url}{separator}apiKey={self.api_key}"
            else:
                # 첫 번째 요청: POST 본문에 파라미터 포함
                full_url = f"{url}?apiKey={self.api_key}"
            
            request_body = {
                "orderBy": order_by,
                "sort": sort,
                "limit": min(limit, 1000)
            } if not next_url else None
            
            logger.info(
                "polygon_screener_api_call",
                endpoint="/v1/market/stocks/screener",
                limit=limit,
                order_by=order_by,
                sort=sort,
                has_next_url=bool(next_url)
            )
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if next_url:
                    # 다음 페이지: GET 요청
                    response = await client.get(full_url)
                else:
                    # 첫 페이지: POST 요청
                    response = await client.post(full_url, json=request_body)
                
                response.raise_for_status()
                data = response.json()
                
                # 응답 데이터 확인
                sample_result = data.get("results", [])[0] if data.get("results") else {}
                logger.info(
                    "polygon_screener_api_call_success",
                    result_count=len(data.get("results", [])),
                    has_next=bool(data.get("next_url")),
                    sample_fields=list(sample_result.keys())[:10] if sample_result else []
                )
                
                return data
                
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:500] if e.response.text else "No error detail"
            logger.error(
                "polygon_screener_api_call_failed",
                status_code=e.response.status_code,
                response=error_detail,
                url=full_url,
                request_body=request_body
            )
            raise Exception(f"Polygon Screener API 호출 실패: {e.response.status_code} - {error_detail}")
        except Exception as e:
            logger.error(
                "polygon_screener_api_call_error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise Exception(f"Polygon Screener API 호출 중 오류: {str(e)}")
    
    async def get_ticker_details(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        개별 티커의 상세 정보 조회 (market_cap 포함)
        
        Args:
            ticker: 티커 심볼 (예: "AAPL")
        
        Returns:
            티커 상세 정보 (market_cap 포함)
        """
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
    
    async def get_top_3000_tickers(self) -> List[Dict[str, Any]]:
        """
        시가총액 기준 상위 3000개 티커 조회
        
        프로세스:
        1. 티커 목록을 먼저 충분히 수집 (8000개 - market_cap이 없는 종목이 많아서 여유 있게)
        2. 각 티커의 상세 정보를 순차적으로 조회하여 market_cap 수집 (배치 10개씩)
        3. market_cap 기준으로 정렬
        4. 상위 3000개 반환
        
        Returns:
            시가총액 기준 정렬된 티커 리스트 (최대 3000개)
        """
        import asyncio
        
        # 1. 티커 목록 먼저 충분히 수집 (8000개 - market_cap이 없는 종목이 많아서 여유 있게)
        all_tickers = []
        cursor = None
        page = 1
        target_collect = 8000  # 3000개 확보를 위해 충분히 많이 수집
        
        logger.info("polygon_starting_ticker_collection", target=target_collect)
        
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
            "polygon_ticker_list_collected",
            total_count=len(all_tickers)
        )
        
        # 2. 각 티커의 market_cap 정보 순차적으로 조회 (작은 배치로)
        tickers_with_market_cap = []
        batch_size = 10  # 작은 배치로 줄임 (API 제한 방지)
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
                "polygon_market_cap_batch",
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
            
            # API 제한 방지 (배치 간 대기 증가)
            await asyncio.sleep(0.5)
        
        # 3. market_cap 기준 정렬 (내림차순)
        tickers_with_market_cap.sort(
            key=lambda x: x.get("market_cap", 0) or 0,
            reverse=True
        )
        
        logger.info(
            "polygon_top_3000_completed",
            total_collected=len(all_tickers),
            with_market_cap=len(tickers_with_market_cap),
            final_count=min(3000, len(tickers_with_market_cap)),
            method="ticker_details_with_market_cap"
        )
        
        # 4. 상위 3000개 반환
        return tickers_with_market_cap[:3000]  
    
    def _extract_cursor_from_url(self, url: str) -> Optional[str]:
        """
        next_url에서 cursor 파라미터 추출
        """
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            cursor = params.get("cursor", [None])[0]
            return cursor
        except Exception:
            return None

