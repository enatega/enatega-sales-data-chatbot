import os
import re
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a sales intelligence assistant. Convert the raw meeting transcript into clean, dense informational paragraphs.

Rules:
- Remove all timestamps, speaker labels, filler words (uh, um, yeah yeah, okay okay, etc.)
- Merge related dialogue into coherent paragraphs by topic
- Preserve all factual details: product names, pricing, features, objections, integrations, next steps, client concerns
- Write in third-person past tense (e.g. "The client asked about...", "Rami explained that...")
- Group into logical sections: Meeting Overview, Product Discussion, Client Requirements, Objections & Concerns, Next Steps
- Each section should be a dense paragraph, not bullet points
- Do not invent or assume anything not present in the transcript"""

def clean_transcript(raw_text: str, filename: str) -> str:
    # Extract meeting name from filename for context
    meeting_name = Path(filename).stem

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Meeting: {meeting_name}\n\nTranscript:\n{raw_text}"}
        ],
        temperature=0.2,
        max_tokens=2000
    )
    return response.choices[0].message.content.strip()

def clean_all_transcripts(raw_dir: str = "data/raw", output_dir: str = "data/clean/cleaned"):
    raw_path = Path(raw_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    txt_files = [f for f in raw_path.glob("*.txt") if f.name != ".gitkeep"]

    if not txt_files:
        print("No .txt files found in data/raw/")
        return

    print(f"Found {len(txt_files)} transcript(s) to clean...\n")

    for txt_file in txt_files:
        out_file = out_path / txt_file.name
        if out_file.exists():
            print(f"  [skip] {txt_file.name} (already cleaned)")
            continue

        print(f"  Cleaning: {txt_file.name}")
        raw_text = txt_file.read_text(encoding="utf-8")

        # Basic pre-clean: collapse excessive whitespace
        raw_text = re.sub(r'\n{3,}', '\n\n', raw_text).strip()

        try:
            cleaned = clean_transcript(raw_text, txt_file.name)
            out_file.write_text(cleaned, encoding="utf-8")
            print(f"  ✅ Saved: {out_file.name}")
        except Exception as e:
            print(f"  ❌ Failed: {txt_file.name} — {e}")

    print(f"\nDone. Cleaned files saved to: {out_path}")

if __name__ == "__main__":
    clean_all_transcripts()
