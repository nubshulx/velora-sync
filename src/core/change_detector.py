"""
Change detection for requirements
"""

import difflib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from src.utils.logger import get_logger
from src.utils.cache import CacheManager

logger = get_logger(__name__)


@dataclass
class Change:
    """Represents a change in requirements"""
    change_type: str  # 'added', 'modified', 'removed'
    requirement_id: str
    old_content: Optional[str]
    new_content: Optional[str]
    diff_summary: str


class ChangeDetector:
    """Detects changes in requirements between runs"""
    
    def __init__(self, cache_manager: CacheManager):
        """
        Initialize change detector
        
        Args:
            cache_manager: Cache manager for storing previous state
        """
        self.cache_manager = cache_manager
    
    def detect_changes(
        self,
        current_requirements: List[Dict[str, str]],
        previous_requirements: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[List[Change], bool]:
        """
        Detect changes between current and previous requirements
        
        Args:
            current_requirements: Current requirements list
            previous_requirements: Previous requirements list (optional)
            
        Returns:
            Tuple of (list of changes, has_changes flag)
        """
        logger.info("Detecting requirement changes")
        
        # If no previous requirements provided, try to load from cache
        if previous_requirements is None:
            cached_content = self.cache_manager.get_requirements_content()
            if cached_content:
                # Parse cached content (simplified - in real scenario would need proper parsing)
                previous_requirements = self._parse_cached_requirements(cached_content)
            else:
                logger.info("No previous requirements found - treating all as new")
                return self._all_requirements_as_new(current_requirements), True
        
        # Create indices for quick lookup
        current_index = {req['id']: req for req in current_requirements}
        previous_index = {req['id']: req for req in previous_requirements}
        
        changes = []
        
        # Check for added and modified requirements
        for req_id, current_req in current_index.items():
            if req_id not in previous_index:
                # New requirement
                change = Change(
                    change_type='added',
                    requirement_id=req_id,
                    old_content=None,
                    new_content=current_req['content'],
                    diff_summary=f"New requirement: {current_req.get('title', req_id)}"
                )
                changes.append(change)
                logger.debug(f"Detected new requirement: {req_id}")
            else:
                # Check if modified
                previous_req = previous_index[req_id]
                if current_req['content'] != previous_req['content']:
                    diff_summary = self._generate_diff_summary(
                        previous_req['content'],
                        current_req['content']
                    )
                    change = Change(
                        change_type='modified',
                        requirement_id=req_id,
                        old_content=previous_req['content'],
                        new_content=current_req['content'],
                        diff_summary=diff_summary
                    )
                    changes.append(change)
                    logger.debug(f"Detected modified requirement: {req_id}")
        
        # Check for removed requirements
        for req_id, previous_req in previous_index.items():
            if req_id not in current_index:
                change = Change(
                    change_type='removed',
                    requirement_id=req_id,
                    old_content=previous_req['content'],
                    new_content=None,
                    diff_summary=f"Removed requirement: {previous_req.get('title', req_id)}"
                )
                changes.append(change)
                logger.debug(f"Detected removed requirement: {req_id}")
        
        has_changes = len(changes) > 0
        logger.info(f"Detected {len(changes)} changes")
        
        return changes, has_changes
    
    def _generate_diff_summary(self, old_content: str, new_content: str) -> str:
        """
        Generate human-readable diff summary
        
        Args:
            old_content: Previous content
            new_content: Current content
            
        Returns:
            Diff summary string
        """
        # Use difflib to generate diff
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')
        
        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm='',
            n=1  # Context lines
        ))
        
        if not diff:
            return "No changes detected"
        
        # Count additions and deletions
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        summary_parts = []
        if additions > 0:
            summary_parts.append(f"{additions} line(s) added")
        if deletions > 0:
            summary_parts.append(f"{deletions} line(s) removed")
        
        return ", ".join(summary_parts) if summary_parts else "Content modified"
    
    def _all_requirements_as_new(
        self,
        requirements: List[Dict[str, str]]
    ) -> List[Change]:
        """
        Treat all requirements as new
        
        Args:
            requirements: List of requirements
            
        Returns:
            List of changes marking all as added
        """
        changes = []
        for req in requirements:
            change = Change(
                change_type='added',
                requirement_id=req['id'],
                old_content=None,
                new_content=req['content'],
                diff_summary=f"New requirement: {req.get('title', req['id'])}"
            )
            changes.append(change)
        return changes
    
    def _parse_cached_requirements(self, cached_content: str) -> List[Dict[str, str]]:
        """
        Parse cached requirements content
        
        Args:
            cached_content: Cached text content
            
        Returns:
            List of requirement dictionaries
        """
        # Simple parsing - treat entire content as single requirement
        # In production, would use same parsing logic as WordReader
        return [{
            'id': 'CACHED',
            'title': 'Cached Requirements',
            'content': cached_content
        }]
    
    def get_change_summary(self, changes: List[Change]) -> Dict[str, any]:
        """
        Get summary statistics of changes
        
        Args:
            changes: List of changes
            
        Returns:
            Dictionary with change statistics
        """
        summary = {
            'total_changes': len(changes),
            'added': sum(1 for c in changes if c.change_type == 'added'),
            'modified': sum(1 for c in changes if c.change_type == 'modified'),
            'removed': sum(1 for c in changes if c.change_type == 'removed'),
            'changes_by_id': {}
        }
        
        for change in changes:
            summary['changes_by_id'][change.requirement_id] = {
                'type': change.change_type,
                'summary': change.diff_summary
            }
        
        return summary
