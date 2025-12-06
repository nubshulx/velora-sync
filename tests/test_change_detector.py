"""
Unit tests for change detector
"""

import pytest
from src.core.change_detector import ChangeDetector, Change
from src.utils.cache import CacheManager
from pathlib import Path
import tempfile


@pytest.fixture
def cache_manager():
    """Create temporary cache manager for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield CacheManager(Path(tmpdir))


@pytest.fixture
def change_detector(cache_manager):
    """Create change detector instance"""
    return ChangeDetector(cache_manager)


def test_detect_new_requirements(change_detector):
    """Test detection of new requirements"""
    current_requirements = [
        {'id': 'REQ-001', 'title': 'Login', 'content': 'User should be able to login'},
        {'id': 'REQ-002', 'title': 'Logout', 'content': 'User should be able to logout'}
    ]
    
    previous_requirements = []
    
    changes, has_changes = change_detector.detect_changes(current_requirements, previous_requirements)
    
    assert has_changes is True
    assert len(changes) == 2
    assert all(c.change_type == 'added' for c in changes)


def test_detect_modified_requirements(change_detector):
    """Test detection of modified requirements"""
    current_requirements = [
        {'id': 'REQ-001', 'title': 'Login', 'content': 'User should be able to login with email'}
    ]
    
    previous_requirements = [
        {'id': 'REQ-001', 'title': 'Login', 'content': 'User should be able to login'}
    ]
    
    changes, has_changes = change_detector.detect_changes(current_requirements, previous_requirements)
    
    assert has_changes is True
    assert len(changes) == 1
    assert changes[0].change_type == 'modified'
    assert changes[0].requirement_id == 'REQ-001'


def test_detect_removed_requirements(change_detector):
    """Test detection of removed requirements"""
    current_requirements = [
        {'id': 'REQ-001', 'title': 'Login', 'content': 'User should be able to login'}
    ]
    
    previous_requirements = [
        {'id': 'REQ-001', 'title': 'Login', 'content': 'User should be able to login'},
        {'id': 'REQ-002', 'title': 'Logout', 'content': 'User should be able to logout'}
    ]
    
    changes, has_changes = change_detector.detect_changes(current_requirements, previous_requirements)
    
    assert has_changes is True
    assert len(changes) == 1
    assert changes[0].change_type == 'removed'
    assert changes[0].requirement_id == 'REQ-002'


def test_no_changes(change_detector):
    """Test when no changes are detected"""
    requirements = [
        {'id': 'REQ-001', 'title': 'Login', 'content': 'User should be able to login'}
    ]
    
    changes, has_changes = change_detector.detect_changes(requirements, requirements)
    
    assert has_changes is False
    assert len(changes) == 0


def test_change_summary(change_detector):
    """Test change summary generation"""
    changes = [
        Change('added', 'REQ-001', None, 'New content', 'New requirement'),
        Change('modified', 'REQ-002', 'Old', 'New', '1 line(s) added'),
        Change('removed', 'REQ-003', 'Old content', None, 'Removed requirement')
    ]
    
    summary = change_detector.get_change_summary(changes)
    
    assert summary['total_changes'] == 3
    assert summary['added'] == 1
    assert summary['modified'] == 1
    assert summary['removed'] == 1
    assert 'REQ-001' in summary['changes_by_id']
