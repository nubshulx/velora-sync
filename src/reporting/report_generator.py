"""
Report generator for Velora Sync runs
"""

from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from src.core.change_detector import Change
from src.utils.logger import get_logger
from src.utils.exceptions import ReportGenerationError

logger = get_logger(__name__)


class ReportGenerator:
    """Generates markdown reports for Velora Sync runs"""
    
    def __init__(self):
        """Initialize report generator"""
        self.start_time = datetime.now()
    
    def generate_report(
        self,
        changes: List[Change],
        test_case_stats: Dict[str, int],
        requirements_processed: int,
        errors: List[str] = None,
        warnings: List[str] = None
    ) -> str:
        """
        Generate comprehensive markdown report
        
        Args:
            changes: List of detected changes
            test_case_stats: Statistics from test case updates
            requirements_processed: Number of requirements processed
            errors: List of error messages
            warnings: List of warning messages
            
        Returns:
            Markdown report string
        """
        try:
            logger.info("Generating run report")
            
            end_time = datetime.now()
            duration = (end_time - self.start_time).total_seconds()
            
            report_parts = []
            
            # Header
            report_parts.append("# Velora Sync - Run Report")
            report_parts.append("")
            report_parts.append(f"**Run Date:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            report_parts.append(f"**Duration:** {duration:.2f} seconds")
            report_parts.append("")
            
            # Summary
            report_parts.append("## Summary")
            report_parts.append("")
            report_parts.append(f"- **Requirements Processed:** {requirements_processed}")
            report_parts.append(f"- **Test Cases Created:** {test_case_stats.get('created', 0)}")
            report_parts.append(f"- **Test Cases Updated:** {test_case_stats.get('updated', 0)}")
            report_parts.append(f"- **Test Cases Unchanged:** {test_case_stats.get('unchanged', 0)}")
            report_parts.append(f"- **Total Test Cases:** {test_case_stats.get('total', 0)}")
            report_parts.append("")
            
            # Changes detected
            if changes:
                report_parts.append("## Requirement Changes Detected")
                report_parts.append("")
                
                added = [c for c in changes if c.change_type == 'added']
                modified = [c for c in changes if c.change_type == 'modified']
                removed = [c for c in changes if c.change_type == 'removed']
                
                report_parts.append(f"- **Added:** {len(added)}")
                report_parts.append(f"- **Modified:** {len(modified)}")
                report_parts.append(f"- **Removed:** {len(removed)}")
                report_parts.append("")
                
                # Details for each change type
                if added:
                    report_parts.append("### Added Requirements")
                    report_parts.append("")
                    for change in added:
                        report_parts.append(f"- **{change.requirement_id}**: {change.diff_summary}")
                    report_parts.append("")
                
                if modified:
                    report_parts.append("### Modified Requirements")
                    report_parts.append("")
                    for change in modified:
                        report_parts.append(f"- **{change.requirement_id}**: {change.diff_summary}")
                    report_parts.append("")
                
                if removed:
                    report_parts.append("### Removed Requirements")
                    report_parts.append("")
                    for change in removed:
                        report_parts.append(f"- **{change.requirement_id}**: {change.diff_summary}")
                    report_parts.append("")
            else:
                report_parts.append("## No Changes Detected")
                report_parts.append("")
                report_parts.append("No changes were detected in the requirements document.")
                report_parts.append("")
            
            # Warnings
            if warnings:
                report_parts.append("## Warnings")
                report_parts.append("")
                for warning in warnings:
                    report_parts.append(f"> ⚠️ {warning}")
                report_parts.append("")
            
            # Errors
            if errors:
                report_parts.append("## Errors")
                report_parts.append("")
                for error in errors:
                    report_parts.append(f"> ❌ {error}")
                report_parts.append("")
            
            # Status
            if errors:
                status = "❌ **FAILED**"
                status_msg = "The run completed with errors."
            elif warnings:
                status = "⚠️ **COMPLETED WITH WARNINGS**"
                status_msg = "The run completed successfully with some warnings."
            else:
                status = "✅ **SUCCESS**"
                status_msg = "The run completed successfully."
            
            report_parts.append("## Status")
            report_parts.append("")
            report_parts.append(status)
            report_parts.append("")
            report_parts.append(status_msg)
            report_parts.append("")
            
            # Footer
            report_parts.append("---")
            report_parts.append("")
            report_parts.append("*Generated by Velora Sync - Enterprise Test Case Generation Tool*")
            
            report = "\n".join(report_parts)
            logger.info("Report generated successfully")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate report: {str(e)}")
            raise ReportGenerationError(f"Report generation failed: {str(e)}")
    
    def save_report(self, report: str, output_path: Path) -> None:
        """
        Save report to file
        
        Args:
            report: Report content
            output_path: Path to save report
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save report: {str(e)}")
            raise ReportGenerationError(f"Failed to save report: {str(e)}")
    
    def generate_github_summary(
        self,
        changes: List[Change],
        test_case_stats: Dict[str, int],
        requirements_processed: int
    ) -> str:
        """
        Generate concise summary for GitHub Actions
        
        Args:
            changes: List of changes
            test_case_stats: Test case statistics
            requirements_processed: Requirements processed count
            
        Returns:
            GitHub Actions summary markdown
        """
        summary_parts = []
        
        summary_parts.append("## Velora Sync Run Summary")
        summary_parts.append("")
        summary_parts.append(f"Processed {requirements_processed} requirement(s)")
        summary_parts.append(f"Created {test_case_stats.get('created', 0)} new test case(s)")
        summary_parts.append(f"Updated {test_case_stats.get('updated', 0)} test case(s)")
        summary_parts.append(f"Total test cases: {test_case_stats.get('total', 0)}")
        
        if changes:
            summary_parts.append("")
            summary_parts.append(f"**Changes:** {len(changes)} requirement change(s) detected")
        
        return "\n".join(summary_parts)
