import os
import sys
import requests

def is_tags_file(file_path):
    """
    Determine if the file is a TAGS file.
    Adjust this logic as needed for your repo structure.
    """
    # Example: any file in a 'tags' folder or with 'tag' in the filename
    lower_path = file_path.lower()
    return ("tags" in lower_path or "tag" in os.path.basename(lower_path))

def format_markdown_with_deepseek_r1(content, file_path, is_tags_file_flag):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY is not set.")
        return content

    prompt = f"""You are an expert markdown formatter. Your task is to improve the formatting and readability of markdown content while preserving all original meaning and information.

**File Path**: {file_path}
**Special Context**: {'This is a knowledge base tag file' if is_tags_file_flag else 'This is a general markdown document'}

**CRITICAL REQUIREMENT - Tags Section**:
ALWAYS ensure there is a "Tags" section at the very top of every document (after the title if present). The Tags section should be formatted exactly as:

Tags: 

(with no additional formatting, emojis, or styling - just plain text)

If the document already has a Tags section, keep it at the top. If it doesn't have one, add it at the top.

**Core Formatting Rules**:
1. **Heading Hierarchy**: Ensure proper progression (# → ## → ### → ####)
2. **List Consistency**: Use `-` for unordered lists, numbers only when sequence matters
3. **Code Blocks**: Add appropriate language identifiers (```
4. **Spacing**: Maintain consistent spacing between sections
5. **Links**: Preserve all URLs and link text exactly as provided
6. **Content Preservation**: Never alter the actual information, only improve presentation

**Visual Enhancement Guidelines**:
- Add relevant emojis to main headings only (not subheadings or lists)
- Keep emojis professional and contextually appropriate
- Avoid emojis in code blocks, inline code, or technical sections
- For TAGS files: Add brief descriptions at the start of each section
- DO NOT add emojis or formatting to the "Tags" section itself

**Special Instructions for TAGS Files**:
If this is a TAGS folder file, add a concise 1-2 sentence description at the beginning of each major section explaining what that tag category covers in the knowledge base.

**Output Requirements**:
- Return ONLY the formatted markdown content
- Do not wrap output in code blocks or add commentary
- If the file is empty, return empty content
- Maintain all original links, references, and technical details
- ALWAYS include the Tags section at the top (plain text format: "Tags: ")

**Content to Format**:
{content}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "Markdown Formatter"
    }

    data = {
        "model": "deepseek-coder:33b",
        "messages": [
            {"role": "system", "content": "You are a helpful markdown formatting assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,
        "temperature": 0.0,
        "top_p": 1.0
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=180
        )
        response.raise_for_status()
        result = response.json()
        formatted_content = result["choices"]["message"]["content"]

        # Remove code block wrappers if present
        if formatted_content.startswith("```"):
            # Remove the first line entirely (``` or ```markdown)
            lines = formatted_content.splitlines()
            if len(lines) > 1 and lines[0].startswith("```"):
                lines = lines[1:]
            formatted_content = "\n".join(lines)

        if formatted_content.endswith("```"):
            # Remove the last line entirely if it's ```
            lines = formatted_content.splitlines()
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            formatted_content = "\n".join(lines)

        return formatted_content
    except Exception as e:
        print(f"Error formatting {file_path}: {e}")
        return content

def main():
    changed_files = os.environ.get("CHANGED_FILES", "")
    if not changed_files:
        print("No changed markdown files to process.")
        sys.exit(0)

    file_list = changed_files.strip().split()
    if not file_list:
        print("No changed markdown files to process.")
        sys.exit(0)

    updated = 0
    for file_path in file_list:
        if not os.path.isfile(file_path):
            print(f"File not found: {file_path}")
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original = f.read()
        except Exception as e:
            print(f"Could not read {file_path}: {e}")
            continue

        if not original.strip():
            print(f"Skipping empty file: {file_path}")
            continue

        is_tags = is_tags_file(file_path)
        formatted = format_markdown_with_deepseek_r1(original, file_path, is_tags)

        if formatted.strip() != original.strip():
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(formatted)
                print(f"✅ Formatted: {file_path}")
                updated += 1
            except Exception as e:
                print(f"Could not write {file_path}: {e}")
        else:
            print(f"🟡 No changes needed: {file_path}")

    print(f"\nSummary: {updated} file(s) updated out of {len(file_list)} changed.")

if __name__ == "__main__":
    main()
