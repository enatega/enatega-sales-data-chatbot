import os
import json
from pathlib import Path
from typing import List, Dict
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from dotenv import load_dotenv

load_dotenv()

def ingest_to_qdrant(
    chunks_file: str = "data/clean/meeting_chunks.json",
    collection_name: str = None
) -> bool:
    """
    Ingest meeting chunks into Qdrant vector database.
    
    Args:
        chunks_file: Path to chunks JSON file
        collection_name: Qdrant collection name
    
    Returns:
        Success status
    """
    
    # Load environment variables
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = collection_name or os.getenv("COLLECTION_NAME", "sales_meetings")
    
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment")
    
    if not QDRANT_URL:
        raise ValueError("QDRANT_URL not found in environment")
    
    # Load chunks
    chunks_path = Path(chunks_file)
    if not chunks_path.exists():
        print(f"Chunks file not found: {chunks_file}")
        print("Run chunking.py first to create chunks")
        return False
    
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    if not chunks:
        print("No chunks found to ingest")
        return False
    
    print(f"Loading {len(chunks)} chunks into Qdrant collection: {COLLECTION_NAME}")
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    
    # Initialize Qdrant client
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    # Create collection if it doesn't exist
    try:
        collections = qdrant_client.get_collections().collections
        collection_exists = any(c.name == COLLECTION_NAME for c in collections)
        
        if not collection_exists:
            print(f"Creating collection: {COLLECTION_NAME}")
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
        else:
            print(f"Collection {COLLECTION_NAME} already exists")
            
            # Clear existing data
            print("Clearing existing data...")
            try:
                qdrant_client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector={"filter": {"must": [{"key": "source", "match": {"any": ["*"]}}]}}
                )
            except Exception as clear_error:
                print(f"Warning: Could not clear existing data: {clear_error}")
                print("Continuing with ingestion...")
    
    except Exception as e:
        print(f"Error managing collection: {e}")
        return False
    
    # Convert chunks to LangChain documents
    documents = []
    for chunk in chunks:
        doc = Document(
            page_content=chunk['content'],
            metadata=chunk['metadata']
        )
        documents.append(doc)
    
    # Create vector store and add documents
    try:
        vector_store = QdrantVectorStore(
            client=qdrant_client,
            collection_name=COLLECTION_NAME,
            embedding=embeddings
        )
        
        # Add documents in smaller batches with retry logic
        batch_size = 10  # Reduced batch size
        total_batches = (len(documents) + batch_size - 1) // batch_size
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
            
            # Retry logic for each batch
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    vector_store.add_documents(batch)
                    break  # Success, exit retry loop
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"  Retry {attempt + 1}/{max_retries} for batch {batch_num}: {e}")
                        import time
                        time.sleep(2)  # Wait before retry
                    else:
                        print(f"  Failed batch {batch_num} after {max_retries} attempts: {e}")
                        raise e
        
        print(f"Successfully ingested {len(documents)} chunks into Qdrant")
        return True
        
    except Exception as e:
        print(f"Error ingesting documents: {e}")
        return False

def verify_ingestion(collection_name: str = None) -> Dict:
    """
    Verify that documents were successfully ingested.
    
    Args:
        collection_name: Qdrant collection name
    
    Returns:
        Verification results
    """
    
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = collection_name or os.getenv("COLLECTION_NAME", "sales_meetings")
    
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        # Get collection info
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        
        # Count documents
        count_result = qdrant_client.count(
            collection_name=COLLECTION_NAME,
            exact=True
        )
        
        results = {
            "collection_name": COLLECTION_NAME,
            "total_documents": count_result.count,
            "vector_size": collection_info.config.params.vectors.size,
            "distance_metric": collection_info.config.params.vectors.distance.name,
            "status": "success"
        }
        
        print(f"Collection: {COLLECTION_NAME}")
        print(f"Total documents: {count_result.count}")
        print(f"Vector size: {collection_info.config.params.vectors.size}")
        print(f"Distance metric: {collection_info.config.params.vectors.distance.name}")
        
        return results
        
    except Exception as e:
        print(f"Error verifying ingestion: {e}")
        return {"status": "error", "error": str(e)}

def search_test(query: str = "pricing objections", collection_name: str = None) -> List[Dict]:
    """
    Test search functionality.
    
    Args:
        query: Test query
        collection_name: Qdrant collection name
    
    Returns:
        Search results
    """
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = collection_name or os.getenv("COLLECTION_NAME", "sales_meetings")
    
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

        query_vector = embeddings.embed_query(query)
        results = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=3
        ).points

        print(f"Test query: '{query}'")
        print(f"Found {len(results)} results:")

        search_results = []
        for i, hit in enumerate(results, 1):
            payload = hit.payload or {}
            meta = payload.get("metadata", payload)
            content = payload.get("page_content", "")[:200]
            search_results.append({"rank": i, "content": content, "metadata": meta})
            print(f"\n{i}. Source: {meta.get('filename', 'Unknown')}")
            print(f"   Section: {meta.get('section', 'Unknown')}")
            print(f"   Content: {content}")

        return search_results

    except Exception as e:
        print(f"Error testing search: {e}")
        return []

if __name__ == "__main__":
    # Ingest chunks
    success = ingest_to_qdrant()
    
    if success:
        print("\n" + "="*50)
        print("VERIFICATION")
        print("="*50)
        verify_ingestion()
        
        print("\n" + "="*50)
        print("SEARCH TEST")
        print("="*50)
        search_test()
    else:
        print("Ingestion failed")