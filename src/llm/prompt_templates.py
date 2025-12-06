"""
Prompt templates for LLM test case generation
"""

from typing import Dict, List


class PromptTemplates:
    """Collection of prompt templates for LLM interactions"""
    
    @staticmethod
    def get_test_case_generation_prompt(
        requirement: str,
        template: Dict[str, str],
        requirement_id: str = ""
    ) -> str:
        """
        Generate prompt for test case creation
        
        Args:
            requirement: Requirement text
            template: Test case template dictionary
            requirement_id: Optional requirement ID
            
        Returns:
            Formatted prompt string
        """
        # Extract template fields (excluding sample values)
        fields = list(template.keys())
        
        prompt = f"""You are a senior QA engineer creating comprehensive, detailed test cases.

REQUIREMENT TO TEST:
{requirement}

YOUR TASK:
Generate 3-5 UNIQUE test cases. Each must test a DIFFERENT scenario (positive, negative, edge case, boundary).

STRICT OUTPUT FORMAT:
- Separate each test case with exactly: ---TEST_CASE---
- Each field on its OWN LINE
- NO markdown formatting (no ** or #)

FIELDS TO INCLUDE FOR EACH TEST CASE:
{chr(10).join(f"{field}: <value>" for field in fields)}

CRITICAL REQUIREMENTS FOR TEST STEPS:

Each test case MUST have 5-8 DETAILED steps. Write steps like this example:

Test Steps: 1. Open web browser and navigate to the application URL
2. Wait for the login page to fully load
3. Locate the username input field
4. Enter the test username 'testuser@company.com'
5. Locate the password input field
6. Enter the test password 'TestPass123!'
7. Click the 'Sign In' button
8. Verify the dashboard page loads successfully

RULES FOR TEST STEPS:
- Each step on a NEW LINE starting with the step number
- Be SPECIFIC: include actual field names, button text, URLs, test data
- Include verification/assertion steps
- Steps should be executable by a manual tester

RULES FOR UNIQUE TEST CASES:
- Each test case MUST cover a DIFFERENT scenario
- DO NOT repeat the same test with minor variations
- Include: 1 positive/happy path, 1-2 negative cases, 1-2 edge cases

WRONG (duplicate test cases):
- TC1: Test login with valid credentials
- TC2: Test login with correct username and password  <-- This is the SAME as TC1!

CORRECT (unique test cases):
- TC1: Verify successful login with valid credentials
- TC2: Verify error message with invalid password
- TC3: Verify account lockout after 5 failed attempts
- TC4: Verify "Remember Me" checkbox functionality

NOW GENERATE THE TEST CASES:
"""
        return prompt
    
    @staticmethod
    def get_batch_generation_prompt(
        requirements: List[Dict[str, str]],
        template: Dict[str, str]
    ) -> str:
        """
        Generate prompt for batch test case creation
        
        Args:
            requirements: List of requirement dictionaries
            template: Test case template
            
        Returns:
            Formatted prompt string
        """
        fields = list(template.keys())
        
        # Format requirements
        req_text = "\n\n".join([
            f"REQUIREMENT {i+1} (ID: {req['id']}):\n{req['content']}"
            for i, req in enumerate(requirements)
        ])
        
        prompt = f"""You are a QA expert generating test cases from multiple software requirements.

REQUIREMENTS:
{req_text}

TASK:
Generate comprehensive test cases for ALL the above requirements.

OUTPUT FORMAT:
For each test case, provide:
{chr(10).join(f"- {field}: <value>" for field in fields)}

Separate each test case with "---TEST_CASE---".

GUIDELINES:
1. Generate 3-5 test cases per requirement
2. Cover positive, negative, and edge cases
3. Be specific in test steps and expected results
4. Reference the correct requirement ID for each test case
5. Ensure test case IDs are unique and sequential

TEST CASES:
"""
        return prompt
    
    @staticmethod
    def get_requirement_analysis_prompt(requirement: str) -> str:
        """
        Generate prompt for requirement analysis
        
        Args:
            requirement: Requirement text
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""Analyze the following software requirement and extract key testable aspects.

REQUIREMENT:
{requirement}

TASK:
Identify and list:
1. Main functionality to be tested
2. Input parameters and their constraints
3. Expected outputs and behaviors
4. Edge cases and boundary conditions
5. Potential error scenarios

Provide a concise analysis focusing on testable aspects.

ANALYSIS:
"""
        return prompt
    
    @staticmethod
    def get_change_detection_prompt(
        old_requirement: str,
        new_requirement: str
    ) -> str:
        """
        Generate prompt for detecting requirement changes
        
        Args:
            old_requirement: Previous requirement text
            new_requirement: New requirement text
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""Compare the following two versions of a software requirement and identify changes.

OLD VERSION:
{old_requirement}

NEW VERSION:
{new_requirement}

TASK:
Analyze the changes and categorize them as:
1. ADDED: New functionality or details added
2. MODIFIED: Existing functionality changed
3. REMOVED: Functionality or details removed
4. CLARIFIED: Wording improved without functional change

Provide a summary of changes and their impact on testing.

CHANGE ANALYSIS:
"""
        return prompt
    
    @staticmethod
    def get_test_case_update_prompt(
        requirement_change: str,
        existing_test_cases: List[Dict[str, str]],
        template: Dict[str, str]
    ) -> str:
        """
        Generate prompt for updating test cases based on requirement changes
        
        Args:
            requirement_change: Description of requirement changes
            existing_test_cases: Current test cases
            template: Test case template
            
        Returns:
            Formatted prompt string
        """
        fields = list(template.keys())
        
        # Format existing test cases
        tc_text = "\n\n".join([
            f"TEST CASE {i+1}:\n" + "\n".join([
                f"- {k}: {v}" for k, v in tc.items()
                if k in fields
            ])
            for i, tc in enumerate(existing_test_cases)
        ])
        
        prompt = f"""You are a QA expert updating test cases based on requirement changes.

REQUIREMENT CHANGES:
{requirement_change}

EXISTING TEST CASES:
{tc_text}

TASK:
Based on the requirement changes:
1. Identify which existing test cases need updates
2. Generate updated versions of affected test cases
3. Create new test cases for new functionality
4. Mark obsolete test cases

OUTPUT FORMAT:
For each test case (updated or new), provide:
{chr(10).join(f"- {field}: <value>" for field in fields)}

Separate each test case with "---TEST_CASE---".
Prefix with "UPDATED:" or "NEW:" to indicate the type.

UPDATED/NEW TEST CASES:
"""
        return prompt
