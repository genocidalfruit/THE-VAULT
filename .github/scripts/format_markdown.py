import os
import sys
import requests
import hashlib
import json
import glob
from pathlib import Path

# Hash storage file
HASH_FILE = ".github/.markdown_hashes.json"

def calculate_content_hash(content):
    """Calculate SHA256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def load_stored_hashes():
    """Load previously stored file hashes."""
    if os.path.exists(HASH_FILE):
        try:
            with open(HASH_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Warning: Could not load hash file: {e}")
    return {}

def save_stored_hashes(hashes):
    """Save file hashes to storage."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(HASH_FILE), exist_ok=True)
        with open(HASH_FILE, 'w', encoding='utf-8') as f:
            json.dump(hashes, f, indent=2)
    except IOError as e:
        print(f"⚠️  Warning: Could not save hash file: {e}")

def is_tags_file(file_path):
    """Check if the file is a tags file based on path or filename."""
    lower_path = file_path.lower()
    return "tags" in lower_path or "tag" in os.path.basename(lower_path)

def find_all_markdown_files():
    """Find all markdown files in the repository."""
    markdown_files = []
    
    # Common markdown file patterns
    patterns = [
        "**/*.md",
        "**/*.markdown"
    ]
    
    # Files to ignore
    ignore_patterns = [
        ".github/**",
        ".git/**",
        "**/README.md",
        "**/readme.md",
        "CHANGELOG.md",
        "LICENSE.md"
    ]
    
    for pattern in patterns:
        for file_path in glob.glob(pattern, recursive=True):
            # Convert to Path object for easier manipulation
            path_obj = Path(file_path)
            
            # Check if file should be ignored
            should_ignore = False
            for ignore_pattern in ignore_patterns:
                if path_obj.match(ignore_pattern.replace("**", "*")):
                    should_ignore = True
                    break
            
            if not should_ignore and path_obj.is_file():
                markdown_files.append(str(path_obj))
    
    return markdown_files

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
        "model": "deepseek/deepseek-r1",
        "messages": [
            {"role": "system", "content": "You are a helpful markdown formatting assistant. Format the content while preserving all original meaning and information."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,
        "temperature": 0.1,
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

        return formatted_content.strip() + "\n"
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API request error for {file_path}: {e}")
        return content
    except KeyError as e:
        print(f"❌ API response format error for {file_path}: {e}")
        return content
    except Exception as e:
        print(f"❌ Unexpected error formatting {file_path}: {e}")
        return content

def process_file(file_path, stored_hashes):
    """Process a single markdown file based on hash comparison."""
    if not os.path.isfile(file_path):
        print(f"❌ File not found: {file_path}")
        return False, None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()
    except Exception as e:
        print(f"❌ Could not read {file_path}: {e}")
        return False, None

    if not original_content.strip():
        print(f"⏭️  Skipping empty file: {file_path}")
        return False, None

    # Calculate current hash
    current_hash = calculate_content_hash(original_content)
    stored_hash = stored_hashes.get(file_path)

    # Check if file has changed since last processing
    if stored_hash == current_hash:
        print(f"✅ No changes detected: {file_path}")
        return False, current_hash

    print(f"🔍 Hash changed for: {file_path}")
    print(f"   Stored: {stored_hash[:8] if stored_hash else 'None'}...")
    print(f"   Current: {current_hash[:8]}...")

    # Check if file is a tags file
    is_tags = is_tags_file(file_path)
    
    # Format the content
    formatted_content = format_markdown_with_deepseek_r1(original_content, file_path, is_tags)
    
    # Calculate hash of formatted content
    formatted_hash = calculate_content_hash(formatted_content)
    
    # Only write if the formatted content is different from original
    if formatted_hash != current_hash:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(formatted_content)
            print(f"✅ Formatted and updated: {file_path}")
            return True, formatted_hash
        except Exception as e:
            print(f"❌ Could not write {file_path}: {e}")
            return False, current_hash
    else:
        print(f"ℹ️  Content unchanged after formatting: {file_path}")
        return False, current_hash

def main():
    """Main function to process markdown files based on hash comparison."""
    print("🚀 Starting hash-based markdown formatting...")
    
    # Load stored hashes
    stored_hashes = load_stored_hashes()
    print(f"📊 Loaded {len(stored_hashes)} stored file hashes")
    
    # Find all markdown files
    markdown_files = find_all_markdown_files()
    print(f"📄 Found {len(markdown_files)} markdown files to check")
    
    if not markdown_files:
        print("ℹ️  No markdown files found.")
        sys.exit(0)

    updated_count = 0
    new_hashes = {}
    
    for file_path in markdown_files:
        print(f"\n📝 Checking: {file_path}")
        was_updated, file_hash = process_file(file_path, stored_hashes)
        
        if was_updated:
            updated_count += 1
        
        # Store the hash (either new formatted hash or original hash)
        if file_hash:
            new_hashes[file_path] = file_hash

    # Update stored hashes with new values
    stored_hashes.update(new_hashes)
    
    # Remove hashes for files that no longer exist
    existing_files = set(markdown_files)
    stored_hashes = {k: v for k, v in stored_hashes.items() if k in existing_files}
    
    # Save updated hashes
    save_stored_hashes(stored_hashes)
    print(f"💾 Saved {len(stored_hashes)} file hashes")

    print(f"\n📊 Summary:")
    print(f"   📄 Files checked: {len(markdown_files)}")
    print(f"   ✅ Files updated: {updated_count}")
    print(f"   💾 Hashes stored: {len(stored_hashes)}")
    
    if updated_count > 0:
        print("✅ Files were updated and ready for commit.")
    else:
        print("ℹ️  No files needed formatting updates.")

if __name__ == "__main__":
    main()