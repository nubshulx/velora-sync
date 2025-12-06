"""
LLM-based change analyzer for requirement documents
Uses AI to intelligently analyze and describe changes between document versions
"""

import json
from typing import List, Optional
from dataclasses import dataclass, field

from src.utils.logger import get_logger
from src.llm.model_client import ModelClient

logger = get_logger(__name__)


@dataclass
class RequirementChange:
    """Represents a single requirement change identified by LLM"""
    change_type: str  # 'added', 'modified', 'removed', 'clarified', 'restructured'
    requirement_id: Optional[str]
    description: str
    impact: str  # 'high', 'medium', 'low'
    details: str = ""


@dataclass
class ChangeAnalysis:
    """Complete analysis of changes between document versions"""
    has_changes: bool
    summary: str
    changes: List[RequirementChange] = field(default_factory=list)
    added_count: int = 0
    modified_count: int = 0
    removed_count: int = 0
    raw_response: str = ""


class LLMChangeAnalyzer:
    """Uses LLM to intelligently analyze requirement changes"""
    
    def __init__(self, model_client: ModelClient):
        """
        Initialize change analyzer with model client
        
        Args:
            model_client: LLM model client for analysis
        """
        self.model_client = model_client
    
    def analyze_changes(
        self,
        previous_content: str,
        current_content: str
    ) -> ChangeAnalysis:
        """
        Use LLM to analyze differences between document versions
        
        Args:
            previous_content: Previous version of the document
            current_content: Current version of the document
            
        Returns:
            ChangeAnalysis with detailed breakdown of changes
        """
        logger.info("Analyzing document changes using LLM...")
        
        # Quick check - if content is identical, no need to call LLM
        if previous_content.strip() == current_content.strip():
            logger.info("Documents are identical - no changes detected")
            return ChangeAnalysis(
                has_changes=False,
                summary="No changes detected between document versions."
            )
        
        try:
            # Generate analysis prompt
            prompt = self._get_analysis_prompt(previous_content, current_content)
            
            # Call LLM for analysis
            response = self.model_client.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.2  # Lower temperature for more consistent analysis
            )
            
            # Parse the response
            analysis = self._parse_analysis_response(response)
            logger.info(f"Change analysis complete: {analysis.summary[:100]}...")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze changes with LLM: {e}")
            # Return a basic analysis indicating changes were detected but couldn't be analyzed
            return ChangeAnalysis(
                has_changes=True,
                summary=f"Changes detected but detailed analysis failed: {str(e)}",
                raw_response=""
            )
    
    def _get_analysis_prompt(self, previous_content: str, current_content: str) -> str:
        """
        Generate the prompt for LLM change analysis
        
        Args:
            previous_content: Previous document content
            current_content: Current document content
            
        Returns:
            Formatted prompt string
        """
        # Truncate content if too long to avoid token limits
        max_content_length = 8000
        prev_truncated = previous_content[:max_content_length] if len(previous_content) > max_content_length else previous_content
        curr_truncated = current_content[:max_content_length] if len(current_content) > max_content_length else current_content
        
        prompt = f"""You are an expert requirements analyst. Analyze the changes between two versions of a requirements document and provide a detailed breakdown.

## PREVIOUS VERSION:
```
{prev_truncated}
```

## CURRENT VERSION:
```
{curr_truncated}
```

## TASK:
Compare these two document versions and identify all changes. For each change, determine:
1. What type of change it is (added, modified, removed, clarified, or restructured)
2. Which requirement(s) are affected
3. A clear description of what changed
4. The impact level (high, medium, low) on existing test cases

## RESPONSE FORMAT:
Respond in valid JSON format with this structure:
{{
    "summary": "Brief overall summary of changes (1-2 sentences)",
    "has_significant_changes": true/false,
    "changes": [
        {{
            "type": "added|modified|removed|clarified|restructured",
            "requirement_id": "REQ-XXX or null if not identifiable",
            "description": "What changed",
            "impact": "high|medium|low",
            "details": "Additional context about the change"
        }}
    ],
    "statistics": {{
        "added": 0,
        "modified": 0,
        "removed": 0
    }}
}}

If there are no meaningful changes (only whitespace, formatting, etc.), set has_significant_changes to false.

Respond ONLY with the JSON, no additional text."""

        return prompt
    
    def _parse_analysis_response(self, response: str) -> ChangeAnalysis:
        """
        Parse the LLM response into a ChangeAnalysis object
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Parsed ChangeAnalysis
        """
        try:
            # Try to extract JSON from the response
            # Handle cases where LLM might wrap JSON in markdown code blocks
            json_str = response.strip()
            
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            elif json_str.startswith("```"):
                json_str = json_str[3:]
            
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            
            json_str = json_str.strip()
            
            data = json.loads(json_str)
            
            # Parse changes
            changes = []
            for change_data in data.get('changes', []):
                change = RequirementChange(
                    change_type=change_data.get('type', 'modified'),
                    requirement_id=change_data.get('requirement_id'),
                    description=change_data.get('description', ''),
                    impact=change_data.get('impact', 'medium'),
                    details=change_data.get('details', '')
                )
                changes.append(change)
            
            # Get statistics
            stats = data.get('statistics', {})
            
            return ChangeAnalysis(
                has_changes=data.get('has_significant_changes', True),
                summary=data.get('summary', 'Changes detected in requirements document.'),
                changes=changes,
                added_count=stats.get('added', 0),
                modified_count=stats.get('modified', 0),
                removed_count=stats.get('removed', 0),
                raw_response=response
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Return a basic analysis with the raw response
            return ChangeAnalysis(
                has_changes=True,
                summary="Changes detected (could not parse detailed analysis)",
                raw_response=response
            )
    
    def get_change_summary_text(self, analysis: ChangeAnalysis) -> str:
        """
        Generate a human-readable summary of changes
        
        Args:
            analysis: ChangeAnalysis object
            
        Returns:
            Formatted summary text
        """
        if not analysis.has_changes:
            return "No significant changes detected in the requirements document."
        
        lines = [
            "=" * 60,
            "REQUIREMENTS CHANGE ANALYSIS",
            "=" * 60,
            "",
            f"Summary: {analysis.summary}",
            "",
            f"Statistics:",
            f"  - Added: {analysis.added_count}",
            f"  - Modified: {analysis.modified_count}",
            f"  - Removed: {analysis.removed_count}",
            "",
        ]
        
        if analysis.changes:
            lines.append("Detailed Changes:")
            lines.append("-" * 40)
            
            for i, change in enumerate(analysis.changes, 1):
                impact_marker = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(change.impact, "⚪")
                req_id = f"[{change.requirement_id}]" if change.requirement_id else ""
                
                lines.append(f"{i}. {impact_marker} {change.change_type.upper()} {req_id}")
                lines.append(f"   {change.description}")
                if change.details:
                    lines.append(f"   Details: {change.details}")
                lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
