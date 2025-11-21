import os
import hashlib
import requests
import json
import time
import sys
from typing import Dict, Optional



# --- Configuration ---
# API Key is read from the GitHub Actions environment variable
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Using DeepSeek Coder for reliable instruction following and output formatting
MODEL_NAME = "qwen/qwen3-coder:free"
HASH_FILE_PATH = ".github/file_hashes.json"
MAX_RETRIES = 5


# Excluded paths and files
EXCLUDED_DIRS = {'.git', 'Rough Notes'}  # Directories to skip entirely
EXCLUDED_FILES = {'README.md'}  # Specific files to skip
TAGS_FOLDER = 'TAGS'  # Special folder with different formatting rules



# --- LLM System Instructions ---
# Standard prompt for regular Markdown files
STANDARD_SYSTEM_PROMPT = """You are a highly specialized Markdown formatter for Obsidian notes. Perform exactly two tasks on the provided content:

1. **Standardize Formatting**: Clean up the Markdown by:
   - Removing trailing whitespace from all lines
   - Ensuring consistent indentation (use 2 spaces for nested lists and code blocks)
   - Normalizing line breaks (single empty line between block elements, no multiple consecutive empty lines)
   - Ensuring consistent spacing around block elements like quotes, code blocks, and horizontal rules

2. **Add Emojis to Headings**: ONLY modify H1 (#), H2 (##), and H3 (###) headings by prepending ONE relevant, professional emoji directly before the heading text. Examples:
   - For technical topics: 💻, 🔧, 📊
   - For processes: 📝, ⚡, 🔄
   - Keep it simple and relevant. Do not add emojis to H4 or lower headings.

CRITICAL RULES:
- NEVER change heading levels, text content, YAML front matter, links ([[ ]]), inline code (`), code blocks (```
- Preserve all Obsidian-specific syntax like callouts (> [!note]), tags (#tag), and wiki links.
- Output MUST be complete, valid Markdown with ONLY the specified changes.
- If content is already perfectly formatted, return it unchanged.
"""


# Special prompt for TAGS folder files
TAGS_SYSTEM_PROMPT = """You are a specialized editor for Obsidian tag description files. Perform these exact tasks on the provided Markdown content:

1. **Add Emojis to Headings**: ONLY modify H1 (#), H2 (##), and H3 (###) headings by prepending ONE relevant, professional emoji directly before the heading text. Choose emojis that represent the tag's theme or purpose. Examples:
   - For topics: 📚, 💡, 🎯
   - For categories: 🏷️, 📂, 🔖
   - Keep it simple and meaningful.

2. **Add Brief Descriptions**: AFTER each H1, H2, or H3 heading (but before any existing content under it), add exactly ONE new paragraph providing a brief, 1-2 sentence description of what the heading represents. The description should be helpful for someone discovering the tag but should not repeat or alter the heading text.

CRITICAL RULES:
- Do NOT modify the heading levels or text (except adding the emoji).
- Do NOT change any existing content, YAML front matter, links, lists, code blocks, or other elements.
- If a description already exists under a heading, do NOT add another one.
- Descriptions must be concise (under 50 words) and informative.
- Preserve all Obsidian syntax including tags, wiki links, and callouts.
- Output MUST be complete, valid Markdown with ONLY these specified additions.
- If the file is already properly formatted with descriptions, return it unchanged.
"""



# --- Hashing Functions ---



def get_file_hash(filepath: str) -> str:
    """Calculates the SHA256 hash of a file's content."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()



def is_file_empty(filepath: str) -> bool:
    """Checks if a file is completely empty (0 bytes)."""
    try:
        return os.path.getsize(filepath) == 0
    except OSError:
        return False



def load_hashes() -> Dict[str, str]:
    """Loads previous file hashes from the JSON tracking file."""
    hashes = {}
    if not os.path.exists(HASH_FILE_PATH):
        print(f"No previous hashes file found at {HASH_FILE_PATH}.")
        return hashes
    
    print(f"Loading previous hashes from {HASH_FILE_PATH}...")
    try:
        with open(HASH_FILE_PATH, 'r', encoding='utf-8') as f:
            hashes = json.load(f)
        print(f"Loaded {len(hashes)} file hashes from JSON.")
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading hashes from {HASH_FILE_PATH}: {e}. Starting with empty hash dict.")
        hashes = {}
    return hashes



def save_hashes(hashes: Dict[str, str]):
    """Saves the current file hashes to the JSON tracking file."""
    print(f"Saving {len(hashes)} hashes to {HASH_FILE_PATH}...")
    # Ensure the directory exists before saving
    os.makedirs(os.path.dirname(HASH_FILE_PATH), exist_ok=True)
    try:
        with open(HASH_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(hashes, f, indent=2, ensure_ascii=False)
        print("Successfully saved hashes to JSON file.")
    except IOError as e:
        print(f"Error saving hashes to {HASH_FILE_PATH}: {e}")



# --- LLM Communication ---



def call_openrouter_api(content: str, is_tags_file: bool = False) -> Optional[str]:
    """Calls the OpenRouter API with exponential backoff, using appropriate prompt."""
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set.")
        return None
        
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/github-actions-bot/obsidian-formatter",  # Required for OpenRouter to log usage correctly
        "X-Title": "Obsidian Markdown Formatter Action",
    }
    
    system_prompt = TAGS_SYSTEM_PROMPT if is_tags_file else STANDARD_SYSTEM_PROMPT
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
    }

    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            print(f"Attempt {attempt + 1}: Sending file to LLM...")
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                llm_output = result['choices']['message']['content']
                print("LLM call successful.")
                return llm_output
            
            # Handle non-200 errors (rate limits, bad request, etc.)
            print(f"API Error (Status {response.status_code}): {response.text}")
            attempt += 1
            if attempt < MAX_RETRIES:
                delay = 2 ** attempt + (time.time() % 1)
                print(f"Retrying in {delay:.2f}s...")
                time.sleep(delay)
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            attempt += 1
            if attempt < MAX_RETRIES:
                delay = 2 ** attempt + (time.time() % 1)
                print(f"Retrying in {delay:.2f}s...")
                time.sleep(delay)
    
    print("Maximum retries exceeded. Skipping LLM formatting for this file.")
    return None



# --- Main Logic ---



def should_skip_path(root: str, file: str, filepath: str) -> bool:
    """Determine if a file or directory should be skipped based on exclusion rules."""
    filename = os.path.basename(filepath)
    
    # Skip specific files like README.md (check by filename only)
    if filename in EXCLUDED_FILES:
        return True
    
    # Check if in excluded directory (including subpaths)
    root_parts = root.split(os.sep)
    if any(part in EXCLUDED_DIRS for part in root_parts):
        return True
    
    # Special check for TAGS folder (we process it differently, but don't skip)
    if TAGS_FOLDER in root_parts:
        return False
    
    return False



def process_markdown_files():
    """Main function to iterate, compare hashes, and format files."""
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY environment variable is not set.")
        sys.exit(1)

    old_hashes = load_hashes()
    new_hashes = {}
    files_processed = 0

    # Walk through the repository to find all Markdown files
    for root, dirs, files in os.walk(".", topdown=True):
        # Modify dirs in-place to prune excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        
        # Additional skip for hidden directories (except .github where we store hashes)
        dirs[:] = [d for d in dirs if not (d.startswith('.') and d != '.github')]
        
        if should_skip_path(root, '', root):  # Skip the root if needed
            continue
            
        for file in files:
            if file.endswith(('.md', '.markdown')):
                filepath = os.path.join(root, file)
                
                # Normalize path for consistent hashing across different OS/environments
                norm_path = os.path.normpath(filepath)
                
                # Early exclusion check - catch README.md and excluded paths
                if should_skip_path(root, file, filepath):
                    print(f"Skipping excluded file: {norm_path}")
                    # Still track its hash to avoid unnecessary future checks
                    try:
                        current_hash = get_file_hash(filepath)
                        new_hashes[norm_path] = current_hash
                    except Exception as e:
                        print(f"Could not hash excluded file {norm_path}: {e}")
                        pass  # If can't read excluded file, skip silently
                    continue
                
                # Check if file is completely empty - skip empty files
                if is_file_empty(filepath):
                    print(f"Skipping empty file: {norm_path}")
                    # Track empty hash for consistency
                    empty_hash = hashlib.sha256(b'').hexdigest()
                    new_hashes[norm_path] = empty_hash
                    continue
                
                current_content = None
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                except Exception as e:
                    print(f"Skipping {norm_path}: Could not read file content. Error: {e}")
                    continue

                # Check for content changes using hash comparison
                current_hash = get_file_hash(filepath)
                old_hash = old_hashes.get(norm_path, "")
                
                if current_hash == old_hash:
                    # File matches previous hash (already formatted or unchanged)
                    print(f"Skipping {norm_path}: Already formatted (hash match).")
                    new_hashes[norm_path] = current_hash
                    continue
                
                print(f"Processing {norm_path}: Hash changed or new file. Running formatting...")

                # Determine if this is a TAGS file
                is_tags_file = TAGS_FOLDER in root.split(os.sep)
                
                # Call LLM for formatting with appropriate prompt
                llm_output = call_openrouter_api(current_content, is_tags_file)
                
                if llm_output is None:
                    # If LLM failed, retain the original and update hash to current
                    new_hashes[norm_path] = current_hash
                    continue
                
                # Check for actual changes and write back
                llm_output_hash = hashlib.sha256(llm_output.encode('utf-8')).hexdigest()
                
                if llm_output_hash != current_hash:
                    # Changes made, write the new content
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(llm_output)
                    print(f"✅ Successfully formatted and updated: {norm_path}")
                    new_hashes[norm_path] = llm_output_hash
                    files_processed += 1
                else:
                    # No changes needed
                    print(f"ℹ️  No changes made by LLM: {norm_path}")
                    new_hashes[norm_path] = current_hash
    
    # Save the updated hash list
    save_hashes(new_hashes)
    print(f"\nCompleted processing. {files_processed} files were modified by the LLM.")


if __name__ == "__main__":
    process_markdown_files()
