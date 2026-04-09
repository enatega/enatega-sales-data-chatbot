@echo off
echo 🤖 Sales Meeting Chatbot Pipeline
echo ==================================
echo.

REM Load .env file
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" if not "%%A:~0,1%%"=="#" set %%A=%%B
    )
)

REM Check for required environment variables
if "%OPENAI_API_KEY%"=="" (
    echo ❌ OPENAI_API_KEY not found in environment
    echo    Please set it in your .env file
    pause
    exit /b 1
)

if "%QDRANT_URL%"=="" (
    echo ❌ QDRANT_URL not found in environment
    echo    Please set it in your .env file
    pause
    exit /b 1
)

echo ✅ Environment variables found
echo.

REM Step 0: Convert DOCX files if they exist
echo 📄 Step 0: Converting DOCX files...
echo ==================================
if exist "data\raw\*.docx" (
    echo Found .docx files, converting to text format...
    python convert_docx.py convert
    if errorlevel 1 (
        echo ❌ Failed to convert DOCX files
        pause
        exit /b 1
    )
    echo ✅ DOCX files converted successfully
) else (
    echo No .docx files found, skipping conversion
)
echo.

REM Step 1: Clean transcripts with LLM
echo 🧹 Step 1: Cleaning transcripts with LLM...
echo ==========================================
python clean_transcripts.py
if errorlevel 1 (
    echo ❌ Failed to clean transcripts
    pause
    exit /b 1
)
echo ✅ Transcripts cleaned successfully
echo.

REM Step 2: Process meeting files
echo 📁 Step 2: Processing meeting files...
echo ======================================
python process_meetings.py
if errorlevel 1 (
    echo ❌ Failed to process meeting files
    pause
    exit /b 1
)
echo ✅ Meeting files processed successfully
echo.

REM Step 3: Create chunks
echo 🧩 Step 3: Creating chunks...
echo =============================
python chunking.py
if errorlevel 1 (
    echo ❌ Failed to create chunks
    pause
    exit /b 1
)
echo ✅ Chunks created successfully
echo.

REM Step 4: Ingest into Qdrant
echo 📦 Step 4: Ingesting into Qdrant...
echo ===================================
python ingest_qdrant.py
if errorlevel 1 (
    echo ❌ Failed to ingest into Qdrant
    pause
    exit /b 1
)
echo ✅ Data ingested successfully
echo.

REM Step 5: Ensure indexes
echo 🔍 Step 5: Ensuring indexes...
echo ==============================
python ensure_indexes.py
if errorlevel 1 (
    echo ❌ Failed to ensure indexes
    pause
    exit /b 1
)
echo ✅ Indexes ensured successfully
echo.

REM Final summary
echo 🎉 Pipeline completed successfully!
echo ==================================
echo.
echo Next steps:
echo 1. Start the API server: uvicorn api.main:app --reload --port 8000
echo 2. Test the endpoint: curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"session_id\":\"test\",\"message\":\"What pricing concerns did clients have?\"}"
echo 3. Open the frontend: http://127.0.0.1:8000
echo.
echo Happy querying! 🚀
pause