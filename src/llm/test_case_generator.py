"""
Test case generator using LLM
"""

from typing import List, Dict, Any
import re

from src.llm.model_client import ModelClient
from src.llm.prompt_templates import PromptTemplates
from src.utils.exceptions import LLMGenerationError
from src.utils.logger import get_logger, log_execution_time

logger = get_logger(__name__)


class TestCaseGenerator:
    """Generator for test cases using LLM"""
    
    def __init__(
        self,
        model_client: ModelClient,
        template: Dict[str, str],
        max_tokens: int = 512,
        temperature: float = 0.3
    ):
        """
        Initialize test case generator
        
        Args:
            model_client: LLM model client
            template: Test case template dictionary
            max_tokens: Maximum tokens for generation
            temperature: Sampling temperature
        """
        self.model_client = model_client
        self.template = template
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.prompt_templates = PromptTemplates()
        self.global_tc_counter = 0  # Global counter for unique test case IDs
    
    @log_execution_time(logger)
    def generate_from_requirement(
        self,
        requirement: str,
        requirement_id: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Generate test cases from a single requirement
        
        Args:
            requirement: Requirement text
            requirement_id: Optional requirement ID
            
        Returns:
            List of test case dictionaries
            
        Raises:
            LLMGenerationError: If generation fails
        """
        try:
            logger.info(f"Generating test cases for requirement: {requirement_id}")
            
            # Create prompt
            prompt = self.prompt_templates.get_test_case_generation_prompt(
                requirement=requirement,
                template=self.template,
                requirement_id=requirement_id
            )
            
            # Generate test cases
            generated_text = self.model_client.generate(
                prompt=prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Parse generated test cases
            test_cases = self._parse_test_cases(generated_text, requirement_id)
            
            logger.info(f"Generated {len(test_cases)} test cases")
            return test_cases
            
        except Exception as e:
            logger.error(f"Failed to generate test cases: {str(e)}")
            raise LLMGenerationError(f"Test case generation failed: {str(e)}")
    
    @log_execution_time(logger)
    def generate_from_requirements_batch(
        self,
        requirements: List[Dict[str, str]],
        batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate test cases from multiple requirements using TRUE batching
        (combines multiple requirements into single LLM calls)
        
        Args:
            requirements: List of requirement dictionaries with 'id' and 'content'
            batch_size: Number of requirements to process together in ONE LLM call
            
        Returns:
            List of all generated test cases
        """
        try:
            logger.info(f"Generating test cases for {len(requirements)} requirements (batch_size={batch_size})")
            
            all_test_cases = []
            
            # Process in true batches - multiple requirements per LLM call
            for i in range(0, len(requirements), batch_size):
                batch = requirements[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(requirements) + batch_size - 1) // batch_size
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} requirements)")
                
                # Use batch prompt for TRUE batching
                prompt = self.prompt_templates.get_batch_generation_prompt(
                    requirements=batch,
                    template=self.template
                )
                
                # Single LLM call for entire batch
                generated_text = self.model_client.generate(
                    prompt=prompt,
                    max_tokens=self.max_tokens * len(batch),  # Scale tokens by batch size
                    temperature=self.temperature
                )
                
                # Parse all test cases from batch response
                batch_test_cases = self._parse_test_cases(generated_text, batch[0]['id'])
                all_test_cases.extend(batch_test_cases)
                logger.info(f"Batch {batch_num} generated {len(batch_test_cases)} test cases")
            
            logger.info(f"Generated total of {len(all_test_cases)} test cases before deduplication")
            
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
            
            # Re-number test case IDs after deduplication
            self.global_tc_counter = 0
            for tc in unique_test_cases:
                self.global_tc_counter += 1
                tc['Test Case ID'] = f"TC-{self.global_tc_counter:03d}"
            
            logger.info(f"Final count: {len(unique_test_cases)} unique test cases")
            return unique_test_cases
            
        except Exception as e:
            logger.error(f"Batch generation failed: {str(e)}")
            raise LLMGenerationError(f"Batch generation failed: {str(e)}")
    
    def _parse_test_cases(
        self,
        generated_text: str,
        requirement_id: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Parse generated text into structured test cases
        
        Args:
            generated_text: LLM generated text
            requirement_id: Requirement ID for reference
            
        Returns:
            List of test case dictionaries
        """
        test_cases = []
        
        # Split by test case separator
        tc_blocks = re.split(r'---TEST_CASE---', generated_text)
        
        tc_counter = 1
        for block in tc_blocks:
            block = block.strip()
            if not block:
                continue
            
            # Parse test case fields
            test_case = self._parse_test_case_block(block, requirement_id, tc_counter)
            
            if test_case:
                test_cases.append(test_case)
                tc_counter += 1
        
        # If no separators found, try to parse as single test case
        if not test_cases and generated_text.strip():
            test_case = self._parse_test_case_block(generated_text, requirement_id, 1)
            if test_case:
                test_cases.append(test_case)
        
        return test_cases
    
    def _parse_test_case_block(
        self,
        block: str,
        requirement_id: str,
        counter: int
    ) -> Dict[str, Any]:
        """
        Parse a single test case block
        
        Args:
            block: Text block containing test case
            requirement_id: Requirement ID
            counter: Test case counter
            
        Returns:
            Test case dictionary or None if parsing fails
        """
        test_case = {}
        
        # Clean up the block - remove markdown bold formatting
        block = block.replace('**', '')
        
        # Get all field names from template
        fields = list(self.template.keys())
        
        # Find positions of all fields in the block
        field_positions = []
        for field in fields:
            # Pattern to find "Field:" at start of line or after newline
            pattern = rf'(?:^|\n)\s*-?\s*({re.escape(field)})\s*:'
            for match in re.finditer(pattern, block, re.IGNORECASE | re.MULTILINE):
                field_positions.append({
                    'field': field,
                    'start': match.start(),
                    'value_start': match.end()
                })
        
        # Sort by position in text
        field_positions.sort(key=lambda x: x['start'])
        
        # Extract values between field positions
        for i, fp in enumerate(field_positions):
            field = fp['field']
            value_start = fp['value_start']
            
            # Value ends at the next field or end of block
            if i + 1 < len(field_positions):
                value_end = field_positions[i + 1]['start']
            else:
                value_end = len(block)
            
            # Extract and clean the value
            value = block[value_start:value_end].strip()
            
            # Remove trailing separators or markers
            value = re.sub(r'\n*---TEST_CASE---.*$', '', value, flags=re.DOTALL)
            value = value.strip()
            
            if value:
                test_case[field] = value
        
        # If we couldn't extract enough fields, return None
        if len(test_case) < len(self.template) // 2:
            logger.warning(f"Could not parse test case block sufficiently. Extracted {len(test_case)} of {len(self.template)} fields")
            logger.debug(f"Block preview: {block[:200]}...")
            return None
        
        # Fill in missing fields with defaults
        for field, default_value in self.template.items():
            if field not in test_case:
                test_case[field] = default_value
        
        # ALWAYS use global counter for unique test case IDs (ignore LLM output)
        if 'Test Case ID' in test_case:
            self.global_tc_counter += 1
            test_case['Test Case ID'] = f"TC-{self.global_tc_counter:03d}"
        
        return test_case
    
    def update_test_cases(
        self,
        requirement_change: str,
        existing_test_cases: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Update existing test cases based on requirement changes
        
        Args:
            requirement_change: Description of changes
            existing_test_cases: Current test cases
            
        Returns:
            Updated test cases
        """
        try:
            logger.info(f"Updating {len(existing_test_cases)} test cases based on changes")
            
            # Create prompt for updates
            prompt = self.prompt_templates.get_test_case_update_prompt(
                requirement_change=requirement_change,
                existing_test_cases=existing_test_cases,
                template=self.template
            )
            
            # Generate updates
            generated_text = self.model_client.generate(
                prompt=prompt,
                max_tokens=self.max_tokens * 2,  # More tokens for updates
                temperature=self.temperature
            )
            
            # Parse updated test cases
            updated_cases = self._parse_test_cases(generated_text)
            
            logger.info(f"Generated {len(updated_cases)} updated test cases")
            return updated_cases
            
        except Exception as e:
            logger.error(f"Failed to update test cases: {str(e)}")
            raise LLMGenerationError(f"Test case update failed: {str(e)}")
