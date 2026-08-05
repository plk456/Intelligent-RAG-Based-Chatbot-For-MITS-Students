import os
import json
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

# Load env variables
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
load_dotenv(dotenv_path=os.path.join(root_dir, ".env"))

from Server.rag.document_processor import DocumentProcessor
from Server.rag.vector_store import QdrantVectorStore
from Server.rag.bm25_retriever import BM25Retriever
from Server.rag.hybrid_searcher import HybridSearcher
from Server.rag.streaming import GeminiGenerator

class MITSQueryEngine:
    def __init__(self, dataset_dir: str = None):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))

        
        if dataset_dir is None:
            self.dataset_dir = os.path.join(root_dir, "newmits_dataset")
        else:
            self.dataset_dir = dataset_dir

        self.db_dir = os.path.join(root_dir, "database")
        self.bm25_data_path = os.path.join(self.db_dir, "bm25_chunks.json")
        try:
            os.makedirs(self.db_dir, exist_ok=True)
        except Exception as e:
            print(f"[MITSQueryEngine] Warning: Could not create db_dir: {e}")

        # Components
        self.doc_processor = DocumentProcessor(self.dataset_dir)
        self.vector_store = QdrantVectorStore()
        self.bm25_retriever = BM25Retriever()
        self.hybrid_searcher = HybridSearcher(self.vector_store, self.bm25_retriever)
        self.generator = GeminiGenerator()

        self.is_initialized = False

    def should_reindex(self) -> bool:
        """Determines if the database needs to be reindexed based on dataset file updates."""
        if os.environ.get("VERCEL"):
            return False
        if not os.path.exists(self.bm25_data_path):
            return True
        
        try:
            cache_mtime = os.path.getmtime(self.bm25_data_path)
            for root, _, files in os.walk(self.dataset_dir):
                for file_name in files:
                    if file_name.endswith('.txt'):
                        file_path = os.path.join(root, file_name)
                        if os.path.getmtime(file_path) > cache_mtime:
                            print(f"[MITSQueryEngine] Detected updated dataset file: {file_name}. Automatic reindexing triggered.")
                            return True
        except Exception as e:
            print(f"[MITSQueryEngine] Error checking modification times: {e}")
            return True
            
        return False

    def initialize_system(self, force_reindex: bool = False):
        """Initializes both Qdrant and BM25 search indices."""
        print("[MITSQueryEngine] Initializing RAG System...")
        
        # Check if the source files were updated
        if self.should_reindex():
            print("[MITSQueryEngine] Dataset changes detected or cache missing. Forcing reindex...")
            force_reindex = True
            
        # Check if we have pre-saved chunks for BM25
        chunks_loaded = False
        chunks = []
        
        if os.path.exists(self.bm25_data_path) and not force_reindex:
            try:
                with open(self.bm25_data_path, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                chunks_loaded = True
                print(f"[MITSQueryEngine] Loaded {len(chunks)} pre-processed chunks from storage.")
            except Exception as e:
                print(f"[MITSQueryEngine] Failed to load saved chunks: {e}")

        # If we couldn't load chunks or force_reindex is True, parse files and index
        if not chunks_loaded or force_reindex:
            print("[MITSQueryEngine] Running full document processing and indexing...")
            chunks = self.doc_processor.process_all_documents()
            if not chunks:
                print("[MITSQueryEngine] Error: No document chunks were created. Cannot index.")
                return False
                
            # Index Qdrant
            try:
                self.vector_store.index_documents(chunks)
            except Exception as e:
                print(f"[MITSQueryEngine] Warning: Vector database indexing failed: {e}")

            # Save chunks locally for BM25 reloading on restart
            try:
                with open(self.bm25_data_path, 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[MITSQueryEngine] Failed to save chunks to disk: {e}")

        # Index BM25 (always fits fast in memory from loaded chunks)
        self.bm25_retriever.index_documents(chunks)
        
        # Also ensure Qdrant collection is present
        try:
            self.vector_store.ensure_collection()
        except Exception as e:
            print(f"[MITSQueryEngine] Qdrant ensure collection failed: {e}")

        self.is_initialized = True
        print("[MITSQueryEngine] RAG System Initialization Complete.")
        return True

    def query(self, user_query: str) -> Tuple[str, List[Dict[str, Any]]]:
        if not self.is_initialized:
            success = self.initialize_system()
            if not success:
                return "RAG system initialization failed. Check server logs.", []

        # Perform Hybrid Search using RRF
        contexts = self.hybrid_searcher.search(user_query, top_k=5)
        
        if not contexts:
            return "I couldn't find any relevant information in the MITS database regarding your query.", []

        # Synthesize answer using Gemini
        answer = self.generator.generate_response(user_query, contexts)
        
        return answer, contexts

    def query_stream(self, user_query: str):
        if not self.is_initialized:
            success = self.initialize_system()
            if not success:
                yield json.dumps({"error": "RAG system initialization failed."}) + "\n"
                return

        # Perform Hybrid Search
        contexts = self.hybrid_searcher.search(user_query, top_k=5)
        
        # Format sources
        sources = [
            {"source": ctx["metadata"]["source"], "text": ctx["text"][:200] + "..."}
            for ctx in contexts
        ]
        
        # Yield metadata first (sources)
        yield json.dumps({"sources": sources}) + "\n"

        if not contexts:
            yield json.dumps({"text": "I couldn't find any relevant information in the MITS database regarding your query."}) + "\n"
            return

        # Generate stream chunks
        for chunk in self.generator.generate_response_stream(user_query, contexts):
            yield json.dumps({"text": chunk}) + "\n"

