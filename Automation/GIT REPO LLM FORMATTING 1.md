```markdown
Tags: [[Tech]]

## 🚀 1. Set Up GitHub Actions Workflow

Scheduling using `cron`:

```yaml
cron: "0 9 * * *" # Run daily at 9 AM UTC
```

- Setup Python
- Install dependencies
- Check if daily run is needed
- Run script
- Update last run timestamp
- Commit changes

<br>

## 🐍 2. Python Script

Utilizes the Gemini API to analyze files. Based on a provided prompt, it applies formatting and styling enhancements.
Certain directories are ignored.
File changes are checked using hashes and only the changed files are made available for formatting.
```
