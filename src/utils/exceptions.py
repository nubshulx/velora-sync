"""
Custom exception classes for Velora Sync
"""


class VeloraSyncException(Exception):
    """Base exception class for all Velora Sync errors"""
    pass


class ConfigurationError(VeloraSyncException):
    """Raised when configuration is invalid or missing"""
    pass


class DocumentReadError(VeloraSyncException):
    """Raised when document reading fails"""
    pass


class DocumentWriteError(VeloraSyncException):
    """Raised when document writing fails"""
    pass


class SharePointAuthError(VeloraSyncException):
    """Raised when SharePoint authentication fails"""
    pass


class SharePointOperationError(VeloraSyncException):
    """Raised when SharePoint operations fail"""
    pass


class LLMGenerationError(VeloraSyncException):
    """Raised when LLM test case generation fails"""
    pass


class ModelLoadError(VeloraSyncException):
    """Raised when LLM model loading fails"""
    pass


class ChangeDetectionError(VeloraSyncException):
    """Raised when change detection fails"""
    pass


class ReportGenerationError(VeloraSyncException):
    """Raised when report generation fails"""
    pass
