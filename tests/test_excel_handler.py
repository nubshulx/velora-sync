"""
Unit tests for Excel handler
"""

import pytest
from src.document_readers.excel_handler import ExcelHandler
from pathlib import Path
import tempfile
import openpyxl


@pytest.fixture
def template():
    """Test case template"""
    return {
        "Test Case ID": "TC001",
        "Title": "Sample test",
        "Steps": "1. Test step",
        "Expected": "Pass"
    }


@pytest.fixture
def excel_handler(template):
    """Create Excel handler instance"""
    return ExcelHandler(template=template, create_backup=False)


@pytest.fixture
def temp_excel_file():
    """Create temporary Excel file"""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        temp_path = Path(f.name)
    yield temp_path
    if temp_path.exists():
        temp_path.unlink()


def test_write_new_test_cases(excel_handler, temp_excel_file):
    """Test writing new test cases to Excel"""
    test_cases = [
        {
            "Test Case ID": "TC-001",
            "Title": "Test login",
            "Steps": "1. Open app\n2. Login",
            "Expected": "User logged in"
        },
        {
            "Test Case ID": "TC-002",
            "Title": "Test logout",
            "Steps": "1. Click logout",
            "Expected": "User logged out"
        }
    ]
    
    stats = excel_handler.write_test_cases(
        document_path=str(temp_excel_file),
        test_cases=test_cases,
        mode='new_only'
    )
    
    assert stats['created'] == 2
    assert stats['total'] == 2
    assert temp_excel_file.exists()


def test_read_test_cases(excel_handler, temp_excel_file):
    """Test reading test cases from Excel"""
    # First write some test cases
    test_cases = [
        {
            "Test Case ID": "TC-001",
            "Title": "Test login",
            "Steps": "1. Login",
            "Expected": "Success"
        }
    ]
    
    excel_handler.write_test_cases(
        document_path=str(temp_excel_file),
        test_cases=test_cases,
        mode='new_only'
    )
    
    # Now read them back
    read_cases = excel_handler.read_test_cases(str(temp_excel_file))
    
    assert len(read_cases) == 1
    assert read_cases[0]['Test Case ID'] == 'TC-001'
    assert read_cases[0]['Title'] == 'Test login'


def test_merge_new_only_mode(excel_handler, temp_excel_file):
    """Test merging in new_only mode"""
    # Write initial test cases
    initial_cases = [
        {"Test Case ID": "TC-001", "Title": "Test 1", "Steps": "Step 1", "Expected": "Pass"}
    ]
    
    excel_handler.write_test_cases(
        document_path=str(temp_excel_file),
        test_cases=initial_cases,
        mode='new_only'
    )
    
    # Add new test cases
    new_cases = [
        {"Test Case ID": "TC-001", "Title": "Modified Test 1", "Steps": "New steps", "Expected": "Pass"},
        {"Test Case ID": "TC-002", "Title": "Test 2", "Steps": "Step 2", "Expected": "Pass"}
    ]
    
    stats = excel_handler.write_test_cases(
        document_path=str(temp_excel_file),
        test_cases=new_cases,
        mode='new_only'
    )
    
    # Should only add TC-002, keep TC-001 unchanged
    assert stats['created'] == 1
    assert stats['unchanged'] == 1
    assert stats['total'] == 2


def test_merge_full_sync_mode(excel_handler, temp_excel_file):
    """Test merging in full_sync mode"""
    # Write initial test cases
    initial_cases = [
        {"Test Case ID": "TC-001", "Title": "Test 1", "Steps": "Step 1", "Expected": "Pass"}
    ]
    
    excel_handler.write_test_cases(
        document_path=str(temp_excel_file),
        test_cases=initial_cases,
        mode='full_sync'
    )
    
    # Update and add test cases
    new_cases = [
        {"Test Case ID": "TC-001", "Title": "Modified Test 1", "Steps": "New steps", "Expected": "Pass"},
        {"Test Case ID": "TC-002", "Title": "Test 2", "Steps": "Step 2", "Expected": "Pass"}
    ]
    
    stats = excel_handler.write_test_cases(
        document_path=str(temp_excel_file),
        test_cases=new_cases,
        mode='full_sync'
    )
    
    # Should update TC-001 and add TC-002
    assert stats['created'] == 1
    assert stats['updated'] == 1
    assert stats['total'] == 2
