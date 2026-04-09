import json
import tiktoken
from pathlib import Path
from typing import List, Dict, Tuple

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count tokens in text using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except:
        # Fallback: rough estimation
        return len(text.split()) * 1.3

def chunk_meeting_content(
    meetings: List[Dict],
    max_tokens: int = 500,
    overlap_tokens: int = 50,
    output_file: str = "data/clean/meeting_chunks.json"
) -> List[Dict]:
    """
    Chunk meeting content into smaller pieces for embeddings.
    
    Args:
        meetings: List of processed meeting dictionaries
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlap between chunks
        output_file: Output file path
    
    Returns:
        List of chunk dictionaries
    """
    
    all_chunks = []
    
    for meeting in meetings:
        content = meeting['content']
        filename = meeting['filename']
        source = meeting['source']
        
        # Extract metadata from content
        metadata = extract_meeting_metadata(content)
        
        # Split content into sections first
        sections = split_into_sections(content)
        
        for section_title, section_content in sections:
            # Chunk each section
            section_chunks = chunk_text(
                text=section_content,
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens
            )
            
            for i, chunk_content in enumerate(section_chunks):
                chunk = {
                    'content': chunk_content,
                    'metadata': {
                        'source': source,
                        'filename': filename,
                        'section': section_title,
                        'chunk_index': i,
                        'total_chunks': len(section_chunks),
                        **metadata
                    },
                    'token_count': count_tokens(chunk_content)
                }
                all_chunks.append(chunk)
    
    # Save chunks
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    
    print(f"Created {len(all_chunks)} chunks from {len(meetings)} meetings")
    return all_chunks

def split_into_sections(content: str) -> List[Tuple[str, str]]:
    """Split content into logical sections based on headers."""
    
    sections = []
    lines = content.split('\n')
    current_section = ""
    current_title = "Introduction"
    
    for line in lines:
        # Check if line is a header (starts with #)
        if line.strip().startswith('#'):
            # Save previous section
            if current_section.strip():
                sections.append((current_title, current_section.strip()))
            
            # Start new section
            current_title = line.strip().replace('#', '').strip()
            current_section = ""
        else:
            current_section += line + '\n'
    
    # Add final section
    if current_section.strip():
        sections.append((current_title, current_section.strip()))
    
    return sections

def chunk_text(text: str, max_tokens: int = 500, overlap_tokens: int = 50) -> List[str]:
    """
    Split text into chunks with token-based limits and overlap.
    """
    
    # Split by paragraphs first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    for paragraph in paragraphs:
        paragraph_tokens = count_tokens(paragraph)
        
        # If single paragraph exceeds max_tokens, split it further
        if paragraph_tokens > max_tokens:
            # Save current chunk if it has content
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_tokens = 0
            
            # Split large paragraph by sentences
            sentences = split_by_sentences(paragraph)
            for sentence in sentences:
                sentence_tokens = count_tokens(sentence)
                
                if current_tokens + sentence_tokens > max_tokens:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
                    current_tokens = sentence_tokens
                else:
                    current_chunk += " " + sentence if current_chunk else sentence
                    current_tokens += sentence_tokens
        
        # If adding paragraph would exceed limit
        elif current_tokens + paragraph_tokens > max_tokens:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = paragraph
            current_tokens = paragraph_tokens
        
        # Add paragraph to current chunk
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
            current_tokens += paragraph_tokens
    
    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Add overlap between chunks
    if len(chunks) > 1 and overlap_tokens > 0:
        chunks = add_overlap(chunks, overlap_tokens)
    
    return chunks

def split_by_sentences(text: str) -> List[str]:
    """Split text by sentences."""
    import re
    
    # Simple sentence splitting
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences

def add_overlap(chunks: List[str], overlap_tokens: int) -> List[str]:
    """Add overlap between consecutive chunks."""
    
    if len(chunks) <= 1:
        return chunks
    
    overlapped_chunks = [chunks[0]]  # First chunk unchanged
    
    for i in range(1, len(chunks)):
        prev_chunk = chunks[i-1]
        current_chunk = chunks[i]
        
        # Get last part of previous chunk for overlap
        prev_words = prev_chunk.split()
        overlap_words = prev_words[-overlap_tokens:] if len(prev_words) > overlap_tokens else prev_words
        overlap_text = " ".join(overlap_words)
        
        # Combine overlap with current chunk
        overlapped_chunk = overlap_text + " " + current_chunk
        overlapped_chunks.append(overlapped_chunk)
    
    return overlapped_chunks

def extract_meeting_metadata(content: str) -> Dict:
    """Extract metadata from meeting content."""
    
    metadata = {}
    lines = content.split('\n')
    
    for line in lines[:30]:  # Check first 30 lines
        line = line.strip().lower()
        
        if 'date:' in line or 'meeting date:' in line:
            metadata['date'] = line.split(':', 1)[1].strip()
        elif 'client:' in line or 'company:' in line:
            metadata['client'] = line.split(':', 1)[1].strip()
        elif 'participants:' in line or 'attendees:' in line:
            metadata['participants'] = line.split(':', 1)[1].strip()
        elif 'meeting type:' in line or 'type:' in line:
            metadata['meeting_type'] = line.split(':', 1)[1].strip()
    
    return metadata

if __name__ == "__main__":
    # Load processed meetings
    meetings_file = "data/clean/processed_meetings.json"
    
    if not Path(meetings_file).exists():
        print(f"No processed meetings found at {meetings_file}")
        print("Run process_meetings.py first")
        exit(1)
    
    with open(meetings_file, 'r', encoding='utf-8') as f:
        meetings = json.load(f)
    
    # Create chunks
    chunks = chunk_meeting_content(meetings)
    print(f"Successfully created {len(chunks)} chunks")