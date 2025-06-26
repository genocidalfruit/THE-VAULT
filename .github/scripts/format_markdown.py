import os
import glob
import json
import hashlib
import time
import requests
from datetime import datetime, timedelta

# Configure OpenRouter API
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable not set")

TRACKING_FILE = '.github/formatted-files-tracking.json'
CACHE_DURATION_DAYS = 7  # Re-format files after 7 days

def get_file_hash(file_path):
    """Generate MD5 hash of file content"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def load_tracking_data():
    """Load tracking data from JSON file"""
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_tracking_data(data):
    """Save tracking data to JSON file"""
    os.makedirs(os.path.dirname(TRACKING_FILE), exist_ok=True)
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def should_format_file(file_path, tracking_data):
    """Determine if file should be formatted based on tracking data"""
    current_hash = get_file_hash(file_path)
    current_time = time.time()
    
    if file_path not in tracking_data:
        return True, current_hash
    
    file_data = tracking_data[file_path]
    
    # Check if file content has changed
    if file_data.get('hash') != current_hash:
        return True, current_hash
    
    # Check if cache has expired
    last_formatted = file_data.get('last_formatted', 0)
    cache_expiry = last_formatted + (CACHE_DURATION_DAYS * 24 * 3600)
    
    if current_time > cache_expiry:
        return True, current_hash
    
    return False, current_hash

def format_markdown_with_deepseek_r1(content, file_path):
    """Format markdown content using DeepSeek R1 0528 Qwen3 8B via OpenRouter API"""
    
    # Determine if this is a TAGS folder file for special handling
    is_tags_file = 'TAGS' in file_path.upper()
    
    prompt = f"""You are an expert markdown formatter. Your task is to improve the formatting and readability of markdown content while preserving all original meaning and information.

**File Path**: {file_path}
**Special Context**: {'This is a knowledge base tag file' if is_tags_file else 'This is a general markdown document'}

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
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek/deepseek-r1-0528-qwen3-8b:free",
        "messages": [
            {
                "role": "system", 
                "content": "You are a professional markdown formatter focused on improving document readability while preserving all original content and meaning. Apply consistent formatting standards and enhance visual appeal through strategic use of emojis and spacing. ALWAYS ensure every document has a 'Tags: ' section at the top in plain text format."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 8000,
        "top_p": 0.9
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
        
        # Extract the formatted content
        formatted_content = result["choices"]["message"]["content"]
        
        # Clean up any potential code block wrapping
        if formatted_content.startswith('```markdown'):
            formatted_content = formatted_content[12:]
        if formatted_content.endswith('\n```'):
            formatted_content = formatted_content[:-4]
        
        return formatted_content
        
    except Exception as e:
        print(f"Error formatting with DeepSeek R1: {str(e)}")
        return content

def should_skip_file(file_path):
    """Determine if a file should be skipped based on path patterns"""
    # Skip files in excluded directories
    excluded_patterns = [
        'ROUGH NOTES/', 'RESOURCES/'  # Specified folders
    ]
    
    if any(pattern in file_path for pattern in excluded_patterns):
        return True
    
    # Skip any file or folder that starts with a dot
    path_parts = file_path.split(os.sep)
    if any(part.startswith('.') for part in path_parts):
        return True
    
    # Skip README files (case insensitive)
    filename = os.path.basename(file_path).lower()
    if filename in ['readme.md', 'readme.markdown']:
        return True
    
    return False

def process_markdown_files():
    """Process markdown files with intelligent tracking"""
    tracking_data = load_tracking_data()
    updated_files = []
    skipped_files = []
    
    # Get all markdown files recursively from all directories
    markdown_files = []
    for pattern in ['**/*.md', '**/*.markdown']:
        markdown_files.extend(glob.glob(pattern, recursive=True))
    
    # Remove duplicates and filter files
    markdown_files = [f for f in set(markdown_files) if not should_skip_file(f)]
    
    print(f"🔍 Found {len(markdown_files)} markdown files to process")
    
    for file_path in markdown_files:
        should_format, current_hash = should_format_file(file_path, tracking_data)
        
        if not should_format:
            skipped_files.append(file_path)
            print(f"⏭️ Skipping (already formatted): {file_path}")
            continue
        
        print(f"🔄 Processing: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                original_content = file.read()
            
            # Skip empty files
            if not original_content.strip():
                print(f"📄 Skipping empty file: {file_path}")
                continue
            
            # Format with DeepSeek R1
            formatted_content = format_markdown_with_deepseek_r1(original_content, file_path)
            
            # Only write if content actually changed
            if formatted_content.strip() != original_content.strip():
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(formatted_content)
                
                # Update tracking data
                tracking_data[file_path] = {
                    'hash': hashlib.md5(formatted_content.encode()).hexdigest(),
                    'last_formatted': time.time(),
                    'original_hash': current_hash,
                    'model_used': 'deepseek-r1-0528-qwen3-8b'
                }
                
                updated_files.append(file_path)
                print(f"✅ Successfully formatted: {file_path}")
            else:
                # Update tracking even if no changes to avoid reprocessing
                tracking_data[file_path] = {
                    'hash': current_hash,
                    'last_formatted': time.time(),
                    'original_hash': current_hash,
                    'model_used': 'deepseek-r1-0528-qwen3-8b'
                }
                print(f"📝 No changes needed: {file_path}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {str(e)}")
    
    # Clean up tracking data for deleted files
    existing_files = set(markdown_files)
    tracking_data = {k: v for k, v in tracking_data.items() if k in existing_files}
    
    # Save updated tracking data
    save_tracking_data(tracking_data)
    
    # Print summary
    print(f"\n📊 Processing Summary:")
    print(f"   ✨ Updated files: {len(updated_files)}")
    print(f"   ⏭️ Skipped files: {len(skipped_files)}")
    print(f"   📁 Total files: {len(markdown_files)}")
    
    if updated_files:
        print(f"\n📝 Updated files:")
        for file in updated_files:
            print(f"   - {file}")

if __name__ == "__main__":
    process_markdown_files()
