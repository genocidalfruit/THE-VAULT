import os
import hashlib
import requests
import time
import sys
from typing import Dict, Optional

# --- Configuration ---
# API Key is read from the GitHub Actions environment variable
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Using DeepSeek Coder for reliable instruction following and output formatting
MODEL_NAME = "deepseek/deepseek-coder"
HASH_FILE_PATH = ".github/file_hashes.txt"
MAX_RETRIES = 5

# --- LLM System Instruction ---
# This prompt strictly guides the model to perform both tasks (formatting and emoji addition) 
# while protecting YAML front matter and other content.
SYSTEM_PROMPT = """You are a highly specialized code formatter and editor designed for Obsidian Markdown notes. Your task is to perform two actions on the provided Markdown content:
1.  **Standardize Formatting:** Apply modern Markdown formatting best practices (e.g., trim trailing whitespace, ensure consistent list indentation, and normalize line breaks).
2.  **Add Emojis:** ONLY modify H1, H2, and H3 headings by prepending a single, relevant, and professional emoji to the heading text. Do not add emojis to other heading levels.

CRITICAL RULE: DO NOT change the heading level or the text of the heading, except to add the emoji. DO NOT modify any part of the YAML front matter, links, code blocks, lists, or regular paragraph text. The output MUST be valid, complete Markdown content, including all original front matter and content, with only the specified modifications.
"""

# --- Hashing Functions ---

def get_file_hash(filepath: str) -> str:
    """Calculates the SHA256 hash of a file's content."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def load_hashes() -> Dict[str, str]:
    """Loads previous file hashes from the tracking file."""
    hashes = {}
    if not os.path.exists(HASH_FILE_PATH):
        return hashes
    
    print(f"Loading previous hashes from {HASH_FILE_PATH}...")
    with open(HASH_FILE_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    hash_val, path = line.split(" ", 1)
                    hashes[path] = hash_val
                except ValueError:
                    # Skip malformed lines
                    continue
    return hashes

def save_hashes(hashes: Dict[str, str]):
    """Saves the current file hashes to the tracking file."""
    print(f"Saving updated hashes to {HASH_FILE_PATH}...")
    # Ensure the directory exists before saving
    os.makedirs(os.path.dirname(HASH_FILE_PATH), exist_ok=True)
    with open(HASH_FILE_PATH, 'w') as f:
        for path, hash_val in hashes.items():
            f.write(f"{hash_val} {path}\n")

# --- LLM Communication ---

def call_openrouter_api(content: str) -> Optional[str]:
    """Calls the OpenRouter API with exponential backoff."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/github-actions-bot/obsidian-formatter", # Required for OpenRouter to log usage correctly
        "X-Title": "Obsidian Markdown Formatter Action",
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
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
                llm_output = result['choices'][0]['message']['content']
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

def process_markdown_files():
    """Main function to iterate, compare hashes, and format files."""
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY environment variable is not set.")
        sys.exit(1)

    old_hashes = load_hashes()
    new_hashes = {}
    files_processed = 0

    # Walk through the repository to find all Markdown files
    for root, _, files in os.walk("."):
        # Skip hidden directories and build directories
        if any(d.startswith('.') and d not in ['.github'] for d in root.split(os.sep)):
            continue
        if 'node_modules' in root or '.git' in root:
            continue
            
        for file in files:
            if file.endswith(('.md', '.markdown')):
                filepath = os.path.join(root, file)
                
                # Normalize path for consistent hashing across different OS/environments
                norm_path = os.path.normpath(filepath)
                
                current_content = None
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                except Exception as e:
                    print(f"Skipping {norm_path}: Could not read file content. Error: {e}")
                    continue

                # 1. Check for content changes using hash comparison
                current_hash = get_file_hash(filepath)
                old_hash = old_hashes.get(norm_path)
                
                if current_hash == old_hash:
                    # File has not changed since the last successful format, skip API call
                    print(f"Skipping {norm_path}: Content unchanged.")
                    new_hashes[norm_path] = current_hash
                    continue
                
                print(f"Processing {norm_path}: Hash mismatch or new file. Formatting...")

                # 2. Call LLM for formatting
                llm_output = call_openrouter_api(current_content)
                
                if llm_output is None:
                    # If LLM failed, retain the original file and keep the current_hash
                    # The hash comparison will trigger processing again on the next run.
                    new_hashes[norm_path] = current_hash
                    continue
                
                # 3. Check for actual changes and write back
                # Recalculate hash of the LLM output to decide if the file was modified
                llm_output_hash = hashlib.sha256(llm_output.encode('utf-8')).hexdigest()
                
                if llm_output_hash != current_hash:
                    # Changes made by the LLM, write the new content
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(llm_output)
                    print(f"✅ Successfully formatted and updated: {norm_path}")
                    # Store the hash of the *new* content for tracking
                    new_hashes[norm_path] = llm_output_hash
                    files_processed += 1
                else:
                    # LLM didn't make changes (e.g., already perfectly formatted)
                    print(f"ℹ️  No effective changes made by LLM: {norm_path}")
                    new_hashes[norm_path] = current_hash
    
    # 4. Save the updated hash list
    save_hashes(new_hashes)
    print(f"\nCompleted processing. {files_processed} files were modified by the LLM.")


if __name__ == "__main__":
    process_markdown_files()