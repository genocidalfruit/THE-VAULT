import os
import glob
import json
import hashlib
import time
from datetime import datetime, timedelta
import google.generativeai as genai

# Configure Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

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

def format_markdown_with_gemini(content, file_path):
    """Format markdown content using Gemini API with file-specific context"""
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    prompt = f"""
    Please format and improve the following markdown content while preserving its structure and meaning.
    
    File: {file_path}
    
    Formatting requirements:
    1. Fix any formatting inconsistencies
    2. Ensure proper heading hierarchy (# ## ### ####)
    3. Standardize list formatting (use - for bullets, numbers only when order matters)
    4. Improve readability while maintaining the original content
    5. Ensure code blocks have proper language specification
    6. Maintain consistent spacing between sections
    7. Return only the formatted markdown without any additional commentary. Do not wrap it in "markdown ``````" or any other code block.
    8. Add a little flair in the formatting to make it visually appealing (Relevant emojis for headings, spacing, etc.)
    9. In case the file is empty, do not return any content.
    10. Do not replace links with any sort of text, keep them as they are.
    
    IMPORTANT: Do not change the original content, only the formatting. The goal is to enhance readability and consistency.
    
    Do not go overboard with the emojis, keep it professional and relevant to the content. Make sure not use them for non-heading bullet points or lists.
    Do not use emojis in code blocks or inline code. Do not use emojis for the 'Tags' section.

    Content to format:
    {content}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error formatting with Gemini: {str(e)}")
        return content  # Return original content if formatting fails

def filter_markdown_files(files):
    """Filter markdown files to exclude README files and files in dot folders"""
    filtered_files = []
    
    for file_path in files:
        # Skip files in dot folders (any directory component starting with .)
        if any(part.startswith('.') for part in file_path.split(os.sep)):
            continue
            
        # Skip README files (case insensitive)
        if os.path.basename(file_path).lower() == 'readme.md':
            continue
            
        filtered_files.append(file_path)
    
    return filtered_files

def process_markdown_files():
    """Process markdown files with intelligent tracking"""
    tracking_data = load_tracking_data()
    updated_files = []
    skipped_files = []
    
    # Get all markdown files recursively from all directories
    markdown_files = []
    for pattern in ['**/*.md', '**/*.markdown']:
        markdown_files.extend(glob.glob(pattern, recursive=True))
    
    # Remove duplicates
    markdown_files = list(set(markdown_files))
    
    # Apply comprehensive filtering
    # First exclude system/build directories and "Rough Notes" folder
    markdown_files = [f for f in markdown_files if not any(skip in f for skip in [
        '.git/', '.github/', '.obsidian/', '.trash/', 'ROUGH NOTES/', 'RESOURCES/'
    ])]
    
    # Then apply custom filtering for README and dot folders
    markdown_files = filter_markdown_files(markdown_files)
    
    print(f"Found {len(markdown_files)} markdown files to process")
    
    for file_path in markdown_files:
        should_format, current_hash = should_format_file(file_path, tracking_data)
        
        if not should_format:
            skipped_files.append(file_path)
            print(f"Skipping (already formatted): {file_path}")
            continue
        
        print(f"Processing: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                original_content = file.read()
            
            # Skip empty files
            if not original_content.strip():
                print(f"Skipping empty file: {file_path}")
                continue
            
            # Format with Gemini
            formatted_content = format_markdown_with_gemini(original_content, file_path)
            
            # Only write if content actually changed
            if formatted_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(formatted_content)
                
                # Update tracking data
                tracking_data[file_path] = {
                    'hash': hashlib.md5(formatted_content.encode()).hexdigest(),
                    'last_formatted': time.time(),
                    'original_hash': current_hash
                }
                
                updated_files.append(file_path)
                print(f"✅ Successfully formatted: {file_path}")
            else:
                # Update tracking even if no changes to avoid reprocessing
                tracking_data[file_path] = {
                    'hash': current_hash,
                    'last_formatted': time.time(),
                    'original_hash': current_hash
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
    print(f"   Updated files: {len(updated_files)}")
    print(f"   Skipped files: {len(skipped_files)}")
    print(f"   Total files: {len(markdown_files)}")
    
    if updated_files:
        print(f"\n📝 Updated files:")
        for file in updated_files:
            print(f"   - {file}")

if __name__ == "__main__":
    process_markdown_files()
