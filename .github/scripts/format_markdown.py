import os
import sys
import requests
import hashlib
import difflib

def is_tags_file(file_path):
    """Check if the file is a tags file based on path or filename."""
    lower_path = file_path.lower()
    return "tags" in lower_path or "tag" in os.path.basename(lower_path)

def calculate_content_hash(content):
    """Calculate SHA256 hash of content for comparison."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def is_content_significantly_different(original, formatted):
    """
    Check if the formatted content is significantly different from original.
    Uses multiple criteria to determine if changes are meaningful.
    """
    # Remove leading/trailing whitespace for comparison
    original_clean = original.strip()
    formatted_clean = formatted.strip()
    
    # If exactly the same, no changes needed
    if original_clean == formatted_clean:
        return False
    
    # Calculate similarity ratio
    similarity = difflib.SequenceMatcher(None, original_clean, formatted_clean).ratio()
    
    # If similarity is very high (>95%), consider it as no significant changes
    if similarity > 0.95:
        # Check if the only differences are minor formatting (spaces, newlines)
        original_normalized = ' '.join(original_clean.split())
        formatted_normalized = ' '.join(formatted_clean.split())
        
        if original_normalized == formatted_normalized:
            return False
    
    # If we reach here, there are significant differences
    return True

def format_markdown_with_deepseek_r1(content, file_path, is_tags_file_flag):
    """Format markdown content using DeepSeek R1 model via OpenRouter API."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY is not set.")
        return content

    prompt = f"""You are an expert markdown formatter. Your task is to improve the formatting and readability of markdown content while preserving all original meaning and information.

**File Path**: {file_path}
**Special Context**: {'This is a knowledge base tag file' if is_tags_file_flag else 'This is a general markdown document'}

**CRITICAL REQUIREMENTS**:

1. **Tags Section**: ALWAYS ensure there is a "Tags:" section at the very top of every document (after the title if present). Format it exactly as:
   ```
   Tags: 
   ```
   (Plain text, no additional formatting, emojis, or styling)

2. **Content Preservation**: 
   - Never alter the actual information or meaning
   - Preserve all URLs and link text exactly as provided
   - Keep all technical details intact
   - Maintain all existing content structure

3. **Formatting Rules**:
   - **Heading Hierarchy**: Ensure proper progression (# → ## → ### → ####)
   - **List Consistency**: Use `-` for unordered lists, numbers only when sequence matters
   - **Code Blocks**: Add appropriate language identifiers where missing
   - **Spacing**: Maintain consistent spacing between sections
   - **Visual Enhancement**: Add relevant emojis to main headings only (not subheadings or lists)

4. **Special Instructions for TAGS Files**:
   If this is a TAGS folder file, add a concise 1-2 sentence description at the beginning of each major section explaining what that tag category covers.

5. **Output Requirements**:
   - Return ONLY the formatted markdown content
   - Do not wrap output in code blocks or add commentary
   - If the content is already well-formatted, make minimal changes
   - Maintain all original links, references, and technical details

**Content to Format**:
{content}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "Markdown Formatter"
    }

    data = {
        "model": "deepseek/deepseek-r1",  # Updated model name
        "messages": [
            {"role": "system", "content": "You are a helpful markdown formatting assistant. Format the content while preserving all original meaning and information."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,  # Increased token limit
        "temperature": 0.1,  # Slightly higher for better formatting creativity
        "top_p": 1.0
    }

    try:
        print(f"🔄 Formatting {file_path}...")
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=180
        )
        response.raise_for_status()
        result = response.json()
        
        if "choices" not in result or not result["choices"]:
            print(f"❌ No response choices for {file_path}")
            return content
            
        formatted_content = result["choices"][0]["message"]["content"]

        # Clean up potential code block wrapping
        if formatted_content.startswith("```"):
            lines = formatted_content.splitlines()
            if len(lines) > 1 and lines[0].startswith("```"):
                lines = lines[1:]
            formatted_content = "\n".join(lines)

        if formatted_content.endswith("```"):
            lines = formatted_content.splitlines()
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            formatted_content = "\n".join(lines)

        return formatted_content.strip() + "\n"  # Ensure single trailing newline
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API request error for {file_path}: {e}")
        return content
    except KeyError as e:
        print(f"❌ API response format error for {file_path}: {e}")
        return content
    except Exception as e:
        print(f"❌ Unexpected error formatting {file_path}: {e}")
        return content

def process_file(file_path):
    """Process a single markdown file."""
    if not os.path.isfile(file_path):
        print(f"❌ File not found: {file_path}")
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()
    except Exception as e:
        print(f"❌ Could not read {file_path}: {e}")
        return False

    if not original_content.strip():
        print(f"⏭️  Skipping empty file: {file_path}")
        return False

    # Check if file is a tags file
    is_tags = is_tags_file(file_path)
    
    # Format the content
    formatted_content = format_markdown_with_deepseek_r1(original_content, file_path, is_tags)
    
    # Check if changes are significant
    if not is_content_significantly_different(original_content, formatted_content):
        print(f"✅ No changes needed: {file_path}")
        return False

    # Write the formatted content back to file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(formatted_content)
        print(f"✅ Formatted: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Could not write {file_path}: {e}")
        return False

def main():
    """Main function to process changed markdown files."""
    changed_files = os.environ.get("CHANGED_FILES", "")
    if not changed_files:
        print("ℹ️  No changed markdown files to process.")
        sys.exit(0)

    # Parse the changed files list
    file_list = []
    for line in changed_files.strip().split('\n'):
        if line.strip():
            # Remove quotes if present
            file_path = line.strip().strip('"').strip("'")
            if file_path:
                file_list.append(file_path)

    if not file_list:
        print("ℹ️  No valid markdown files to process.")
        sys.exit(0)

    print(f"🚀 Processing {len(file_list)} changed markdown file(s)...")
    
    updated_count = 0
    for file_path in file_list:
        print(f"\n📄 Processing: {file_path}")
        if process_file(file_path):
            updated_count += 1

    print(f"\n📊 Summary: {updated_count} file(s) updated out of {len(file_list)} processed.")
    
    # Exit with appropriate code
    if updated_count > 0:
        print("✅ Files were updated and ready for commit.")
        sys.exit(0)
    else:
        print("ℹ️  No files needed formatting updates.")
        sys.exit(0)

if __name__ == "__main__":
    main()