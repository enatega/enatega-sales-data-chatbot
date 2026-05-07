import os
import time
from pathlib import Path
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Sales Meeting Chatbot API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")

@app.get("/app.js")
async def serve_js():
    return FileResponse("frontend/app.js")

@app.get("/style.css")
async def serve_css():
    return FileResponse("frontend/style.css")

# ---------- Config ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "sales_meetings")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found")

# ---------- Initialize components ----------
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, request_timeout=30)
llm = ChatOpenAI(
    temperature=0.7, 
    model="gpt-4o-mini", 
    openai_api_key=OPENAI_API_KEY,
    request_timeout=30,
    max_retries=2
)

qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30)

# Load master summary once at startup
MASTER_SUMMARY = ""
master_summary_path = Path("data/clean/master_summary.txt")
if master_summary_path.exists():
    MASTER_SUMMARY = master_summary_path.read_text(encoding="utf-8")
    print(f"✅ Master summary loaded: {len(MASTER_SUMMARY)} characters")
else:
    print("⚠️ Master summary not found. Run generate_master_summary.py first.")

# Session memory storage
session_memories: dict[str, list] = {}

def get_history(session_id: str) -> list:
    if session_id not in session_memories:
        session_memories[session_id] = []
    return session_memories[session_id]

# ---------- Query classifier ----------
STRATEGIC_KEYWORDS = [
    "strategy", "strategies", "recommend", "suggestion", "suggest", "improve", "improvement",
    "pattern", "trend", "common", "most", "top", "best", "worst", "typical", "usually",
    "objection", "objections", "pricing", "price", "feature", "features", "competitor",
    "competitors", "region", "industry", "industries", "segment", "marketing", "pitch",
    "plan", "approach", "how should", "what should", "why do", "which clients",
    "overall", "across", "all clients", "all meetings", "generally", "insight", "insights",
    "win", "lose", "lost", "deal", "convert", "conversion", "sales cycle", "follow up"
]

def is_strategic_question(message: str) -> bool:
    msg = message.lower()
    return any(kw in msg for kw in STRATEGIC_KEYWORDS)

# ---------- Prompt Templates ----------
STRATEGIC_PROMPT = (
    "You are an expert Sales Strategist AI for Enatega — a food delivery platform solution.\n"
    "You have comprehensive knowledge from 250+ real client sales meetings summarized below.\n\n"
    "Use this knowledge to give specific, actionable, data-driven answers.\n"
    "Reference patterns, client names, regions, and real examples from the data.\n"
    "If asked for a plan or strategy, provide structured step-by-step guidance.\n\n"
    "KNOWLEDGE BASE FROM 250+ MEETINGS:\n{master_summary}\n\n"
    "Chat History:\n{chat_history}\n\n"
    "Question: {question}\n"
    "Answer:"
)

SPECIFIC_PROMPT = (
    "You are a Sales Assistant AI for Enatega — a food delivery platform solution.\n"
    "Answer the question using the relevant meeting excerpts provided below.\n"
    "Be specific, reference client names and meetings where relevant.\n\n"
    "Relevant Meeting Excerpts:\n{context}\n\n"
    "Chat History:\n{chat_history}\n\n"
    "Question: {question}\n"
    "Answer:"
)

# ---------- request/response ----------
class ChatReq(BaseModel):
    session_id: str
    message: str

class ChatResp(BaseModel):
    answer: str
    sources: List[str]
    used_chunks: int
    latency_ms: int

@app.post("/chat", response_model=ChatResp)
async def chat_endpoint(req: ChatReq):
    start_time = time.time()

    try:
        history = get_history(req.session_id)
        history_text = "".join([f"{m['role']}: {m['content']}\n" for m in history[-6:]])
        sources = []
        used_chunks = 0

        if is_strategic_question(req.message):
            # --- STRATEGIC MODE: use master summary ---
            print(f"[STRATEGIC] {req.message}")
            full_prompt = STRATEGIC_PROMPT.format(
                master_summary=MASTER_SUMMARY,
                chat_history=history_text,
                question=req.message
            )
            used_chunks = 51  # all batches
        else:
            # --- SPECIFIC MODE: semantic search ---
            print(f"[SPECIFIC] {req.message}")
            try:
                query_vector = embeddings.embed_query(req.message)
                search_result = qdrant_client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=query_vector,
                    limit=10
                ).points
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

            docs = []
            for hit in search_result:
                payload = hit.payload or {}
                content = payload.get('page_content', '') or payload.get('content', '')
                meta = payload.get('metadata', payload)
                if content:
                    docs.append(content)
                filename = meta.get('filename', meta.get('source', ''))
                if filename:
                    sources.append(filename)

            context = "\n\n".join([d for d in docs if d.strip()]) or "No relevant meeting data found."
            used_chunks = len(docs)
            full_prompt = SPECIFIC_PROMPT.format(
                context=context,
                chat_history=history_text,
                question=req.message
            )

        try:
            response = llm.invoke(full_prompt).content
        except Exception as e:
            print(f"LLM error: {e}")
            response = "I encountered an issue generating a response. Please try again."

        history.append({"role": "Human", "content": req.message})
        history.append({"role": "Assistant", "content": response})

        return ChatResp(
            answer=response,
            sources=list(set(sources)),
            used_chunks=used_chunks,
            latency_ms=int((time.time() - start_time) * 1000)
        )

    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "collection": COLLECTION_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)