"""
Main entry point for Velora Sync
"""

import sys
import os
from pathlib import Path
from typing import Optional

from config.config import Config
from src.utils.logger import setup_logger, get_logger
from src.utils.cache import CacheManager
from src.utils.exceptions import VeloraSyncException
from src.document_readers.sharepoint_client import SharePointClient
from src.document_readers.word_reader import WordReader
from src.document_readers.excel_handler import ExcelHandler
from src.llm.model_client import ModelClient
from src.llm.test_case_generator import TestCaseGenerator
from src.core.change_detector import ChangeDetector
from src.core.update_strategy import UpdateStrategy
from src.reporting.report_generator import ReportGenerator
from src.document_readers.google_drive_client import GoogleDriveClient


def main() -> int:
    """
    Main execution function
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    config: Optional[Config] = None
    logger = None
    errors = []
    warnings = []
    
    try:
        # Load configuration
        config = Config()
        
        # Setup logging
        is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
        log_file = config.get_log_file_path()
        logger = setup_logger(
            log_level=config['LOG_LEVEL'],
            log_file=log_file,
            github_actions=is_github_actions
        )
        
        logger.info("=" * 80)
        logger.info("VELORA SYNC - Enterprise Test Case Generation Tool")
        logger.info("=" * 80)
        logger.info(f"Configuration loaded successfully")
        logger.info(f"Update mode: {config['UPDATE_MODE']}")
        logger.info(f"LLM provider: {config['LLM_PROVIDER']}")
        if config['LLM_PROVIDER'] == 'gemini':
            logger.info(f"LLM model: {config['LLM_MODEL']} (FREE)")
        else:
            logger.info(f"LLM model: {config['LLM_MODEL']}")
        
        # Initialize components
        logger.info("Initializing components...")
        
        # SharePoint client (if needed)
        sharepoint_client = None
        if config.is_sharepoint_source() or config.is_sharepoint_destination():
            logger.info("Initializing SharePoint client")
            sharepoint_client = SharePointClient(
                tenant_id=config['SHAREPOINT_TENANT_ID'],
                client_id=config['SHAREPOINT_CLIENT_ID'],
                client_secret=config['SHAREPOINT_CLIENT_SECRET'],
                site_url=config['SHAREPOINT_SITE_URL'],
                timeout=config['API_TIMEOUT']
            )
        
        # Cache manager - use Upstash Redis if configured, otherwise file-based
        if config.is_upstash_enabled():
            from src.utils.redis_cache import UpstashCacheManager
            cache_manager = UpstashCacheManager(
                rest_url=config['UPSTASH_REDIS_REST_URL'],
                rest_token=config['UPSTASH_REDIS_REST_TOKEN']
            )
            if cache_manager.is_connected():
                logger.info("Using Upstash Redis for caching")
            else:
                logger.warning("Upstash connection failed, falling back to file-based cache")
                cache_manager = CacheManager(config['CACHE_DIR'])
        else:
            cache_manager = CacheManager(config['CACHE_DIR'])
            logger.info("Using file-based caching")
        
        # Word reader
        word_reader = WordReader(sharepoint_client=sharepoint_client)
        
        # Google Drive client (if credentials available)
        google_drive_client = None
        google_creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        google_creds_file = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
        
        if google_creds_json or google_creds_file:
            try:
                google_drive_client = GoogleDriveClient(
                    service_account_json=google_creds_json,
                    service_account_file=google_creds_file
                )
                if google_drive_client.is_authenticated():
                    logger.info("Google Drive client initialized")
                else:
                    logger.warning("Google Drive credentials provided but authentication failed")
                    google_drive_client = None
            except Exception as e:
                logger.warning(f"Failed to initialize Google Drive client: {e}")
                google_drive_client = None
        
        # Excel handler
        excel_handler = ExcelHandler(
            template=config['TEST_CASE_TEMPLATE'],
            sharepoint_client=sharepoint_client,
            google_drive_client=google_drive_client,
            create_backup=config['CREATE_BACKUP']
        )
        
        # LLM model client
        logger.info("Loading LLM model...")
        
        provider = config['LLM_PROVIDER']
        model_name = config['LLM_MODEL']
        api_token = config.get('API_TOKEN')
        
        logger.info(f"Provider: {provider}, Model: {model_name}")
        
        model_client = ModelClient(
            provider=provider,
            model_name=model_name,
            api_token=api_token,
            max_retries=config['MAX_RETRIES'],
            timeout=config['API_TIMEOUT']
        )
        
        # Test case generator
        test_case_generator = TestCaseGenerator(
            model_client=model_client,
            template=config['TEST_CASE_TEMPLATE'],
            max_tokens=config['MAX_TOKENS'],
            temperature=config['TEMPERATURE']
        )
        
        # Initialize orchestrator based on mode
        if config['UPDATE_MODE'] == 'intelligent':
            from src.core.intelligent_orchestrator import IntelligentTestCaseOrchestrator
            orchestrator = IntelligentTestCaseOrchestrator(
                model_client=model_client,
                test_case_generator=test_case_generator
            )
            logger.info("Using intelligent orchestrator")
        else:
            # Traditional modes
            change_detector = ChangeDetector(cache_manager=cache_manager)
            update_strategy = UpdateStrategy(mode=config['UPDATE_MODE'])
            orchestrator = None
            logger.info(f"Using traditional {config['UPDATE_MODE']} mode")
        
        # Report generator
        report_generator = ReportGenerator()
        
        logger.info("All components initialized successfully")
        
        # Step 1: Read requirements document
        logger.info("Step 1: Reading requirements document")
        requirements = word_reader.extract_requirements(config['SOURCE_DOCUMENT_PATH'])
        logger.info(f"Extracted {len(requirements)} requirement(s)")
        
        # Step 2: Read existing test cases
        logger.info("Step 2: Reading existing test cases")
        try:
            existing_test_cases = excel_handler.read_test_cases(config['DESTINATION_DOCUMENT_PATH'])
            logger.info(f"Found {len(existing_test_cases)} existing test case(s)")
        except:
            existing_test_cases = []
            logger.info("No existing test cases found (new file)")
        
        # Step 2.5: Analyze document changes using LLM
        full_content = word_reader.read_document(config['SOURCE_DOCUMENT_PATH'])
        previous_content = None
        change_analysis = None
        
        # Try to get previous content from cache
        if hasattr(cache_manager, 'get_previous_document_content'):
            previous_content = cache_manager.get_previous_document_content()
        elif hasattr(cache_manager, 'get_requirements_content'):
            previous_content = cache_manager.get_requirements_content()
        
        if previous_content:
            logger.info("Previous document version found in cache - analyzing changes...")
            from src.core.llm_change_analyzer import LLMChangeAnalyzer
            change_analyzer = LLMChangeAnalyzer(model_client)
            change_analysis = change_analyzer.analyze_changes(
                previous_content=previous_content,
                current_content=full_content
            )
            
            # Log change analysis summary
            if change_analysis.has_changes:
                logger.info("=" * 60)
                logger.info("DOCUMENT CHANGE ANALYSIS")
                logger.info("=" * 60)
                logger.info(f"Summary: {change_analysis.summary}")
                logger.info(f"Changes: Added={change_analysis.added_count}, Modified={change_analysis.modified_count}, Removed={change_analysis.removed_count}")
                for change in change_analysis.changes:
                    impact_marker = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}.get(change.impact, "")
                    logger.info(f"  - {change.change_type.upper()} {impact_marker}: {change.description}")
                logger.info("=" * 60)
            else:
                logger.info("No significant changes detected in requirements document")
        else:
            logger.info("No previous document version in cache - treating all requirements as new")
        
        # Step 3: Process based on mode
        if config['UPDATE_MODE'] == 'intelligent':
            logger.info("Step 3: Processing requirements intelligently")
            
            # Use intelligent orchestrator
            processing_results = orchestrator.process_requirements_intelligently(
                requirement_sections=requirements,
                existing_test_cases=existing_test_cases,
                mode='intelligent'
            )
            
            # Get all test cases
            all_test_cases = orchestrator.get_all_test_cases(processing_results)
            
            # Extract statistics
            test_case_stats = {
                'created': processing_results['statistics'].get('new_test_cases_created', 0),
                'updated': processing_results['statistics'].get('test_cases_updated', 0),
                'unchanged': processing_results['statistics'].get('test_cases_unchanged', 0),
                'total': len(all_test_cases)
            }
            
            changes = []  # Intelligent mode handles this internally
            
        else:
            # Traditional workflow
            logger.info("Step 3: Detecting changes in requirements")
            
            # full_content already read in Step 2.5
            
            # Check if requirements changed
            has_content_changed = cache_manager.has_requirements_changed(full_content)
            
            # Force processing if Excel file is empty (first run scenario)
            if len(existing_test_cases) == 0 and len(requirements) > 0:
                logger.info("Excel file is empty, forcing processing of all requirements")
                has_content_changed = True
            
            if not has_content_changed:
                logger.info("No changes detected in requirements document")
                changes = []
                has_changes = False
            else:
                logger.info("Changes detected, analyzing...")
                changes, has_changes = change_detector.detect_changes(requirements)
                
                # Update cache
                cache_manager.set_requirements_content(full_content)
                cache_manager.set_requirements_hash(cache_manager.compute_hash(full_content))
            
            # Create update plan
            logger.info("Step 4: Creating update plan")
            update_plan = update_strategy.create_update_plan(changes, requirements)
            logger.info(f"Update plan: {update_plan.reason}")
            
            # Generate test cases
            test_case_stats = {'created': 0, 'updated': 0, 'unchanged': 0, 'total': 0}
            all_test_cases = existing_test_cases.copy()
            
            if update_plan.requirements_to_process:
                logger.info(f"Step 5: Generating test cases for {len(update_plan.requirements_to_process)} requirement(s)")
                
                new_test_cases = test_case_generator.generate_from_requirements_batch(
                    requirements=update_plan.requirements_to_process,
                    batch_size=config['BATCH_SIZE']
                )
                
                logger.info(f"Generated {len(new_test_cases)} test case(s)")
                all_test_cases.extend(new_test_cases)
                test_case_stats['created'] = len(new_test_cases)
                test_case_stats['unchanged'] = len(existing_test_cases)
                test_case_stats['total'] = len(all_test_cases)
            else:
                logger.info("Step 5: Skipped (no requirements to process)")
                test_case_stats['total'] = len(existing_test_cases)
                test_case_stats['unchanged'] = len(existing_test_cases)
        
        # Step 6: Write test cases to Excel
        logger.info("Step 6: Writing test cases to Excel")
        final_stats = excel_handler.write_test_cases(
            document_path=config['DESTINATION_DOCUMENT_PATH'],
            test_cases=all_test_cases,
            mode=config['UPDATE_MODE'] if config['UPDATE_MODE'] != 'intelligent' else 'new_only'
        )
        
        logger.info(f"Test cases written: {final_stats}")
        
        # Update cache with current document content
        logger.info("Updating document cache...")
        if hasattr(cache_manager, 'set_document_content'):
            cache_manager.set_document_content(full_content, requirements)
        else:
            cache_manager.set_requirements_content(full_content)
            cache_manager.set_requirements_hash(cache_manager.compute_hash(full_content))
        logger.info("Document cached for future change detection")
        
        # Step 7: Generate report
        logger.info("Step 7: Generating report")
        
        # Calculate requirements processed based on mode
        if config['UPDATE_MODE'] == 'intelligent':
            requirements_processed = len(requirements)
        else:
            requirements_processed = len(update_plan.requirements_to_process)
        
        report = report_generator.generate_report(
            changes=changes,
            test_case_stats=test_case_stats,
            requirements_processed=requirements_processed,
            errors=errors,
            warnings=warnings
        )
        
        # Save report
        report_path = config.get_report_file_path()
        report_generator.save_report(report, report_path)
        logger.info(f"Report saved to {report_path}")
        
        logger.info("=" * 80)
        logger.info("VELORA SYNC COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
        return 0
        
    except VeloraSyncException as e:
        error_msg = f"Velora Sync error: {str(e)}"
        if logger:
            logger.error(error_msg)
        else:
            print(f"ERROR: {error_msg}", file=sys.stderr)
        
        errors.append(error_msg)
        
        # Try to generate error report
        if config and logger:
            try:
                report_generator = ReportGenerator()
                report = report_generator.generate_report(
                    changes=[],
                    test_case_stats={'created': 0, 'updated': 0, 'unchanged': 0, 'total': 0},
                    requirements_processed=0,
                    errors=errors,
                    warnings=warnings
                )
                report_path = config.get_report_file_path()
                report_generator.save_report(report, report_path)
            except:
                pass
        
        return 1
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        if logger:
            logger.error(error_msg, exc_info=True)
        else:
            print(f"ERROR: {error_msg}", file=sys.stderr)
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
