import os
import time
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any, Optional

class QdrantVectorStore:
    def __init__(self, collection_name: str = "mits_knowledge"):
        self.collection_name = collection_name
        
        # Determine database path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(current_dir)
        db_dir = os.path.join(app_dir, "database", "qdrant_db")
        os.makedirs(db_dir, exist_ok=True)
        
        # Initialize client (uses local persistence)
        self.client = QdrantClient(path=db_dir)
        
        # Configure Gemini API
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            print("[QdrantVectorStore] WARNING: GEMINI_API_KEY not found in environment. Please add it to your .env file.")

        # gemini-embedding-2 yields 3072 dimensions
        self.vector_dim = 3072

    def ensure_collection(self, force_recreate: bool = False):
        collections = [col.name for col in self.client.get_collections().collections]
        if self.collection_name in collections and not force_recreate:
            print(f"[QdrantVectorStore] Collection '{self.collection_name}' already exists.")
            return

        print(f"[QdrantVectorStore] Creating Qdrant collection '{self.collection_name}'...")
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_dim, distance=Distance.COSINE)
        )

    def _call_with_retry(self, func, *args, **kwargs):
        max_retries = 6
        delay = 2
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                err_msg = str(e).lower()
                is_rate_limit = any(term in err_msg for term in ["429", "quota", "resource_exhausted", "limit"])
                if is_rate_limit and attempt < max_retries - 1:
                    sleep_time = delay * (2 ** attempt)
                    print(f"[QdrantVectorStore] Rate limit hit. Retrying in {sleep_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(sleep_time)
                else:
                    raise e

    def get_embedding(self, text: str, is_query: bool = False) -> List[float]:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            # Return a dummy vector if API key is missing to prevent total server crash
            return [0.0] * self.vector_dim
            
        task_type = "retrieval_query" if is_query else "retrieval_document"
        try:
            response = self._call_with_retry(
                genai.embed_content,
                model="models/gemini-embedding-2",
                content=text,
                task_type=task_type
            )
            return response['embedding']
        except Exception as e:
            print(f"[QdrantVectorStore] Error generating embedding: {e}")
            raise e

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return [[0.0] * self.vector_dim for _ in texts]
            
        try:
            response = self._call_with_retry(
                genai.embed_content,
                model="models/gemini-embedding-2",
                content=texts,
                task_type="retrieval_document"
            )
            return response['embedding']
        except Exception as e:
            print(f"[QdrantVectorStore] Error in batch embeddings: {e}. Falling back to single embeddings.")
            # Fallback to single embedding generation
            return [self.get_embedding(t) for t in texts]

    def index_documents(self, chunks: List[Dict[str, Any]]):
        self.ensure_collection(force_recreate=True)
        
        points = []
        batch_size = 50
        
        print(f"[QdrantVectorStore] Indexing {len(chunks)} chunks into Qdrant in batches of {batch_size}...")
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            batch_texts = [item["text"] for item in batch]
            
            try:
                embeddings = self.get_embeddings_batch(batch_texts)
            except Exception as e:
                print(f"[QdrantVectorStore] Failed to generate embeddings for batch {i//batch_size}. Skipping batch.")
                continue

            for idx, item in enumerate(batch):
                global_idx = i + idx
                points.append(
                    PointStruct(
                        id=global_idx,
                        vector=embeddings[idx],
                        payload={
                            "text": item["text"],
                            "metadata": item["metadata"]
                        }
                    )
                )

        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            print(f"[QdrantVectorStore] Successfully upserted {len(points)} points to Qdrant.")

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vector = self.get_embedding(query, is_query=True)
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k
        )
        
        search_results = []
        for res in results:
            search_results.append({
                "text": res.payload["text"],
                "metadata": res.payload["metadata"],
                "score": res.score
            })
        return search_results
