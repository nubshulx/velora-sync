"""
Enhanced orchestrator for intelligent requirement mapping workflow
"""

from typing import List, Dict, Any

from src.llm.model_client import ModelClient
from src.llm.test_case_generator import TestCaseGenerator
from src.core.requirement_mapper import RequirementMapper
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IntelligentTestCaseOrchestrator:
    """
    Orchestrates intelligent test case generation with requirement mapping
    Prevents requirement drift in unstructured documents
    """
    
    def __init__(
        self,
        model_client: ModelClient,
        test_case_generator: TestCaseGenerator
    ):
        """
        Initialize orchestrator
        
        Args:
            model_client: LLM model client
            test_case_generator: Test case generator
        """
        self.model_client = model_client
        self.test_case_generator = test_case_generator
        self.requirement_mapper = RequirementMapper(model_client)
    
    def process_requirements_intelligently(
        self,
        requirement_sections: List[Dict[str, str]],
        existing_test_cases: List[Dict[str, Any]],
        mode: str = 'intelligent'
    ) -> Dict[str, Any]:
        """
        Process requirements with intelligent mapping to existing test cases
        
        Args:
            requirement_sections: List of requirement dictionaries
            existing_test_cases: List of existing test cases
            mode: Processing mode ('intelligent', 'new_only', 'full_sync')
            
        Returns:
            Processing results with new/updated test cases and statistics
        """
        logger.info(f"Processing {len(requirement_sections)} requirements in {mode} mode")
        
        results = {
            'new_test_cases': [],
            'updated_test_cases': [],
            'unchanged_test_cases': existing_test_cases.copy(),
            'statistics': {},
            'mapping_analysis': None
        }
        
        if mode == 'intelligent':
            # Step 1: Map requirements to existing test cases
            logger.info("Step 1: Analyzing requirement coverage...")
            mapping_results = self.requirement_mapper.map_requirements_to_test_cases(
                requirement_sections=requirement_sections,
                existing_test_cases=existing_test_cases
            )
            results['mapping_analysis'] = mapping_results
            
            # Step 2: Generate recommendations
            logger.info("Step 2: Generating recommendations...")
            recommendations = self.requirement_mapper.generate_update_recommendations(
                mapping_results
            )
            
            # Step 3: Execute recommendations
            logger.info("Step 3: Executing recommendations...")
            for rec in recommendations:
                if rec['action'] == 'create':
                    # Generate new test cases for uncovered requirements
                    new_tcs = self.test_case_generator.generate_from_requirement(
                        requirement=rec['requirement']['content'],
                        requirement_id=rec['requirement']['id']
                    )
                    results['new_test_cases'].extend(new_tcs)
                    logger.info(f"Created {len(new_tcs)} test cases for {rec['requirement']['id']}")
                
                elif rec['action'] == 'update':
                    # Update existing test cases based on requirement changes
                    updated_tcs = self.test_case_generator.generate_from_requirement(
                        requirement=rec['requirement']['content'],
                        requirement_id=rec['requirement']['id']
                    )
                    results['updated_test_cases'].extend(updated_tcs)
                    
                    # Remove old versions from unchanged list
                    old_tc_ids = {tc.get('Test Case ID') for tc in rec['test_cases']}
                    results['unchanged_test_cases'] = [
                        tc for tc in results['unchanged_test_cases']
                        if tc.get('Test Case ID') not in old_tc_ids
                    ]
                    logger.info(f"Updated test cases for {rec['requirement']['id']}")
            
            # Compile statistics
            results['statistics'] = {
                'requirements_processed': len(requirement_sections),
                'new_test_cases_created': len(results['new_test_cases']),
                'test_cases_updated': len(results['updated_test_cases']),
                'test_cases_unchanged': len(results['unchanged_test_cases']),
                'coverage_complete': mapping_results['statistics']['fully_covered'],
                'coverage_partial': mapping_results['statistics']['partially_covered'],
                'coverage_none': mapping_results['statistics']['not_covered'],
                'orphaned_test_cases': mapping_results['statistics']['orphaned_test_cases']
            }
        
        elif mode == 'new_only':
            # Traditional new_only mode (for backward compatibility)
            for req in requirement_sections:
                new_tcs = self.test_case_generator.generate_from_requirement(
                    requirement=req['content'],
                    requirement_id=req['id']
                )
                results['new_test_cases'].extend(new_tcs)
            
            results['statistics'] = {
                'requirements_processed': len(requirement_sections),
                'new_test_cases_created': len(results['new_test_cases']),
                'test_cases_unchanged': len(existing_test_cases)
            }
        
        elif mode == 'full_sync':
            # Traditional full_sync mode (for backward compatibility)
            for req in requirement_sections:
                new_tcs = self.test_case_generator.generate_from_requirement(
                    requirement=req['content'],
                    requirement_id=req['id']
                )
                results['new_test_cases'].extend(new_tcs)
            
            results['statistics'] = {
                'requirements_processed': len(requirement_sections),
                'new_test_cases_created': len(results['new_test_cases'])
            }
        
        logger.info(f"Processing complete: {results['statistics']}")
        return results
    
    def get_all_test_cases(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Combine all test cases from processing results, removing duplicates
        
        Args:
            results: Results from process_requirements_intelligently
            
        Returns:
            Combined list of unique test cases
        """
        all_test_cases = []
        all_test_cases.extend(results.get('new_test_cases', []))
        all_test_cases.extend(results.get('updated_test_cases', []))
        all_test_cases.extend(results.get('unchanged_test_cases', []))
        
        # Remove duplicates based on Test Case Title
        seen_titles = set()
        unique_test_cases = []
        for tc in all_test_cases:
            title = tc.get('Test Case Title', '').strip().lower()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_test_cases.append(tc)
            elif title:
                logger.debug(f"Removing duplicate test case: {tc.get('Test Case Title')}")
        
        if len(unique_test_cases) < len(all_test_cases):
            logger.info(f"Removed {len(all_test_cases) - len(unique_test_cases)} duplicate test cases")
        
        # Re-number test case IDs
        for i, tc in enumerate(unique_test_cases, start=1):
            tc['Test Case ID'] = f"TC-{i:03d}"
        
        return unique_test_cases
