"""
Upstash Redis caching utilities for Velora Sync
Provides distributed caching for requirement document versioning
"""

import json
import hashlib
from typing import Any, Optional, Dict, List
from datetime import datetime

from src.utils.logger import get_logger

logger = get_logger(__name__)


class UpstashCacheManager:
    """Manages Upstash Redis-based caching for requirements with versioning"""
    
    # Cache key prefixes
    KEY_DOCUMENT_CONTENT = "velora:document:content"
    KEY_DOCUMENT_HASH = "velora:document:hash"
    KEY_DOCUMENT_METADATA = "velora:document:metadata"
    KEY_REQUIREMENTS = "velora:requirements"
    
    def __init__(
        self,
        rest_url: str,
        rest_token: str,
        ttl_days: int = 30
    ):
        """
        Initialize Upstash Redis connection
        
        Args:
            rest_url: Upstash Redis REST URL
            rest_token: Upstash Redis REST token
            ttl_days: Time-to-live for cached data in days
        """
        self.rest_url = rest_url
        self.rest_token = rest_token
        self.ttl_seconds = ttl_days * 24 * 60 * 60
        self._redis = None
        self._connected = False
        
        self._init_connection()
    
    def _init_connection(self) -> None:
        """Initialize connection to Upstash Redis"""
        try:
            from upstash_redis import Redis
            
            self._redis = Redis(
                url=self.rest_url,
                token=self.rest_token
            )
            
            # Test connection with a ping
            self._redis.ping()
            self._connected = True
            logger.info("Connected to Upstash Redis successfully")
            
        except ImportError:
            logger.error("upstash-redis package not installed. Run: pip install upstash-redis")
            self._connected = False
        except Exception as e:
            logger.warning(f"Failed to connect to Upstash Redis: {e}")
            self._connected = False
    
    def is_connected(self) -> bool:
        """
        Check if Upstash Redis is available
        
        Returns:
            True if connected, False otherwise
        """
        if not self._redis:
            return False
        
        try:
            self._redis.ping()
            return True
        except Exception:
            return False
    
    def compute_hash(self, content: str) -> str:
        """
        Compute SHA-256 hash of content
        
        Args:
            content: Content to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_previous_document_content(self) -> Optional[str]:
        """
        Get cached document content from previous run
        
        Returns:
            Previous document content or None if not cached
        """
        if not self._connected:
            return None
        
        try:
            content = self._redis.get(self.KEY_DOCUMENT_CONTENT)
            if content:
                logger.debug("Retrieved previous document content from Upstash cache")
                return content
            return None
        except Exception as e:
            logger.warning(f"Failed to get document content from Upstash: {e}")
            return None
    
    def set_document_content(
        self,
        content: str,
        requirements: Optional[List[Dict]] = None
    ) -> None:
        """
        Cache current document content and parsed requirements
        
        Args:
            content: Document content text
            requirements: Parsed requirements list (optional)
        """
        if not self._connected:
            logger.warning("Upstash not connected, skipping cache update")
            return
        
        try:
            # Store document content
            self._redis.set(
                self.KEY_DOCUMENT_CONTENT,
                content,
                ex=self.ttl_seconds
            )
            
            # Store document hash
            content_hash = self.compute_hash(content)
            self._redis.set(
                self.KEY_DOCUMENT_HASH,
                content_hash,
                ex=self.ttl_seconds
            )
            
            # Store metadata
            metadata = {
                'hash': content_hash,
                'updated_at': datetime.now().isoformat(),
                'content_length': len(content),
                'requirements_count': len(requirements) if requirements else 0
            }
            self._redis.set(
                self.KEY_DOCUMENT_METADATA,
                json.dumps(metadata),
                ex=self.ttl_seconds
            )
            
            # Store parsed requirements if provided
            if requirements:
                self._redis.set(
                    self.KEY_REQUIREMENTS,
                    json.dumps(requirements),
                    ex=self.ttl_seconds
                )
            
            logger.info("Document content cached to Upstash Redis")
            
        except Exception as e:
            logger.warning(f"Failed to cache document content to Upstash: {e}")
    
    def get_requirements_hash(self) -> Optional[str]:
        """
        Get cached requirements document hash
        
        Returns:
            Hash string or None if not cached
        """
        if not self._connected:
            return None
        
        try:
            return self._redis.get(self.KEY_DOCUMENT_HASH)
        except Exception as e:
            logger.warning(f"Failed to get document hash from Upstash: {e}")
            return None
    
    def set_requirements_hash(self, content_hash: str) -> None:
        """
        Cache requirements document hash
        
        Args:
            content_hash: Hash of requirements content
        """
        if not self._connected:
            return
        
        try:
            self._redis.set(
                self.KEY_DOCUMENT_HASH,
                content_hash,
                ex=self.ttl_seconds
            )
        except Exception as e:
            logger.warning(f"Failed to set document hash in Upstash: {e}")
    
    def get_requirements_content(self) -> Optional[str]:
        """
        Get cached requirements content (alias for get_previous_document_content)
        
        Returns:
            Requirements text or None if not cached
        """
        return self.get_previous_document_content()
    
    def set_requirements_content(self, content: str) -> None:
        """
        Cache requirements content
        
        Args:
            content: Requirements text
        """
        self.set_document_content(content)
    
    def get_cached_requirements(self) -> Optional[List[Dict]]:
        """
        Get cached parsed requirements
        
        Returns:
            List of requirement dictionaries or None
        """
        if not self._connected:
            return None
        
        try:
            data = self._redis.get(self.KEY_REQUIREMENTS)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Failed to get requirements from Upstash: {e}")
            return None
    
    def get_document_version_info(self) -> Dict[str, Any]:
        """
        Get version metadata for cached document
        
        Returns:
            Dictionary with version info (hash, timestamp, etc.)
        """
        if not self._connected:
            return {}
        
        try:
            metadata_str = self._redis.get(self.KEY_DOCUMENT_METADATA)
            if metadata_str:
                return json.loads(metadata_str)
            return {}
        except Exception as e:
            logger.warning(f"Failed to get document version info from Upstash: {e}")
            return {}
    
    def has_document_changed(self, current_content: str) -> bool:
        """
        Quick hash-based change detection
        
        Args:
            current_content: Current document content
            
        Returns:
            True if document has changed or no cache exists
        """
        current_hash = self.compute_hash(current_content)
        cached_hash = self.get_requirements_hash()
        
        if cached_hash is None:
            logger.info("No cached hash found - treating as changed")
            return True
        
        has_changed = current_hash != cached_hash
        if has_changed:
            logger.info("Document hash changed - content has been modified")
        else:
            logger.info("Document hash matches - no changes detected")
        
        return has_changed
    
    # Alias for compatibility with existing CacheManager interface
    def has_requirements_changed(self, current_content: str) -> bool:
        """
        Check if requirements have changed since last run
        
        Args:
            current_content: Current requirements text
            
        Returns:
            True if changed or no cache exists, False otherwise
        """
        return self.has_document_changed(current_content)
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        if not self._connected:
            return
        
        try:
            self._redis.delete(self.KEY_DOCUMENT_CONTENT)
            self._redis.delete(self.KEY_DOCUMENT_HASH)
            self._redis.delete(self.KEY_DOCUMENT_METADATA)
            self._redis.delete(self.KEY_REQUIREMENTS)
            logger.info("Upstash cache cleared")
        except Exception as e:
            logger.warning(f"Failed to clear Upstash cache: {e}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get cache information
        
        Returns:
            Dictionary with cache metadata
        """
        version_info = self.get_document_version_info()
        return {
            'cache_type': 'upstash_redis',
            'connected': self._connected,
            'rest_url': self.rest_url[:30] + '...' if len(self.rest_url) > 30 else self.rest_url,
            'ttl_seconds': self.ttl_seconds,
            'metadata': version_info
        }
