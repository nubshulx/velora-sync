"""
Caching utilities for Velora Sync
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Optional, Dict
from datetime import datetime


class CacheManager:
    """Manages caching for requirements and model data"""
    
    def __init__(self, cache_dir: Path):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "metadata.json"
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """Load cache metadata from file"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}
    
    def _save_metadata(self) -> None:
        """Save cache metadata to file"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)
    
    def compute_hash(self, content: str) -> str:
        """
        Compute SHA-256 hash of content
        
        Args:
            content: Content to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_requirements_hash(self) -> Optional[str]:
        """
        Get cached requirements document hash
        
        Returns:
            Hash string or None if not cached
        """
        return self.metadata.get('requirements_hash')
    
    def set_requirements_hash(self, content_hash: str) -> None:
        """
        Cache requirements document hash
        
        Args:
            content_hash: Hash of requirements content
        """
        self.metadata['requirements_hash'] = content_hash
        self.metadata['requirements_updated'] = datetime.now().isoformat()
        self._save_metadata()
    
    def get_requirements_content(self) -> Optional[str]:
        """
        Get cached requirements content
        
        Returns:
            Requirements text or None if not cached
        """
        cache_file = self.cache_dir / "requirements.txt"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def set_requirements_content(self, content: str) -> None:
        """
        Cache requirements content
        
        Args:
            content: Requirements text
        """
        cache_file = self.cache_dir / "requirements.txt"
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def has_requirements_changed(self, current_content: str) -> bool:
        """
        Check if requirements have changed since last run
        
        Args:
            current_content: Current requirements text
            
        Returns:
            True if changed or no cache exists, False otherwise
        """
        current_hash = self.compute_hash(current_content)
        cached_hash = self.get_requirements_hash()
        
        if cached_hash is None:
            return True
        
        return current_hash != cached_hash
    
    def get_test_cases_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Get cached test cases snapshot
        
        Returns:
            Test cases data or None if not cached
        """
        cache_file = self.cache_dir / "test_cases_snapshot.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def set_test_cases_snapshot(self, test_cases: Dict[str, Any]) -> None:
        """
        Cache test cases snapshot
        
        Args:
            test_cases: Test cases data
        """
        cache_file = self.cache_dir / "test_cases_snapshot.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(test_cases, f, indent=2)
    
    def clear_cache(self) -> None:
        """Clear all cache files"""
        for cache_file in self.cache_dir.glob("*"):
            if cache_file.is_file():
                cache_file.unlink()
        self.metadata = {}
        self._save_metadata()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get cache information
        
        Returns:
            Dictionary with cache metadata
        """
        return {
            'cache_dir': str(self.cache_dir),
            'metadata': self.metadata,
            'cache_files': [str(f) for f in self.cache_dir.glob("*") if f.is_file()]
        }
