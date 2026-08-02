import re
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi

class BM25Retriever:
    def __init__(self):
        self.bm25 = None
        self.chunks = []

    def tokenize(self, text: str) -> List[str]:
        # Lowercase and extract alphanumeric tokens
        return re.findall(r'\w+', text.lower())

    def index_documents(self, chunks: List[Dict[str, Any]]):
        self.chunks = chunks
        if not chunks:
            print("[BM25Retriever] Warning: No chunks provided for BM25 indexing.")
            return

        print(f"[BM25Retriever] Indexing {len(chunks)} chunks with BM25...")
        corpus_tokens = [self.tokenize(chunk["text"]) for chunk in chunks]
        self.bm25 = BM25Okapi(corpus_tokens)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.bm25 or not self.chunks:
            return []

        query_tokens = self.tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # Get indices of top scores
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for idx in top_indices:
            # Only include results with positive scores
            if scores[idx] > 0:
                results.append({
                    "text": self.chunks[idx]["text"],
                    "metadata": self.chunks[idx]["metadata"],
                    "score": float(scores[idx])
                })
        return results
