import os
import json
from pathlib import Path
from typing import List, Dict

def process_meeting_files(raw_dir: str = "data/clean/cleaned", clean_dir: str = "data/clean") -> List[Dict]:
    """
    Process cleaned meeting transcripts from cleaned directory.
    Supports .txt, .json, .md files.
    """
    raw_path = Path(raw_dir)
    clean_path = Path(clean_dir)
    clean_path.mkdir(parents=True, exist_ok=True)
    
    processed_meetings = []
    
    if not raw_path.exists():
        print(f"Raw directory {raw_dir} doesn't exist. Creating it...")
        raw_path.mkdir(parents=True, exist_ok=True)
        return processed_meetings
    
    # Process all files in raw directory
    for file_path in raw_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.json', '.md']:
            print(f"Processing: {file_path.name}")
            
            try:
                content = process_single_file(file_path)
                if content:
                    processed_meetings.append({
                        'filename': file_path.name,
                        'content': content,
                        'source': str(file_path)
                    })
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
    
    # Save processed meetings
    output_file = clean_path / "processed_meetings.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_meetings, f, indent=2, ensure_ascii=False)
    
    print(f"Processed {len(processed_meetings)} meeting files")
    return processed_meetings

def process_single_file(file_path: Path) -> str:
    """Process a single meeting file and structure the content."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_content = f.read()
    
    # Handle JSON files
    if file_path.suffix.lower() == '.json':
        try:
            data = json.loads(raw_content)
            return process_json_meeting(data, file_path.name)
        except json.JSONDecodeError:
            return process_text_meeting(raw_content, file_path.name)
    
    # Handle text and markdown files
    return process_text_meeting(raw_content, file_path.name)

def process_json_meeting(data: Dict, filename: str) -> str:
    """Process JSON meeting data into structured text."""
    
    structured_content = f"# Meeting: {filename}\n\n"
    
    # Extract common fields
    if 'title' in data:
        structured_content += f"## Meeting Title\n{data['title']}\n\n"
    
    if 'date' in data:
        structured_content += f"## Date\n{data['date']}\n\n"
    
    if 'participants' in data:
        participants = data['participants']
        if isinstance(participants, list):
            structured_content += f"## Participants\n{', '.join(participants)}\n\n"
        else:
            structured_content += f"## Participants\n{participants}\n\n"
    
    if 'client' in data:
        structured_content += f"## Client\n{data['client']}\n\n"
    
    if 'summary' in data:
        structured_content += f"## Meeting Summary\n{data['summary']}\n\n"
    
    if 'transcript' in data:
        structured_content += f"## Transcript\n{data['transcript']}\n\n"
    
    if 'key_points' in data:
        key_points = data['key_points']
        if isinstance(key_points, list):
            structured_content += "## Key Points\n"
            for point in key_points:
                structured_content += f"• {point}\n"
            structured_content += "\n"
        else:
            structured_content += f"## Key Points\n{key_points}\n\n"
    
    if 'objections' in data:
        structured_content += f"## Client Objections\n{data['objections']}\n\n"
    
    if 'pricing_discussion' in data:
        structured_content += f"## Pricing Discussion\n{data['pricing_discussion']}\n\n"
    
    if 'next_steps' in data:
        next_steps = data['next_steps']
        if isinstance(next_steps, list):
            structured_content += "## Next Steps\n"
            for step in next_steps:
                structured_content += f"• {step}\n"
            structured_content += "\n"
        else:
            structured_content += f"## Next Steps\n{next_steps}\n\n"
    
    if 'follow_up' in data:
        structured_content += f"## Follow-up Required\n{data['follow_up']}\n\n"
    
    # Add any remaining fields
    excluded_fields = {'title', 'date', 'participants', 'client', 'summary', 'transcript', 
                      'key_points', 'objections', 'pricing_discussion', 'next_steps', 'follow_up'}
    
    for key, value in data.items():
        if key not in excluded_fields:
            structured_content += f"## {key.replace('_', ' ').title()}\n{value}\n\n"
    
    return structured_content

def process_text_meeting(content: str, filename: str) -> str:
    """Process plain text meeting content."""
    
    # Add header if not present
    if not content.startswith('#'):
        structured_content = f"# Meeting: {filename}\n\n"
        structured_content += content
        return structured_content
    
    return content

def extract_meeting_metadata(content: str) -> Dict:
    """Extract metadata from meeting content for better chunking."""
    
    metadata = {}
    lines = content.split('\n')
    
    for line in lines[:20]:  # Check first 20 lines for metadata
        line = line.strip()
        if 'date:' in line.lower():
            metadata['date'] = line.split(':', 1)[1].strip()
        elif 'client:' in line.lower():
            metadata['client'] = line.split(':', 1)[1].strip()
        elif 'participants:' in line.lower():
            metadata['participants'] = line.split(':', 1)[1].strip()
    
    return metadata

if __name__ == "__main__":
    processed = process_meeting_files()
    print(f"Successfully processed {len(processed)} meeting files")