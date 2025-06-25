Tags : 

## 1. Set Up GitHub Actions Workflow

Scheduling using -
`cron: "0 9 * * *" # Run daily at 9 AM UTC`

- Setup Python
- Install dependencies
- Check if daily run is needed
- Run script
- Update last run timestamp
- Commit changes

## 2. Python Script

Uses Gemini API to read through files and based on a prompt, add formatting and styling to the files.