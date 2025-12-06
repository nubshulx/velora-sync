# Velora Sync

**Enterprise Test Case Generation Tool**

[![GitHub Actions](https://img.shields.io/badge/CI-GitHub%20Actions-blue)](https://github.com/features/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Velora Sync is an automated CI/CD tool that generates and maintains test cases from requirement documents using Large Language Models (LLM). It runs as a GitHub Actions job, intelligently detecting requirement changes and updating test cases accordingly.

## ✨ Features

- **🤖 AI-Powered Test Generation**: Uses Hugging Face LLM models (default: google/flan-t5-large) to generate comprehensive test cases
- **📄 Document Integration**: Supports both local and SharePoint Word/Excel documents
- **🔍 Intelligent Change Detection**: Automatically detects requirement changes and updates only affected test cases
- **⚙️ Flexible Update Modes**: 
  - `new_only`: Only add new test cases (preserves manual edits)
  - `full_sync`: Update existing + add new test cases
- **📊 Comprehensive Reporting**: Generates detailed markdown reports with statistics and change tracking
- **🔄 Automated Scheduling**: Runs twice daily via GitHub Actions cron jobs
- **☁️ SharePoint Support**: Full integration with Microsoft SharePoint via Graph API
- **📝 Template-Based**: Customizable test case templates via JSON configuration

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- GitHub repository (for CI/CD)
- Optional: SharePoint access (for cloud documents)
- Optional: Hugging Face API token (for gated models)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/velora-sync.git
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
   python src/main.py
   ```

### GitHub Actions Setup

1. **Add repository secrets** (Settings → Secrets and variables → Actions):
   - `SOURCE_DOCUMENT_PATH`: Path to requirements document
   - `DESTINATION_DOCUMENT_PATH`: Path to test cases Excel file
   - `HUGGINGFACE_API_TOKEN`: Your Hugging Face API token (optional)
   - For SharePoint:
     - `SHAREPOINT_TENANT_ID`
     - `SHAREPOINT_CLIENT_ID`
     - `SHAREPOINT_CLIENT_SECRET`
     - `SHAREPOINT_SITE_URL`

2. **Enable GitHub Actions**
   - The workflow is already configured in `.github/workflows/velora-sync.yml`
   - It runs automatically twice daily (9 AM and 9 PM UTC)
   - You can also trigger it manually from the Actions tab

## 📖 Configuration

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for detailed configuration options.

### Basic Configuration (.env)

```bash
# Source document (requirements)
SOURCE_DOCUMENT_PATH=/path/to/requirements.docx

# Destination document (test cases)
DESTINATION_DOCUMENT_PATH=/path/to/testcases.xlsx

# LLM Model
LLM_MODEL_NAME=google/flan-t5-large

# Update mode
UPDATE_MODE=new_only  # or full_sync

# Test case template (JSON)
TEST_CASE_TEMPLATE={"Test Case ID": "TC001", "Title": "Sample", ...}
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions                          │
│                  (Cron: 9 AM & 9 PM UTC)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Velora Sync Main                         │
├─────────────────────────────────────────────────────────────┤
│  1. Read Requirements (Word) ─────────────────────┐         │
│  2. Detect Changes (Diff Algorithm)               │         │
│  3. Generate Test Cases (LLM)                     │         │
│  4. Update Excel Document                         │         │
│  5. Generate Report                               │         │
└───────────────────────────────────────────────────┼─────────┘
                                                    │
                    ┌───────────────────────────────┼─────────┐
                    │                               │         │
            ┌───────▼────────┐            ┌────────▼──────┐  │
            │  SharePoint    │            │  LLM Model    │  │
            │  Integration   │            │  (Flan-T5)    │  │
            └────────────────┘            └───────────────┘  │
                                                             │
                                          ┌──────────────────▼┐
                                          │  Reports & Logs   │
                                          │  (Artifacts)      │
                                          └───────────────────┘
```

## 📂 Project Structure

```
velora-sync/
├── .github/
│   └── workflows/
│       └── velora-sync.yml          # GitHub Actions workflow
├── config/
│   └── config.py                    # Configuration management
├── src/
│   ├── core/
│   │   ├── change_detector.py       # Requirement change detection
│   │   └── update_strategy.py       # Update mode logic
│   ├── document_readers/
│   │   ├── word_reader.py           # Word document processing
│   │   ├── excel_handler.py         # Excel operations
│   │   └── sharepoint_client.py     # SharePoint integration
│   ├── llm/
│   │   ├── model_client.py          # LLM model client
│   │   ├── prompt_templates.py      # Prompt engineering
│   │   └── test_case_generator.py   # Test case generation
│   ├── reporting/
│   │   └── report_generator.py      # Report generation
│   ├── utils/
│   │   ├── cache.py                 # Caching utilities
│   │   ├── exceptions.py            # Custom exceptions
│   │   └── logger.py                # Logging framework
│   └── main.py                      # Main entry point
├── tests/                           # Test files
├── .env.example                     # Configuration template
├── requirements.txt                 # Python dependencies
├── setup.py                         # Package setup
└── README.md                        # This file
```

## 🔧 Usage Examples

### Local Execution

```bash
# Run with default configuration
python src/main.py

# View logs
cat reports/velora_sync_*.log

# View report
cat reports/report_*.md
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
  "Requirement ID": "REQ001",
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

## 📊 Reports

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

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Hugging Face for LLM models
- Microsoft Graph API for SharePoint integration
- GitHub Actions for CI/CD automation

## 📞 Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the [Configuration Guide](docs/CONFIGURATION.md)
- Review the generated reports for error details

---

**Built with ❤️ for QA teams everywhere**
