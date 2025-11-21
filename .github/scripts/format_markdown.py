import os
import hashlib
import requests
import json
import time
import sys
from typing import Dict, Optional

# --- Configuration ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "qwen/qwen3-coder:free"
HASH_FILE_PATH = ".github/file_hashes.json"
MAX_RETRIES = 5
RATE_LIMIT_DELAY = 60
MAX_RATE_LIMIT_ATTEMPTS = 3

# Excluded paths and files
EXCLUDED_DIRS = {'.git', 'Rough Notes'}
EXCLUDED_FILES = {'README.md'}
TAGS_FOLDER = 'TAGS'

# --- LLM System Instructions ---
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

TAGS_SYSTEM_PROMPT = """You are a specialized editor for Obsidian tag description files. Perform these exact tasks on the provided Markdown content:

1. **Add Emojis to Headings**: ONLY modify H1 (#), H2 (##), and H3 (###) headings by prepending ONE relevant, professional emoji directly before the heading text. Choose emojis that represent the tag's theme or purpose.
2. **Add Brief Descriptions**: AFTER each H1, H2, or H3 heading (but before any existing content under it), add exactly ONE new paragraph providing a brief, 1-2 sentence description of what the heading represents.

CRITICAL RULES:
- Do NOT modify the heading levels or text (except adding the emoji).
- Do NOT change any existing content, YAML front matter, links, lists, code blocks, or other elements.
- If a description already exists under a heading, do NOT add another one.
- Descriptions must be concise (under 50 words) and informative.
- Preserve all Obsidian syntax including tags, wiki links, and callouts.
- Output MUST be complete, valid Markdown with ONLY these specified additions.
- If the file is already properly formatted with descriptions, return it unchanged.
"""

def get_file_hash(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def is_file_empty(filepath: str) -> bool:
    try:
        return os.path.getsize(filepath) == 0
    except OSError:
        return False

def load_hashes() -> Dict[str, str]:
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
    print(f"Saving {len(hashes)} hashes to {HASH_FILE_PATH}...")
    os.makedirs(os.path.dirname(HASH_FILE_PATH), exist_ok=True)
    try:
        with open(HASH_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(hashes, f, indent=2, ensure_ascii=False)
        print("Successfully saved hashes to JSON file.")
    except IOError as e:
        print(f"Error saving hashes to {HASH_FILE_PATH}: {e}")

def call_openrouter_api(content: str, is_tags_file: bool = False) -> Optional[str]:
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set.")
        return None
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/github-actions-bot/obsidian-formatter",
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
    rate_limit_attempts = 0
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            print(f"Attempt {attempt + 1}: Sending file to LLM ({MODEL_NAME})...")
            response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
            if response.status_code == 200:
                try:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        llm_output = result['choices'][0]['message']['content']  # Fixed: added [0]
                        print(f"LLM call successful with {MODEL_NAME}.")
                        return llm_output
                    else:
                        print(f"Invalid response structure from {MODEL_NAME}: {result}")
                        print("Response details:", response.text[:300])
                        return None
                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    print(f"Error parsing API response from {MODEL_NAME}: {e}")
                    print(f"Response: {response.text[:200]}...")
                    return None
            try:
                error_data = response.json()
            except json.JSONDecodeError:
                error_data = {}
            status_code = response.status_code
            error_msg = error_data.get('error', {}).get('message', f'HTTP {status_code}')
            if status_code == 429:
                rate_limit_attempts += 1
                print(f"Rate limit hit for {MODEL_NAME} (attempt {rate_limit_attempts}/{MAX_RATE_LIMIT_ATTEMPTS})")
                print(f"Error: {error_msg}")
                if rate_limit_attempts >= MAX_RATE_LIMIT_ATTEMPTS:
                    print(f"Maximum rate limit attempts ({MAX_RATE_LIMIT_ATTEMPTS}) exceeded for {MODEL_NAME}.")
                    print("This file will be skipped. Try running again later when rate limits reset.")
                    return None
                delay = RATE_LIMIT_DELAY * rate_limit_attempts
                print(f"Waiting {delay} seconds due to rate limiting...")
                time.sleep(delay)
                attempt += 1
                continue
            elif status_code in [500, 502, 503, 504]:  # Fixed: added list of status codes
                print(f"Service temporarily unavailable (Status {status_code}) for {MODEL_NAME}.")
                attempt += 1
                if attempt < MAX_RETRIES:
                    delay = 2 ** attempt * 10
                    print(f"Retrying in {delay}s...")
                    time.sleep(delay)
                continue
            elif status_code == 401:
                print(f"API key issue for {MODEL_NAME}: {error_msg}")
                print("Check your OPENROUTER_API_KEY in GitHub secrets.")
                return None
            else:
                print(f"API Error (Status {status_code}) with {MODEL_NAME}: {error_msg}")
                print(f"Response details: {response.text[:200]}...")
                attempt += 1
                if attempt < MAX_RETRIES:
                    delay = 2 ** attempt + (time.time() % 1)
                    print(f"Retrying in {delay:.2f}s...")
                    time.sleep(delay)
        except requests.exceptions.Timeout:
            print(f"Request timeout for {MODEL_NAME} (90s). Retrying...")
            attempt += 1
            if attempt < MAX_RETRIES:
                delay = 2 ** attempt * 10
                print(f"Retrying in {delay}s...")
                time.sleep(delay)
        except requests.exceptions.RequestException as e:
            print(f"Network error for {MODEL_NAME}: {e}")
            attempt += 1
            if attempt < MAX_RETRIES:
                delay = 2 ** attempt + (time.time() % 1)
                print(f"Retrying in {delay:.2f}s...")
                time.sleep(delay)
    print(f"All {MAX_RETRIES} attempts failed for {MODEL_NAME}. Skipping LLM formatting for this file.")
    return None

def should_skip_path(root: str, file: str, filepath: str) -> bool:
    filename = os.path.basename(filepath)
    if filename in EXCLUDED_FILES:
        return True
    root_parts = root.split(os.sep)
    if any(part in EXCLUDED_DIRS for part in root_parts):
        return True
    if TAGS_FOLDER in root_parts:
        return False
    return False

def process_markdown_files():
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY environment variable is not set.")
        sys.exit(1)
    old_hashes = load_hashes()
    new_hashes = {}
    files_processed = 0
    files_skipped_rate_limit = 0
    for root, dirs, files in os.walk(".", topdown=True):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        dirs[:] = [d for d in dirs if not (d.startswith('.') and d != '.github')]
        if should_skip_path(root, '', root):
            continue
        for file in files:
            if file.endswith(('.md', '.markdown')):
                filepath = os.path.join(root, file)
                norm_path = os.path.normpath(filepath)
                if should_skip_path(root, file, filepath):
                    print(f"Skipping excluded file: {norm_path}")
                    try:
                        current_hash = get_file_hash(filepath)
                        new_hashes[norm_path] = current_hash
                    except Exception as e:
                        print(f"Could not hash excluded file {norm_path}: {e}")
                    continue
                if is_file_empty(filepath):
                    print(f"Skipping empty file: {norm_path}")
                    empty_hash = hashlib.sha256(b'').hexdigest()
                    new_hashes[norm_path] = empty_hash
                    continue
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                except Exception as e:
                    print(f"Skipping {norm_path}: Could not read file content. Error: {e}")
                    continue
                current_hash = get_file_hash(filepath)
                old_hash = old_hashes.get(norm_path, "")
                if current_hash == old_hash:
                    print(f"Skipping {norm_path}: Already formatted (hash match).")
                    new_hashes[norm_path] = current_hash
                    continue
                print(f"Processing {norm_path}: Hash changed or new file. Running formatting...")
                is_tags_file = TAGS_FOLDER in root.split(os.sep)
                llm_output = call_openrouter_api(current_content, is_tags_file)
                if llm_output is None:
                    print(f"⚠️  Failed to format {norm_path} due to API issues - retaining original content.")
                    new_hashes[norm_path] = current_hash
                    files_skipped_rate_limit += 1
                    continue
                llm_output_hash = hashlib.sha256(llm_output.encode('utf-8')).hexdigest()
                if llm_output_hash != current_hash:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(llm_output)
                    print(f"✅ Successfully formatted and updated: {norm_path}")
                    new_hashes[norm_path] = llm_output_hash
                    files_processed += 1
                else:
                    print(f"ℹ️  No changes made by LLM: {norm_path}")
                    new_hashes[norm_path] = current_hash
    save_hashes(new_hashes)
    print(f"\n{'='*60}")
    print(f"PROCESSING SUMMARY:")
    print(f"✅ Files successfully formatted: {files_processed}")
    print(f"⚠️  Files skipped due to API limits or errors: {files_skipped_rate_limit}")
    print(f"{'='*60}")
    print(f"Hash file updated. Next run will skip successfully processed files.")

if __name__ == "__main__":
    process_markdown_files()