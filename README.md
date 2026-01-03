# Velora Sync

**Enterprise Test Case Generation Tool**

[![GitHub Actions](https://img.shields.io/badge/CI-GitHub%20Actions-blue)](https://github.com/features/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Velora Sync is an automated CI/CD tool that generates and maintains test cases from requirement documents using Large Language Models (LLM). It runs as a GitHub Actions job, intelligently detecting requirement changes and updating test cases accordingly.

## ✨ Features

- **Multi-Provider LLM Support**: Choose from Gemini, DeepSeek, OpenAI, or Hugging Face models
- **Document Integration**: Supports local files and cloud documents
- **Intelligent Change Detection**: Uses LLM-powered analysis to detect requirement changes and update only affected test cases
- **Flexible Update Modes**: 
  - `intelligent`: LLM-powered smart analysis (recommended)
  - `new_only`: Only add new test cases (preserves manual edits)
  - `full_sync`: Update existing + add new test cases
- **Comprehensive Reporting**: Generates detailed markdown reports with statistics and change tracking
- **Cloud Storage Support**: Full integration with Google Drive. SharePoint support is available provided that the user has access to the SharePoint API.
- **Distributed Caching**: Upstash Redis support for persistent cache across CI/CD runs

## Quick Start

### Prerequisites

- Python 3.11 or higher
- GitHub repository (for CI/CD)
- LLM API access
- Optional: SharePoint or Google Drive access (for cloud documents)
- Optional: Upstash Redis (for distributed caching)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/nubshulx/velora-sync.git
   cd velora-sync
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run locally**
   ```bash
   python run.py
   ```

### GitHub Actions Setup

1. **Add repository secrets** (Settings → Secrets and variables → Actions):

   **Required:**
   - `SOURCE_DOCUMENT_PATH`: Path to requirements document (local, SharePoint URL, or Google Drive file ID)
   - `DESTINATION_DOCUMENT_PATH`: Path to test cases Excel file
   - `LLM_PROVIDER`: LLM provider (`gemini`, `deepseek`, `openai`, or `huggingface`)
   - `LLM_MODEL`: Model name (e.g., `gemini-2.0-flash`)
   - `API_TOKEN`: API key for your chosen LLM provider

   **Optional (for cloud storage):**
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: Base64 encoded Google service account JSON (for Google Drive)
   - `SHAREPOINT_TENANT_ID`, `SHAREPOINT_CLIENT_ID`, `SHAREPOINT_CLIENT_SECRET`, `SHAREPOINT_SITE_URL`

   **Optional (for distributed caching):**
   - `UPSTASH_REDIS_REST_URL`: Upstash Redis REST URL
   - `UPSTASH_REDIS_REST_TOKEN`: Upstash Redis REST token

2. **Trigger the workflow**
   - The workflow is configured in `.github/workflows/velora-sync.yml`
   - Trigger manually from the Actions tab with `workflow_dispatch`
   - Select the update mode when triggering


### Basic Configuration (.env)

```bash
# ============================================================================
# REQUIRED: DOCUMENT PATHS
# ============================================================================
SOURCE_DOCUMENT_PATH=./sample_documents/requirements.docx
DESTINATION_DOCUMENT_PATH=./sample_documents/testcases.xlsx

# ============================================================================
# REQUIRED: LLM CONFIGURATION
# ============================================================================
# Provider: 'gemini', 'deepseek', 'openai', or 'huggingface'
LLM_PROVIDER=gemini

# Model name (varies by provider):
# - Gemini: gemini-2.0-flash (FREE)
# - DeepSeek: deepseek-chat (FREE tier)
# - OpenAI: gpt-4-turbo-preview
# - Hugging Face: meta-llama/Llama-3-70b
LLM_MODEL=gemini-2.0-flash

# API key/token for your chosen provider
API_TOKEN=your_api_key_here

# ============================================================================
# OPTIONAL: PROCESSING SETTINGS
# ============================================================================
UPDATE_MODE=intelligent  # 'intelligent', 'new_only', or 'full_sync'
LOG_LEVEL=INFO
MAX_TOKENS=2000
TEMPERATURE=0.3

# ============================================================================
# OPTIONAL: UPSTASH REDIS CACHE
# ============================================================================
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=

# ============================================================================
# OPTIONAL: SHAREPOINT CONFIGURATION
# ============================================================================
# SHAREPOINT_TENANT_ID=your_tenant_id
# SHAREPOINT_CLIENT_ID=your_client_id
# SHAREPOINT_CLIENT_SECRET=your_client_secret
# SHAREPOINT_SITE_URL=https://yourcompany.sharepoint.com/sites/yoursite
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions                          │
│                   (Manual Trigger)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Velora Sync Main                         │
├─────────────────────────────────────────────────────────────┤
│  1. Read Requirements (Word) ─────────────────────┐         │
│  2. Detect Changes (Intelligent/LLM Analysis)     │         │
│  3. Generate Test Cases (Multi-Provider LLM)      │         │
│  4. Update Excel Document                         │         │
│  5. Generate Report                               │         │
└───────────────────────────────────────────────────┼─────────┘
                                                    │
          ┌─────────────────────────────────────────┼────────────────────┐
          │                                         │                    │
  ┌───────▼────────┐  ┌─────────────────┐  ┌───────▼───────┐  ┌─────────▼────────┐
  │  SharePoint    │  │  Google Drive   │  │  LLM Provider │  │  Upstash Redis   │
  │  Integration   │  │  Integration    │  │  (Multi)      │  │  Cache           │
  └────────────────┘  └─────────────────┘  └───────────────┘  └──────────────────┘
                                                    │
                                           ┌───────▼───────────┐
                                           │  Reports & Logs   │
                                           │  (Artifacts)      │
                                           └───────────────────┘
```

## 📂 Project Structure

```
velora-sync/
├── .github/
│   └── workflows/
│       └── velora-sync.yml              # GitHub Actions workflow
├── config/
│   └── config.py                        # Configuration management
├── src/
│   ├── core/
│   │   ├── change_detector.py           # Requirement change detection
│   │   ├── intelligent_orchestrator.py  # Intelligent update orchestration
│   │   ├── llm_change_analyzer.py       # LLM-powered change analysis
│   │   ├── requirement_mapper.py        # Requirement mapping logic
│   │   └── update_strategy.py           # Update mode logic
│   ├── document_readers/
│   │   ├── word_reader.py               # Word document processing
│   │   ├── excel_handler.py             # Excel operations
│   │   ├── sharepoint_client.py         # SharePoint integration
│   │   ├── google_drive_client.py       # Google Drive integration
│   │   └── cloud_downloader.py          # Cloud document downloader
│   ├── llm/
│   │   ├── model_client.py              # Multi-provider LLM client
│   │   ├── prompt_templates.py          # Prompt engineering
│   │   └── test_case_generator.py       # Test case generation
│   ├── reporting/
│   │   └── report_generator.py          # Report generation
│   ├── utils/
│   │   ├── cache.py                     # Local caching utilities
│   │   ├── redis_cache.py               # Upstash Redis cache
│   │   ├── exceptions.py                # Custom exceptions
│   │   └── logger.py                    # Logging framework
│   └── main.py                          # Main entry point
├── .env.example                         # Configuration template
├── requirements.txt                     # Python dependencies
├── run.py                               # Runner script
├── setup.py                             # Package setup
└── README.md                            # This file
```

## Usage Examples

### Local Execution

```bash
# Run with default configuration
python run.py
```

### Google Drive Documents

```bash
# In .env file - use Google Drive file IDs
SOURCE_DOCUMENT_PATH=1abc123... # Google Drive file ID for requirements.docx
DESTINATION_DOCUMENT_PATH=./local/testcases.xlsx

# Add service account JSON (base64 encoded for GitHub secrets)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

### SharePoint Documents

```bash
# In .env file
SOURCE_DOCUMENT_PATH=https://company.sharepoint.com/sites/project/Shared Documents/requirements.docx
DESTINATION_DOCUMENT_PATH=https://company.sharepoint.com/sites/project/Shared Documents/testcases.xlsx
SHAREPOINT_TENANT_ID=your-tenant-id
SHAREPOINT_CLIENT_ID=your-client-id
SHAREPOINT_CLIENT_SECRET=your-client-secret
SHAREPOINT_SITE_URL=https://company.sharepoint.com/sites/project
```

### Custom Test Case Template

```json
{
  "Test Case ID": "TC001",
  "Test Case Title": "Verify login functionality",
  "Description": "Test description",
  "Preconditions": "User account exists",
  "Test Steps": "1. Navigate\n2. Enter credentials\n3. Click login",
  "Expected Result": "User logged in successfully",
  "Priority": "High",
  "Test Type": "Functional",
  "Status": "Active"
}
```

## Reports

After each run, Velora Sync generates:

1. **Detailed Markdown Report** (`reports/report_*.md`)
   - Requirement changes detected
   - Test cases created/updated
   - Processing statistics
   - Errors and warnings

2. **GitHub Actions Summary**
   - Displayed in the Actions UI
   - Quick overview of run results

3. **Log Files** (`reports/velora_sync_*.log`)
   - Detailed execution logs
   - Debug information

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

