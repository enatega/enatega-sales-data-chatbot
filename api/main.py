import os
import time
from typing import List, Optional
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

# Session memory storage
session_memories: dict[str, list] = {}

def get_history(session_id: str) -> list:
    if session_id not in session_memories:
        session_memories[session_id] = []
    return session_memories[session_id]

# ---------- Prompt Template ----------
SALES_PROMPT_TEMPLATE = (
    "You are a Sales Assistant AI that helps sales representatives query information from previous client meetings. "
    "You have access to meeting transcripts, summaries, and client interactions to provide insights about:\n\n"
    
    "• Client objections, concerns, and feedback\n"
    "• Pricing discussions and negotiations\n"
    "• Feature requests and product feedback\n"
    "• Competitor comparisons mentioned by clients\n"
    "• Implementation concerns and technical questions\n"
    "• Industry-specific requirements and use cases\n"
    "• Decision-making processes and timelines\n"
    "• Stakeholder involvement and buying committees\n\n"
    
    "RESPONSE GUIDELINES:\n"
    "• Provide specific, actionable insights from the meeting data\n"
    "• When possible, reference specific client meetings or contexts\n"
    "• Highlight patterns across multiple client interactions\n"
    "• Be concise but comprehensive in your responses\n"
    "• If you don't have relevant information, clearly state that\n"
    "• Focus on helping sales reps prepare for future meetings\n"
    "• Suggest follow-up questions or strategies when appropriate\n\n"
    
    "EXAMPLE RESPONSES:\n"
    "• 'Based on 3 recent enterprise meetings, clients commonly ask about data security certifications...'\n"
    "• 'In the TechCorp meeting last month, they mentioned budget constraints around Q4...'\n"
    "• 'Several healthcare clients have requested HIPAA compliance documentation...'\n\n"
    
    "Context from previous meetings:\n{context}\n\n"
    "Chat History:\n{chat_history}\n\n"
    "Sales Rep Question: {question}\n"
    "Assistant:"
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
        # Simple similarity search using qdrant client directly
        print(f"Searching for: {req.message}")
        
        try:
            query_vector = embeddings.embed_query(req.message)
            print("Query vector created successfully")
        except Exception as embed_error:
            print(f"Embedding error: {embed_error}")
            raise HTTPException(status_code=500, detail=f"Embedding failed: {str(embed_error)}")
        
        try:
            search_result = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=5
            ).points
            print(f"Found {len(search_result)} results")
        except Exception as search_error:
            print(f"Search error: {search_error}")
            raise HTTPException(status_code=500, detail=f"Search failed: {str(search_error)}")
        
        # Extract content and metadata from search results
        docs = []
        sources = []
        
        for hit in search_result:
            # Debug: print the structure
            print(f"Hit payload keys: {hit.payload.keys() if hit.payload else 'No payload'}")
            
            # Try different payload structures
            content = ""
            metadata = {}
            
            if hit.payload:
                # Try direct content access
                content = hit.payload.get('page_content', '') or hit.payload.get('content', '')
                
                # Try nested metadata
                if 'metadata' in hit.payload:
                    metadata = hit.payload['metadata']
                else:
                    # Use payload directly as metadata
                    metadata = hit.payload
            
            if content:
                docs.append(content)
                
            # Extract filename from metadata
            filename = metadata.get('filename', metadata.get('source', 'Unknown'))
            if filename and filename != 'Unknown':
                sources.append(filename)
        
        # Create context from documents
        context = "\n\n".join([doc for doc in docs if doc.strip()])
        
        # If no context found, provide a helpful message
        if not context.strip():
            context = "No relevant meeting data found for this query."
        
        # Get history for this session
        history = get_history(req.session_id)
        history_text = "".join([f"{m['role']}: {m['content']}\n" for m in history[-10:]])

        # Create the prompt
        full_prompt = SALES_PROMPT_TEMPLATE.format(
            context=context,
            chat_history=history_text,
            question=req.message
        )
        
        # Get response from LLM
        print("Sending to LLM...")
        try:
            response = llm.invoke(full_prompt).content
            print("LLM response received")
        except Exception as llm_error:
            print(f"LLM error: {llm_error}")
            response = f"I found {len(docs)} relevant meeting excerpts but encountered an issue. Sources: {', '.join(sources[:3]) if sources else 'your query'}."

        # Save to history
        history = get_history(req.session_id)
        history.append({"role": "Human", "content": req.message})
        history.append({"role": "Assistant", "content": response})
        
        # Remove duplicate sources
        sources = list(set(sources))
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return ChatResp(
            answer=response,
            sources=sources,
            used_chunks=len(docs),
            latency_ms=latency_ms
        )
        
    except Exception as e:
        print(f"Chat error: {str(e)}")  # Debug logging
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "collection": COLLECTION_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)