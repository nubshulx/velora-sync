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
            
            # Step 3: Collect requirements to generate
            logger.info("Step 3: Collecting requirements to process...")
            requirements_to_create = []
            requirements_to_update = []
            
            for rec in recommendations:
                if rec['action'] == 'create':
                    requirements_to_create.append(rec['requirement'])
                elif rec['action'] == 'update':
                    requirements_to_update.append(rec['requirement'])
                    # Remove old versions from unchanged list
                    old_tc_ids = {tc.get('Test Case ID') for tc in rec['test_cases']}
                    results['unchanged_test_cases'] = [
                        tc for tc in results['unchanged_test_cases']
                        if tc.get('Test Case ID') not in old_tc_ids
                    ]
            
            # Step 4: Generate test cases in batches (fewer API calls)
            if requirements_to_create:
                logger.info(f"Generating test cases for {len(requirements_to_create)} uncovered requirements...")
                new_tcs = self.test_case_generator.generate_from_requirements_batch(
                    requirements=requirements_to_create,
                    batch_size=5  # 5 requirements per LLM call
                )
                results['new_test_cases'].extend(new_tcs)
                logger.info(f"Created {len(new_tcs)} test cases")
            
            if requirements_to_update:
                logger.info(f"Updating test cases for {len(requirements_to_update)} changed requirements...")
                updated_tcs = self.test_case_generator.generate_from_requirements_batch(
                    requirements=requirements_to_update,
                    batch_size=5
                )
                results['updated_test_cases'].extend(updated_tcs)
                logger.info(f"Updated {len(updated_tcs)} test cases")
            
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
        Uses semantic similarity to detect duplicates with different wording
        
        Args:
            results: Results from process_requirements_intelligently
            
        Returns:
            Combined list of unique test cases
        """
        all_test_cases = []
        all_test_cases.extend(results.get('new_test_cases', []))
        all_test_cases.extend(results.get('updated_test_cases', []))
        all_test_cases.extend(results.get('unchanged_test_cases', []))
        
        # Remove duplicates using semantic similarity
        unique_test_cases = []
        duplicates_removed = 0
        
        for tc in all_test_cases:
            title = tc.get('Test Case Title', '')
            if not title:
                continue
            
            # Check if this test case is similar to any existing unique test case
            is_duplicate = False
            for existing_tc in unique_test_cases:
                existing_title = existing_tc.get('Test Case Title', '')
                if self._are_titles_similar(title, existing_title):
                    is_duplicate = True
                    logger.debug(f"Removing duplicate: '{title}' (similar to '{existing_title}')")
                    duplicates_removed += 1
                    break
            
            if not is_duplicate:
                unique_test_cases.append(tc)
        
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate test cases (semantic matching)")
        
        # Re-number test case IDs
        for i, tc in enumerate(unique_test_cases, start=1):
            tc['Test Case ID'] = f"TC-{i:03d}"
        
        return unique_test_cases
    
    def _normalize_title_for_comparison(self, title: str) -> set:
        """
        Extract significant keywords from title for semantic comparison
        
        Args:
            title: Test case title
            
        Returns:
            Set of significant keywords
        """
        import re
        
        # Common prefixes to remove (verbs that start test case titles)
        prefixes = [
            'verify', 'test', 'check', 'validate', 'ensure', 'confirm',
            'verify that', 'test that', 'check that', 'ensure that'
        ]
        
        title_lower = title.strip().lower()
        
        # Remove common prefixes
        for prefix in sorted(prefixes, key=len, reverse=True):  # Longer first
            if title_lower.startswith(prefix + ' '):
                title_lower = title_lower[len(prefix) + 1:]
                break
        
        # Remove punctuation and split into words
        words = re.findall(r'\w+', title_lower)
        
        # Common stop words to ignore
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'with', 'for', 'of', 'to', 'and', 'or', 'but', 'if',
            'then', 'else', 'when', 'where', 'why', 'how', 'all', 'each',
            'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
            'very', 'just', 'that', 'this', 'these', 'those', 'what', 'which',
            'who', 'whom', 'after', 'before', 'during', 'on', 'in', 'at', 'by'
        }
        
        # Extract significant words (not stop words, length > 2)
        significant_words = {w for w in words if w not in stop_words and len(w) > 2}
        
        return significant_words
    
    def _are_titles_similar(self, title1: str, title2: str, threshold: float = 0.6) -> bool:
        """
        Check if two titles are semantically similar using Jaccard similarity
        
        Args:
            title1: First title
            title2: Second title
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if titles are similar, False otherwise
        """
        words1 = self._normalize_title_for_comparison(title1)
        words2 = self._normalize_title_for_comparison(title2)
        
        if not words1 or not words2:
            return False
        
        # Jaccard similarity: intersection / union
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        if union == 0:
            return False
        
        similarity = intersection / union
        
        # Also check if one is a subset of the other (handles short vs long titles)
        subset_ratio = intersection / min(len(words1), len(words2)) if min(len(words1), len(words2)) > 0 else 0
        
        # Consider similar if Jaccard >= threshold OR if 80%+ of smaller set is covered
        return similarity >= threshold or subset_ratio >= 0.8

