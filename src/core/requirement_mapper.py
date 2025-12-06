"""
Intelligent requirement-to-test-case mapper using LLM
Solves the "requirement drift" problem for unstructured documents
"""

from typing import List, Dict, Any, Tuple
import json

from src.llm.model_client import ModelClient
from src.utils.logger import get_logger, log_execution_time

logger = get_logger(__name__)


class RequirementMapper:
    """Maps requirements to existing test cases using LLM intelligence"""
    
    def __init__(self, model_client: ModelClient):
        """
        Initialize requirement mapper
        
        Args:
            model_client: LLM model client
        """
        self.model_client = model_client
    
    @log_execution_time(logger)
    def map_requirements_to_test_cases(
        self,
        requirement_sections: List[Dict[str, str]],
        existing_test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Intelligently map requirement sections to existing test cases
        
        Args:
            requirement_sections: List of requirement dictionaries
            existing_test_cases: List of existing test case dictionaries
            
        Returns:
            Mapping result with coverage analysis and recommendations
        """
        logger.info(f"Mapping {len(requirement_sections)} requirements to {len(existing_test_cases)} test cases")
        
        mapping_results = {
            'mappings': [],  # List of {requirement, matched_test_cases, coverage_status}
            'new_requirements': [],  # Requirements with no test cases
            'outdated_test_cases': [],  # Test cases that need updates
            'orphaned_test_cases': [],  # Test cases with no matching requirement
            'statistics': {}
        }
        
        # Process each requirement section
        for req_section in requirement_sections:
            mapping = self._analyze_requirement_coverage(
                requirement=req_section,
                existing_test_cases=existing_test_cases
            )
            mapping_results['mappings'].append(mapping)
            
            # Categorize based on coverage
            if mapping['coverage_status'] == 'none':
                mapping_results['new_requirements'].append(req_section)
            elif mapping['coverage_status'] == 'partial':
                mapping_results['new_requirements'].append(req_section)
            elif mapping['coverage_status'] == 'outdated':
                mapping_results['outdated_test_cases'].extend(mapping['matched_test_cases'])
        
        # Find orphaned test cases
        all_matched_ids = set()
        for mapping in mapping_results['mappings']:
            for tc in mapping['matched_test_cases']:
                all_matched_ids.add(tc.get('Test Case ID', ''))
        
        for tc in existing_test_cases:
            tc_id = tc.get('Test Case ID', '')
            if tc_id and tc_id not in all_matched_ids:
                mapping_results['orphaned_test_cases'].append(tc)
        
        # Calculate statistics
        mapping_results['statistics'] = {
            'total_requirements': len(requirement_sections),
            'fully_covered': sum(1 for m in mapping_results['mappings'] if m['coverage_status'] == 'complete'),
            'partially_covered': sum(1 for m in mapping_results['mappings'] if m['coverage_status'] == 'partial'),
            'not_covered': sum(1 for m in mapping_results['mappings'] if m['coverage_status'] == 'none'),
            'outdated': sum(1 for m in mapping_results['mappings'] if m['coverage_status'] == 'outdated'),
            'orphaned_test_cases': len(mapping_results['orphaned_test_cases'])
        }
        
        logger.info(f"Mapping complete: {mapping_results['statistics']}")
        return mapping_results
    
    def _analyze_requirement_coverage(
        self,
        requirement: Dict[str, str],
        existing_test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze how well a requirement is covered by existing test cases
        
        Args:
            requirement: Requirement dictionary
            existing_test_cases: List of test cases
            
        Returns:
            Coverage analysis result
        """
        # Create prompt for LLM analysis
        prompt = self._create_coverage_analysis_prompt(requirement, existing_test_cases)
        
        # Get LLM analysis
        try:
            response = self.model_client.generate(
                prompt=prompt,
                max_tokens=800,
                temperature=0.2  # Lower temperature for more deterministic analysis
            )
            
            # Parse LLM response
            analysis = self._parse_coverage_response(response)
            
            # Match test cases based on LLM analysis
            matched_test_cases = []
            for tc_id in analysis.get('matched_test_case_ids', []):
                for tc in existing_test_cases:
                    if tc.get('Test Case ID', '') == tc_id:
                        matched_test_cases.append(tc)
                        break
            
            return {
                'requirement': requirement,
                'matched_test_cases': matched_test_cases,
                'coverage_status': analysis.get('coverage_status', 'unknown'),
                'coverage_percentage': analysis.get('coverage_percentage', 0),
                'missing_scenarios': analysis.get('missing_scenarios', []),
                'update_needed': analysis.get('update_needed', False),
                'update_reason': analysis.get('update_reason', '')
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze coverage: {str(e)}")
            # Fallback: no coverage
            return {
                'requirement': requirement,
                'matched_test_cases': [],
                'coverage_status': 'none',
                'coverage_percentage': 0,
                'missing_scenarios': [],
                'update_needed': False,
                'update_reason': ''
            }
    
    def _create_coverage_analysis_prompt(
        self,
        requirement: Dict[str, str],
        existing_test_cases: List[Dict[str, Any]]
    ) -> str:
        """Create prompt for coverage analysis"""
        
        # Format test cases
        tc_summary = "\n".join([
            f"- {tc.get('Test Case ID', 'N/A')}: {tc.get('Test Case Title', tc.get('Title', 'N/A'))}"
            for tc in existing_test_cases[:50]  # Limit to avoid token overflow
        ])
        
        if len(existing_test_cases) > 50:
            tc_summary += f"\n... and {len(existing_test_cases) - 50} more test cases"
        
        prompt = f"""You are a QA expert analyzing requirement coverage.

REQUIREMENT:
ID: {requirement.get('id', 'N/A')}
Title: {requirement.get('title', 'N/A')}
Content: {requirement.get('content', 'N/A')}

EXISTING TEST CASES:
{tc_summary if tc_summary else 'No existing test cases'}

TASK:
Analyze if the existing test cases adequately cover this requirement.

Provide your analysis in the following JSON format:
{{
  "coverage_status": "complete|partial|none|outdated",
  "coverage_percentage": 0-100,
  "matched_test_case_ids": ["TC-001", "TC-002"],
  "missing_scenarios": ["scenario 1", "scenario 2"],
  "update_needed": true|false,
  "update_reason": "explanation if update needed"
}}

COVERAGE STATUS DEFINITIONS:
- "complete": All aspects of requirement are tested, test cases are current
- "partial": Some aspects tested, but missing scenarios exist
- "none": No test cases match this requirement
- "outdated": Test cases exist but don't match current requirement wording

ANALYSIS (JSON only):
"""
        return prompt
    
    def _parse_coverage_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM coverage analysis response"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(0))
                return analysis
            else:
                logger.warning("Could not parse JSON from LLM response")
                return {
                    'coverage_status': 'unknown',
                    'coverage_percentage': 0,
                    'matched_test_case_ids': [],
                    'missing_scenarios': [],
                    'update_needed': False,
                    'update_reason': ''
                }
        except Exception as e:
            logger.error(f"Failed to parse coverage response: {str(e)}")
            return {
                'coverage_status': 'unknown',
                'coverage_percentage': 0,
                'matched_test_case_ids': [],
                'missing_scenarios': [],
                'update_needed': False,
                'update_reason': ''
            }
    
    def generate_update_recommendations(
        self,
        mapping_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate actionable recommendations based on mapping
        
        Args:
            mapping_results: Results from map_requirements_to_test_cases
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Recommend creating test cases for new requirements
        for req in mapping_results['new_requirements']:
            recommendations.append({
                'action': 'create',
                'requirement': req,
                'reason': 'No test cases found for this requirement',
                'priority': 'high'
            })
        
        # Recommend updating outdated test cases
        for mapping in mapping_results['mappings']:
            if mapping['update_needed']:
                recommendations.append({
                    'action': 'update',
                    'requirement': mapping['requirement'],
                    'test_cases': mapping['matched_test_cases'],
                    'reason': mapping['update_reason'],
                    'priority': 'medium'
                })
        
        # Recommend reviewing orphaned test cases
        if mapping_results['orphaned_test_cases']:
            recommendations.append({
                'action': 'review',
                'test_cases': mapping_results['orphaned_test_cases'],
                'reason': 'Test cases found with no matching requirement',
                'priority': 'low'
            })
        
        logger.info(f"Generated {len(recommendations)} recommendations")
        return recommendations
