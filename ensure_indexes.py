import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType
from dotenv import load_dotenv

load_dotenv()

def ensure_qdrant_indexes(collection_name: str = None) -> bool:
    """
    Ensure proper indexes exist in Qdrant collection for optimal search performance.
    
    Args:
        collection_name: Qdrant collection name
    
    Returns:
        Success status
    """
    
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = collection_name or os.getenv("COLLECTION_NAME", "sales_meetings")
    
    if not QDRANT_URL:
        raise ValueError("QDRANT_URL not found in environment")
    
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        # Check if collection exists
        collections = qdrant_client.get_collections().collections
        collection_exists = any(c.name == COLLECTION_NAME for c in collections)
        
        if not collection_exists:
            print(f"Collection {COLLECTION_NAME} doesn't exist. Creating it...")
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
            print(f"Created collection: {COLLECTION_NAME}")
        
        # Create payload indexes for better filtering performance
        indexes_to_create = [
            ("metadata.filename", PayloadSchemaType.KEYWORD),
            ("metadata.client", PayloadSchemaType.KEYWORD),
            ("metadata.date", PayloadSchemaType.KEYWORD),
            ("metadata.section", PayloadSchemaType.KEYWORD),
            ("metadata.meeting_type", PayloadSchemaType.KEYWORD),
            ("metadata.source", PayloadSchemaType.KEYWORD)
        ]
        
        print(f"Creating payload indexes for collection: {COLLECTION_NAME}")
        
        for field_name, schema_type in indexes_to_create:
            try:
                qdrant_client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name=field_name,
                    field_schema=schema_type
                )
                print(f"✓ Created index for field: {field_name}")
            except Exception as e:
                if "already exists" in str(e).lower() or "conflict" in str(e).lower():
                    print(f"✓ Index for field '{field_name}' already exists")
                else:
                    print(f"✗ Failed to create index for field '{field_name}': {e}")
        
        # Get collection info
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        
        print(f"\nCollection Summary:")
        print(f"Name: {COLLECTION_NAME}")
        print(f"Vector size: {collection_info.config.params.vectors.size}")
        print(f"Distance metric: {collection_info.config.params.vectors.distance.name}")
        print(f"Points count: {collection_info.points_count}")
        
        return True
        
    except Exception as e:
        print(f"Error ensuring indexes: {e}")
        return False

def list_collection_info(collection_name: str = None) -> dict:
    """
    Get detailed information about the collection.
    
    Args:
        collection_name: Qdrant collection name
    
    Returns:
        Collection information
    """
    
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = collection_name or os.getenv("COLLECTION_NAME", "sales_meetings")
    
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        # Get collection info
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        
        # Get sample points to understand data structure
        sample_points = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=3,
            with_payload=True,
            with_vectors=False
        )[0]
        
        info = {
            "collection_name": COLLECTION_NAME,
            "points_count": collection_info.points_count,
            "vector_size": collection_info.config.params.vectors.size,
            "distance_metric": collection_info.config.params.vectors.distance.name,
            "sample_payloads": []
        }
        
        for point in sample_points:
            if point.payload:
                meta = point.payload.get("metadata", point.payload)
                info["sample_payloads"].append({
                    "id": point.id,
                    "payload_keys": list(point.payload.keys()),
                    "filename": meta.get("filename", "N/A"),
                    "client": meta.get("client", "N/A"),
                    "section": meta.get("section", "N/A")
                })
        
        print(f"Collection: {COLLECTION_NAME}")
        print(f"Points: {info['points_count']}")
        print(f"Vector size: {info['vector_size']}")
        print(f"Distance: {info['distance_metric']}")
        
        if info["sample_payloads"]:
            print(f"\nSample data structure:")
            for i, sample in enumerate(info["sample_payloads"], 1):
                print(f"{i}. File: {sample['filename']}")
                print(f"   Client: {sample['client']}")
                print(f"   Section: {sample['section']}")
                print(f"   Payload keys: {sample['payload_keys']}")
        
        return info
        
    except Exception as e:
        print(f"Error getting collection info: {e}")
        return {}

def cleanup_collection(collection_name: str = None, confirm: bool = False) -> bool:
    """
    Delete all data from collection (use with caution).
    
    Args:
        collection_name: Qdrant collection name
        confirm: Confirmation flag
    
    Returns:
        Success status
    """
    
    if not confirm:
        print("This will delete ALL data from the collection!")
        response = input("Type 'DELETE' to confirm: ")
        if response != "DELETE":
            print("Operation cancelled")
            return False
    
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = collection_name or os.getenv("COLLECTION_NAME", "sales_meetings")
    
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        # Delete collection
        qdrant_client.delete_collection(COLLECTION_NAME)
        print(f"Deleted collection: {COLLECTION_NAME}")
        
        return True
        
    except Exception as e:
        print(f"Error deleting collection: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "info":
            list_collection_info()
        elif command == "cleanup":
            cleanup_collection()
        else:
            print("Unknown command. Use 'info' or 'cleanup'")
    else:
        # Default: ensure indexes
        success = ensure_qdrant_indexes()
        if success:
            print("\n" + "="*50)
            list_collection_info()