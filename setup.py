"""
Velora Sync - Enterprise Test Case Generation Tool
Setup configuration for package installation
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="velora-sync",
    version="1.0.0",
    author="Velora Team",
    description="Automated test case generation from requirements using LLM",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/velora-sync",
    packages=find_packages(exclude=["tests*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "python-docx>=1.1.0",
        "openpyxl>=3.1.2",
        "transformers>=4.36.0",
        "torch>=2.1.0",
        "msal>=1.26.0",
        "requests>=2.31.0",
        "Office365-REST-Python-Client>=2.5.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.12.0",
            "pylint>=3.0.0",
            "mypy>=1.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "velora-sync=src.main:main",
        ],
    },
)
