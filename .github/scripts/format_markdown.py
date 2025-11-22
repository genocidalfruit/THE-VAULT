import os
import hashlib
import requests
import json
import time
import sys
from typing import Dict, Optional

# --- Configuration ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Using Gemini 2.5 Flash - stable, free, and high performance
MODEL_NAME = "gemini-2.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"
HASH_FILE_PATH = ".github/file_hashes.json"
MAX_RETRIES = 5
RATE_LIMIT_DELAY = 60
MAX_RATE_LIMIT_ATTEMPTS = 3

# Excluded paths and files
EXCLUDED_DIRS = {'.git', 'Rough Notes'}
EXCLUDED_FILES = {'README.md'}
TAGS_FOLDER = 'TAGS'

# --- LLM System Instructions ---
STANDARD_SYSTEM_PROMPT = """You are a Markdown editor for Obsidian notes. Make exactly 3 changes:

1. ADD EMOJI TO ALL HEADINGS (# to ######):
   - Add ONE emoji before heading text if none exists
   - Apply to H1, H2, H3, H4, H5, and H6 headings
   - Examples: 💻 🔧 📊 📝 ⚡ 🔄 🎯 🚀 📌 ⚙️ 🔍 💡 ✨ 🛠️ 📋
   - Skip if emoji already present
   - Choose contextually appropriate emojis based on heading content

2. ADD DESCRIPTION AFTER EACH H1:
   - Insert blank line + 1-2 sentence description (under 50 words)
   - Only if no description exists after that H1
   - Describe what that specific section covers

3. ADD HORIZONTAL LINE BEFORE H1 (except first):
   - Add "---" with blank lines before/after
   - Apply to 2nd, 3rd, 4th+ H1 headings only
   - NOT before H2, H3, H4, H5, or H6

CRITICAL: PRESERVE HEADING HIERARCHY
   - The FIRST heading in the file MUST be H1 (#)
   - Do NOT start files with H2 (##) or lower headings
   - If file starts with H2+, promote it to H1
   - Maintain logical nesting: H1 > H2 > H3 > H4 > H5 > H6

Example:
# Machine Learning
## Introduction
### Basic Concepts
# Data Preprocessing

Becomes:
# 💻 Machine Learning

This section covers ML concepts and techniques.

## 📚 Introduction
### 💡 Basic Concepts

---

# 🔧 Data Preprocessing

This section explains data cleaning and preparation.

DO NOT CHANGE:
- YAML frontmatter, code blocks, links, lists, wiki links, tags, body text
- Only add emoji/description/lines - don't modify existing text
- Return COMPLETE file

If all headings have emojis, H1s have descriptions AND horizontal lines, return unchanged."""

TAGS_SYSTEM_PROMPT = """You are a Markdown editor for Obsidian tag files. Make exactly 3 changes:

1. ADD EMOJI TO ALL HEADINGS (# to ######):
   - Add ONE emoji before heading text if none exists
   - Apply to H1, H2, H3, H4, H5, and H6 headings
   - Examples: 🏷️ 📋 🔖 💡 🎯 📌 🗂️ 🔍 ⚡ 🛠️ 💻 📝 ✨ 🔧 📊
   - Skip if emoji already present
   - Choose contextually appropriate emojis based on heading content

2. ADD DESCRIPTION AFTER EACH H1, H2, H3:
   - Insert blank line + 1-2 sentence description (under 50 words)
   - Only if no description exists after that heading
   - Describe what that tag/section represents

3. ADD HORIZONTAL LINE BEFORE H1 (except first):
   - Add "---" with blank lines before/after
   - Apply to 2nd, 3rd, 4th+ H1 headings only
   - NOT before H2, H3, H4, H5, or H6

CRITICAL: PRESERVE HEADING HIERARCHY
   - The FIRST heading in the file MUST be H1 (#)
   - Do NOT start files with H2 (##) or lower headings
   - If file starts with H2+, promote it to H1
   - Maintain logical nesting: H1 > H2 > H3 > H4 > H5 > H6

Example:
# Programming Languages
## Python
### Scripts
- script.py
# Development Tools

Becomes:
# 💻 Programming Languages

Organizes notes on programming languages.

## 🐍 Python

Contains Python scripts and tutorials.

### 📄 Scripts
- script.py

---

# 🛠️ Development Tools

Covers development tools and editors.

DO NOT CHANGE:
- YAML frontmatter, code blocks, links, lists, wiki links, tags, body text
- Only add emoji/description/lines - don't modify existing text
- Return COMPLETE file

If all headings have emojis, H1/H2/H3 have descriptions AND H1 horizontal lines, return unchanged."""

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

def call_gemini_api(content: str, is_tags_file: bool = False) -> Optional[str]:
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set.")
        return None
    
    # Gemini API uses query parameter for API key
    # Format: https://generativelanguage.googleapis.com/v1beta/models/MODEL_NAME:generateContent?key=API_KEY
    url = f"{API_URL}?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json",
    }
    
    system_prompt = TAGS_SYSTEM_PROMPT if is_tags_file else STANDARD_SYSTEM_PROMPT
    
    # Gemini API request format
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\n{content}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
        }
    }
    
    rate_limit_attempts = 0
    attempt = 0
    
    while attempt < MAX_RETRIES:
        try:
            print(f"Attempt {attempt + 1}: Sending file to Gemini API...")
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        llm_output = result['candidates'][0]['content']['parts'][0]['text']
                        print(f"Gemini API call successful.")
                        return llm_output
                    else:
                        print(f"Invalid response structure from Gemini API: {result}")
                        print("Response details:", response.text[:300])
                        return None
                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    print(f"Error parsing API response from Gemini: {e}")
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
                print(f"Rate limit hit for Gemini API (attempt {rate_limit_attempts}/{MAX_RATE_LIMIT_ATTEMPTS})")
                print(f"Error: {error_msg}")
                
                if rate_limit_attempts >= MAX_RATE_LIMIT_ATTEMPTS:
                    print(f"Maximum rate limit attempts ({MAX_RATE_LIMIT_ATTEMPTS}) exceeded for Gemini API.")
                    print("This file will be skipped. Try running again later when rate limits reset.")
                    return None
                
                delay = RATE_LIMIT_DELAY * rate_limit_attempts
                print(f"Waiting {delay} seconds due to rate limiting...")
                time.sleep(delay)
                attempt += 1
                continue
                
            elif status_code in [500, 502, 503, 504]:
                print(f"Service temporarily unavailable (Status {status_code}) for Gemini API.")
                attempt += 1
                if attempt < MAX_RETRIES:
                    delay = 2 ** attempt * 10
                    print(f"Retrying in {delay}s...")
                    time.sleep(delay)
                continue
                
            elif status_code == 401 or status_code == 403:
                print(f"API key issue for Gemini API: {error_msg}")
                print("Check your GEMINI_API_KEY in GitHub secrets.")
                return None
                
            else:
                print(f"API Error (Status {status_code}) with Gemini API: {error_msg}")
                print(f"Response details: {response.text[:200]}...")
                attempt += 1
                if attempt < MAX_RETRIES:
                    delay = 2 ** attempt + (time.time() % 1)
                    print(f"Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                    
        except requests.exceptions.Timeout:
            print(f"Request timeout for Gemini API (90s). Retrying...")
            attempt += 1
            if attempt < MAX_RETRIES:
                delay = 2 ** attempt * 10
                print(f"Retrying in {delay}s...")
                time.sleep(delay)
                
        except requests.exceptions.RequestException as e:
            print(f"Network error for Gemini API: {e}")
            attempt += 1
            if attempt < MAX_RETRIES:
                delay = 2 ** attempt + (time.time() % 1)
                print(f"Retrying in {delay:.2f}s...")
                time.sleep(delay)
    
    print(f"All {MAX_RETRIES} attempts failed for Gemini API. Skipping LLM formatting for this file.")
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
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
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
                llm_output = call_gemini_api(current_content, is_tags_file)
                
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