Tags: [[Tech]]

## 🚀 1. Set Up GitHub Actions Workflow

This section covers automating daily tasks using GitHub Actions with cron scheduling.

Automating daily tasks with GitHub Actions using cron scheduling.

```yaml
cron: "0 9 * * *" # Run daily at 9 AM UTC
```

Workflow steps:
- Setup Python environment
- Install required dependencies
- Check if daily run is needed
- Execute main script
- Update last run timestamp
- Commit any changes

<br>

## 🐍 2. Python Script

This section describes a Python script that uses the Gemini API to analyze and enhance files with consistent formatting.

A script that leverages the Gemini API to analyze and enhance files with consistent formatting based on provided prompts.

Key features:
- Applies formatting and styling improvements
- Excludes specified directories from processing
- Uses file hashes to detect changes
- Only processes modified files for efficiency