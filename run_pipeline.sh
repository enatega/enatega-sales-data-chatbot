#!/bin/bash

# Sales Meeting Chatbot Pipeline Runner
# This script runs the complete pipeline: convert docx → process → chunk → ingest → ensure indexes

echo "🤖 Sales Meeting Chatbot Pipeline"
echo "=================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: Virtual environment not detected"
    echo "   Consider running: source .venv/bin/activate"
    echo ""
fi

# Check for required environment variables
if [[ -z "$OPENAI_API_KEY" ]]; then
    echo "❌ OPENAI_API_KEY not found in environment"
    echo "   Please set it in your .env file"
    exit 1
fi

if [[ -z "$QDRANT_URL" ]]; then
    echo "❌ QDRANT_URL not found in environment"
    echo "   Please set it in your .env file"
    exit 1
fi

echo "✅ Environment variables found"
echo ""

# Step 0: Convert DOCX files if they exist
echo "📄 Step 0: Converting DOCX files..."
echo "=================================="
if ls data/raw/*.docx 1> /dev/null 2>&1; then
    echo "Found .docx files, converting to text format..."
    python convert_docx.py convert
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to convert DOCX files"
        exit 1
    fi
    
    echo "✅ DOCX files converted successfully"
else
    echo "No .docx files found, skipping conversion"
fi
echo ""

# Step 1: Process meeting files
echo "📁 Step 1: Processing meeting files..."
echo "======================================"
python process_meetings.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to process meeting files"
    exit 1
fi

echo "✅ Meeting files processed successfully"
echo ""

# Step 2: Create chunks
echo "🧩 Step 2: Creating chunks..."
echo "============================="
python chunking.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to create chunks"
    exit 1
fi

echo "✅ Chunks created successfully"
echo ""

# Step 3: Ingest into Qdrant
echo "📦 Step 3: Ingesting into Qdrant..."
echo "==================================="
python ingest_qdrant.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to ingest into Qdrant"
    exit 1
fi

echo "✅ Data ingested successfully"
echo ""

# Step 4: Ensure indexes
echo "🔍 Step 4: Ensuring indexes..."
echo "=============================="
python ensure_indexes.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to ensure indexes"
    exit 1
fi

echo "✅ Indexes ensured successfully"
echo ""

# Final summary
echo "🎉 Pipeline completed successfully!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Start the API server: uvicorn api.main:app --reload --port 8000"
echo "2. Test the endpoint: curl -X POST http://127.0.0.1:8000/chat -H 'Content-Type: application/json' -d '{\"session_id\":\"test\",\"message\":\"What pricing concerns did clients have?\"}'"
echo "3. Open the frontend: http://127.0.0.1:8000"
echo ""
echo "Happy querying! 🚀"