"""
HTML Cleaner for News Articles

Removes HTML tags, scripts, styles, and normalizes whitespace.
"""

import logging
import re
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HTMLCleaner:
    """
    Cleans HTML content from news articles.
    
    Removes:
    - Script and style tags
    - HTML comments
    - Navigation, footer, header elements
    - Advertising and tracking elements
    - Excessive whitespace
    """
    
    # Tags to completely remove (including content)
    REMOVE_TAGS = {
        'script', 'style', 'noscript', 'iframe', 'embed', 'object',
        'applet', 'form', 'input', 'button', 'select', 'textarea',
        'nav', 'header', 'footer', 'aside', 'figure', 'figcaption',
        'meta', 'link', 'head', 'title', 'base'
    }
    
    # Tags to unwrap (keep content, remove tag)
    UNWRAP_TAGS = {
        'div', 'span', 'section', 'article', 'main', 'p', 'br',
        'strong', 'b', 'em', 'i', 'u', 'a', 'ul', 'ol', 'li',
        'blockquote', 'cite', 'q', 'code', 'pre', 'h1', 'h2', 'h3',
        'h4', 'h5', 'h6', 'table', 'thead', 'tbody', 'tr', 'td', 'th',
        'img', 'picture', 'source', 'video', 'audio', 'canvas'
    }
    
    # Attributes to preserve
    KEEP_ATTRS = {'href', 'src', 'alt', 'title', 'datetime'}
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.keep_links = self.config.get('keep_links', True)
        self.keep_images = self.config.get('keep_images', False)
        self.max_length = self.config.get('max_length', 50000)
    
    def clean(self, html: str) -> str:
        """
        Clean HTML content and return plain text.
        
        Args:
            html: Raw HTML string
            
        Returns:
            Cleaned plain text
        """
        if not html or not html.strip():
            return ""
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted tags completely
            for tag in soup.find_all(self.REMOVE_TAGS):
                tag.decompose()
            
            # Remove comments
            for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.startswith('<!--')):
                comment.extract()
            
            # Remove advertising/tracking elements
            self._remove_ads_and_tracking(soup)
            
            # Unwrap allowed tags (keep content)
            for tag in soup.find_all(self.UNWRAP_TAGS):
                # Preserve link href if keeping links
                if tag.name == 'a' and self.keep_links and tag.get('href'):
                    tag['data-href'] = tag['href']
                # Preserve image src if keeping images
                elif tag.name == 'img' and self.keep_images and tag.get('src'):
                    tag['data-src'] = tag['src']
                    tag['data-alt'] = tag.get('alt', '')
                
                # Remove all attributes except allowed ones
                attrs_to_remove = [attr for attr in tag.attrs if attr not in self.KEEP_ATTRS and not attr.startswith('data-')]
                for attr in attrs_to_remove:
                    del tag[attr]
                
                tag.unwrap()
            
            # Get text
            text = soup.get_text(separator=' ', strip=True)
            
            # Normalize whitespace
            text = self._normalize_whitespace(text)
            
            # Truncate if too long
            if len(text) > self.max_length:
                text = text[:self.max_length] + "... [truncated]"
            
            return text
            
        except Exception as e:
            logger.warning(f"HTML cleaning failed: {e}")
            # Fallback: basic regex cleaning
            return self._fallback_clean(html)
    
    def _remove_ads_and_tracking(self, soup: BeautifulSoup) -> None:
        """Remove common ad and tracking elements."""
        # Common ad classes/ids
        ad_patterns = [
            'ad', 'ads', 'advert', 'advertisement', 'sponsored',
            'promo', 'banner', 'popup', 'modal', 'overlay',
            'tracking', 'analytics', 'pixel', 'beacon',
            'newsletter', 'subscribe', 'signup', 'paywall'
        ]
        
        # Remove by class
        for pattern in ad_patterns:
            for elem in soup.find_all(class_=re.compile(pattern, re.I)):
                elem.decompose()
            for elem in soup.find_all(id=re.compile(pattern, re.I)):
                elem.decompose()
        
        # Remove elements with specific attributes
        for elem in soup.find_all(attrs={'data-ad': True}):
            elem.decompose()
        for elem in soup.find_all(attrs={'data-track': True}):
            elem.decompose()
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Remove space before punctuation
        text = re.sub(r'\s+([.,;:!?)])', r'\1', text)
        # Remove space after opening punctuation
        text = re.sub(r'([\(\[\{"])\s+', r'\1', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        # Replace newline+space with newline
        text = re.sub(r'\n +', '\n', text)
        # Trim each line
        lines = [line.strip() for line in text.split('\n')]
        # Remove empty lines at start/end
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        return '\n'.join(lines)
    
    def _fallback_clean(self, html: str) -> str:
        """Fallback regex-based cleaning."""
        # Remove script/style blocks
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        # Remove all tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Normalize whitespace
        text = self._normalize_whitespace(text)
        return text


def clean_html(html: str, config: Optional[dict] = None) -> str:
    """Convenience function to clean HTML."""
    cleaner = HTMLCleaner(config)
    return cleaner.clean(html)