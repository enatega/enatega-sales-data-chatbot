# 🤖 Sales Meeting Chatbot

An AI-powered chatbot that helps sales representatives query information from previous client meetings using **RAG (Retrieval-Augmented Generation)**.  
It processes sales meeting transcripts and summaries, chunks content, embeds it into **Qdrant**, and serves a chatbot API with **FastAPI + LangChain + OpenAI**.

---

## ✨ Features
- 📁 **Manual Data Upload** from Google Drive (transcripts & summaries)
- 📝 **Text Processing** of meeting transcripts into structured format
- 🧩 **Smart Chunking** (token-based with overlap for context retention)
- 📦 **Vector Storage** in Qdrant (Cloud or Local)
- 🧠 **RAG Chatbot API** powered by LangChain & OpenAI
- 🌐 **Simple Chat Widget** for sales team
- 🔄 **Manual Refresh Workflow** (process → chunk → ingest → deploy)
- ☁️ **Deployable** on Render / Railway / AWS / Docker

---

## 📂 Project Structure

```
sales_chatbot/
├── api/                     # FastAPI app
│   └── main.py
├── data/
│   ├── raw/                 # Raw meeting transcripts/summaries
│   └── clean/               # Processed text + chunks
├── frontend/                # Simple HTML/JS chatbot widget
├── process_meetings.py      # Processes meeting transcripts
├── chunking.py              # Splits text into chunks for embeddings
├── ingest_qdrant.py         # Ingests chunks into Qdrant
├── ensure_indexes.py        # Ensures indexes exist in Qdrant
├── run_pipeline.sh          # End-to-end pipeline runner
├── requirements.txt         # Python dependencies
├── Dockerfile               # For containerized deployment
└── .github/workflows/       # GitHub Actions automation
```

---

## ⚙️ Setup

### 1. Clone the repo
```bash
git clone https://github.com/your-username/sales_chatbot.git
cd sales_chatbot
```

### 2. Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key
QDRANT_URL=https://your-qdrant-instance.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key
COLLECTION_NAME=sales_meetings
```

---

## 🛠️ Usage

### 1. Add meeting data
Place your meeting transcripts and summaries in `data/raw/` folder.

### 2. Run the pipeline
```bash
./run_pipeline.sh
```

This will:
- Process meeting transcripts and summaries
- Chunk content
- Ingest into Qdrant
- Ensure indexes

### 3. Run chatbot locally
```bash
uvicorn api.main:app --reload --port 8000
```

Test endpoint:
```bash
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sales_rep_1","message":"What pricing concerns did clients have?"}'
```

---

## 🌐 Deployment

### Docker
```bash
docker build -t sales-chatbot .
docker run -p 8000:8000 sales-chatbot
```

### Render (recommended)
1. Push repo to GitHub
2. Create a Web Service on Render
3. Point to this repo
4. Expose port 8000

Your bot will be live at `https://<your-app>.onrender.com`.

---

## 💬 Embedding Chat Widget

Add this snippet to your sales dashboard:

```html
<div id="sales-chatbot"></div>
<link rel="stylesheet" href="https://sales-bot.onrender.com/style.css">
<script src="https://sales-bot.onrender.com/app.js"></script>
<script>
  SalesChatbotWidget.init({
    endpoint: "https://sales-bot.onrender.com/chat",
    title: "Sales Assistant 🤖",
    subtitle: "Query previous client meetings"
  });
</script>
```

---

## 🧪 Example Queries

- What pricing objections did clients mention?
- Which features were most requested by enterprise clients?
- What concerns did clients have about implementation?
- Show me feedback about our competitor comparisons
- What questions do clients ask about security?
- Which industries showed most interest in our product?

---

## 📜 License

MIT License © 2025