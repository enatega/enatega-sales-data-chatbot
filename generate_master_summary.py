import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CLEANED_DIR = "data/clean/cleaned"
OUTPUT_FILE = "data/clean/master_summary.txt"
BATCH_SIZE = 5  # files per batch

BATCH_PROMPT = """You are analyzing a batch of sales meeting transcripts for Enatega (a food delivery platform solution).
Extract and summarize the following from these meetings:

1. Client objections and concerns raised (and how they were handled)
2. Pricing discussions, budget concerns, preferred pricing models
3. Feature requests and product feedback
4. Competitor mentions and comparisons
5. Client industries, regions, and business types
6. What convinced clients to move forward (or not)
7. Common questions asked by clients
8. Integration requirements (POS, payment gateways, etc.)
9. Sales cycle patterns (timeline, decision makers)
10. Any red flags or deal breakers mentioned

Be specific and factual. Reference client names where relevant.

Meetings:
{content}"""


def read_files_in_batches(cleaned_dir: str, batch_size: int):
    files = sorted(Path(cleaned_dir).glob("*.txt"))
    print(f"Total files: {len(files)}")
    for i in range(0, len(files), batch_size):
        yield files[i:i + batch_size]


def summarize_batch(files: list, batch_num: int) -> str:
    combined = ""
    for f in files:
        content = f.read_text(encoding="utf-8").strip()
        combined += f"\n\n--- {f.stem} ---\n{content}"

    print(f"  Summarizing batch {batch_num} ({len(files)} files)...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": BATCH_PROMPT.format(content=combined)}
        ],
        temperature=0.2,
        max_tokens=4000
    )
    return response.choices[0].message.content.strip()


def generate_master_summary():
    output_path = Path(OUTPUT_FILE)

    print("Step 1: Summarizing files in batches...\n")
    batch_summaries = []
    for batch_num, batch_files in enumerate(read_files_in_batches(CLEANED_DIR, BATCH_SIZE), 1):
        summary = summarize_batch(batch_files, batch_num)
        batch_summaries.append(f"=== BATCH {batch_num} ===\n{summary}")
        print(f"  ✅ Batch {batch_num} done")

    print(f"\nStep 2: Combining {len(batch_summaries)} batch summaries into master knowledge base...")
    master_summary = "\n\n".join(batch_summaries)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(master_summary, encoding="utf-8")
    print(f"\n✅ Master summary saved to: {OUTPUT_FILE}")
    print(f"   Length: {len(master_summary)} characters")
    print(f"   Batches: {len(batch_summaries)}")


if __name__ == "__main__":
    generate_master_summary()
