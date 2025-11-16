import httpx
import structlog
from typing import Optional
from bs4 import BeautifulSoup

# 기사 크롤링: BeautifulSoup을 이용한 웹 크롤링
logger = structlog.get_logger()


class ArticleScraper:
    
    @staticmethod
    async def scrape_article(url: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                })
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 불필요한 태그 제거
                for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
                    tag.decompose()
                
                # 전략 1: 다양한 선택자로 본문 찾기
                article_selectors = [
                    'article',
                    '.article-body',
                    '.article-content',
                    '.post-content',
                    '.entry-content',
                    '[class*="article-body"]',
                    '[class*="article-content"]',
                    '[class*="post-body"]',
                    '[itemprop="articleBody"]',
                    'main article',
                    'main',
                ]
                
                article = None
                for selector in article_selectors:
                    article = soup.select_one(selector)
                    if article:
                        # 네비게이션/메뉴 제거
                        for unwanted in article.select('nav, .nav, .menu, [role="navigation"]'):
                            unwanted.decompose()
                        
                        text = article.get_text(separator=' ', strip=True)
                        if len(text) > 200:
                            logger.debug("scraping_success_selector", url=url[:50], selector=selector, length=len(text))
                            return text
                
                # 전략 2: paragraph 기반 본문 추출 (선택자 실패 시)
                paragraphs = soup.find_all('p')
                if paragraphs:
                    # 긴 paragraph만 추출 (50자 이상)
                    long_paragraphs = []
                    for p in paragraphs:
                        p_text = p.get_text(strip=True)
                        # 링크가 너무 많으면 네비게이션으로 간주
                        links = p.find_all('a')
                        if len(p_text) > 50 and len(links) < 3:
                            long_paragraphs.append(p_text)
                    
                    if long_paragraphs:
                        text = ' '.join(long_paragraphs)
                        if len(text) > 200:
                            logger.debug("scraping_success_paragraphs", url=url[:50], paragraphs_count=len(long_paragraphs), length=len(text))
                            return text
                
                logger.debug("scraping_no_content_found", url=url[:50])
                return None
                
        except Exception as e:
            logger.debug("scraping_failed", url=url[:50], error=str(e))
            return None

