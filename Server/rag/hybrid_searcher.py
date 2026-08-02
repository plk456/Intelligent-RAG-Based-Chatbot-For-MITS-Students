from typing import List, Dict, Any

class HybridSearcher:
    def __init__(self, vector_store, bm25_retriever):
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever

    def search(self, query: str, top_k: int = 5, rrf_k: int = 60) -> List[Dict[str, Any]]:
        # Retrieve candidate docs from both sources (pull more candidates, e.g., 20, to fuse)
        try:
            vector_results = self.vector_store.search(query, top_k=20)
        except Exception as e:
            print(f"[HybridSearcher] Vector store search failed: {e}. Falling back to pure BM25 search.")
            vector_results = []
            
        bm25_results = self.bm25_retriever.search(query, top_k=20)


        # Map to identify unique documents by their chunk_id
        doc_map = {}
        
        # Track ranks
        for idx, doc in enumerate(vector_results):
            chunk_id = doc["metadata"]["chunk_id"]
            doc_map[chunk_id] = {
                "text": doc["text"],
                "metadata": doc["metadata"],
                "vector_rank": idx + 1,
                "bm25_rank": None
            }

        for idx, doc in enumerate(bm25_results):
            chunk_id = doc["metadata"]["chunk_id"]
            if chunk_id in doc_map:
                doc_map[chunk_id]["bm25_rank"] = idx + 1
            else:
                doc_map[chunk_id] = {
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "vector_rank": None,
                    "bm25_rank": idx + 1
                }

        # Calculate Reciprocal Rank Fusion (RRF) scores
        fused_results = []
        for chunk_id, info in doc_map.items():
            rrf_score = 0.0
            if info["vector_rank"] is not None:
                rrf_score += 1.0 / (rrf_k + info["vector_rank"])
            if info["bm25_rank"] is not None:
                rrf_score += 1.0 / (rrf_k + info["bm25_rank"])
                
            fused_results.append({
                "text": info["text"],
                "metadata": info["metadata"],
                "rrf_score": rrf_score
            })

        # Sort by RRF score descending
        fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
        
        # Return top_k
        return fused_results[:top_k]
