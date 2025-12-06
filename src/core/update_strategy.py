"""
Update strategy handler for test cases
"""

from typing import List, Dict, Any
from dataclasses import dataclass

from src.core.change_detector import Change
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class UpdatePlan:
    """Plan for updating test cases"""
    requirements_to_process: List[Dict[str, str]]
    mode: str
    reason: str


class UpdateStrategy:
    """Handles update strategy for test cases"""
    
    def __init__(self, mode: str = 'new_only'):
        """
        Initialize update strategy
        
        Args:
            mode: Update mode ('new_only' or 'full_sync')
        """
        if mode not in ['new_only', 'full_sync']:
            raise ValueError(f"Invalid mode: {mode}. Must be 'new_only' or 'full_sync'")
        
        self.mode = mode
        logger.info(f"Initialized update strategy with mode: {mode}")
    
    def create_update_plan(
        self,
        changes: List[Change],
        all_requirements: List[Dict[str, str]]
    ) -> UpdatePlan:
        """
        Create update plan based on changes and mode
        
        Args:
            changes: List of detected changes
            all_requirements: All current requirements
            
        Returns:
            UpdatePlan with requirements to process
        """
        logger.info(f"Creating update plan in {self.mode} mode")
        
        if not changes:
            logger.info("No changes detected - no updates needed")
            return UpdatePlan(
                requirements_to_process=[],
                mode=self.mode,
                reason="No changes detected"
            )
        
        if self.mode == 'new_only':
            return self._create_new_only_plan(changes, all_requirements)
        else:  # full_sync
            return self._create_full_sync_plan(changes, all_requirements)
    
    def _create_new_only_plan(
        self,
        changes: List[Change],
        all_requirements: List[Dict[str, str]]
    ) -> UpdatePlan:
        """
        Create plan for new_only mode
        
        Args:
            changes: List of changes
            all_requirements: All requirements
            
        Returns:
            UpdatePlan for new requirements only
        """
        # Only process added requirements
        added_req_ids = [c.requirement_id for c in changes if c.change_type == 'added']
        
        requirements_to_process = [
            req for req in all_requirements
            if req['id'] in added_req_ids
        ]
        
        logger.info(f"New-only mode: Processing {len(requirements_to_process)} new requirements")
        
        return UpdatePlan(
            requirements_to_process=requirements_to_process,
            mode=self.mode,
            reason=f"Processing {len(requirements_to_process)} new requirements (preserving existing test cases)"
        )
    
    def _create_full_sync_plan(
        self,
        changes: List[Change],
        all_requirements: List[Dict[str, str]]
    ) -> UpdatePlan:
        """
        Create plan for full_sync mode
        
        Args:
            changes: List of changes
            all_requirements: All requirements
            
        Returns:
            UpdatePlan for all changed requirements
        """
        # Process added and modified requirements
        changed_req_ids = [
            c.requirement_id for c in changes
            if c.change_type in ['added', 'modified']
        ]
        
        requirements_to_process = [
            req for req in all_requirements
            if req['id'] in changed_req_ids
        ]
        
        logger.info(f"Full-sync mode: Processing {len(requirements_to_process)} changed requirements")
        
        return UpdatePlan(
            requirements_to_process=requirements_to_process,
            mode=self.mode,
            reason=f"Processing {len(requirements_to_process)} changed requirements (updating existing test cases)"
        )
    
    def should_process_requirement(self, requirement_id: str, changes: List[Change]) -> bool:
        """
        Check if a requirement should be processed
        
        Args:
            requirement_id: Requirement ID
            changes: List of changes
            
        Returns:
            True if requirement should be processed
        """
        for change in changes:
            if change.requirement_id == requirement_id:
                if self.mode == 'new_only':
                    return change.change_type == 'added'
                else:  # full_sync
                    return change.change_type in ['added', 'modified']
        
        return False
    
    def get_change_description(self, requirement_id: str, changes: List[Change]) -> str:
        """
        Get description of changes for a requirement
        
        Args:
            requirement_id: Requirement ID
            changes: List of changes
            
        Returns:
            Change description string
        """
        for change in changes:
            if change.requirement_id == requirement_id:
                return change.diff_summary
        
        return "No changes"
