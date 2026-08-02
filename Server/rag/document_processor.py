import os
import re
from typing import List, Dict, Any

class DocumentProcessor:
    def __init__(self, dataset_dir: str, chunk_size: int = 500, chunk_overlap: int = 100):
        self.dataset_dir = dataset_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def clean_text(self, text: str) -> str:
        # Replace multiple consecutive newlines or whitespace with cleaner formatting
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()

    def chunk_document(self, text: str, source_name: str, category: str = "General") -> List[Dict[str, Any]]:
        cleaned_text = self.clean_text(text)
        chunks = []
        
        start = 0
        text_len = len(cleaned_text)
        chunk_idx = 0
        
        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            
            # Try to expand/shrink to end of a paragraph or sentence to avoid cutting mid-sentence
            if end < text_len:
                # Look for nearest sentence boundary or newline in the last 100 characters
                search_space = cleaned_text[max(start, end - 100):end]
                boundary_match = list(re.finditer(r'[\.\?\!\n]', search_space))
                if boundary_match:
                    # Align to the last boundary found
                    last_idx = boundary_match[-1].end()
                    end = max(start, end - 100) + last_idx
            
            chunk_content = cleaned_text[start:end].strip()
            if chunk_content:
                # Prepend semantic context to each chunk to help vector/BM25 retrieval and prevent hallucinations
                contextual_text = f"[Category/Department: {category} | Source: {source_name}]\n{chunk_content}"
                chunks.append({
                    "text": contextual_text,
                    "metadata": {
                        "source": source_name,
                        "category": category,
                        "chunk_id": f"{source_name}_{chunk_idx}"
                    }
                })
                chunk_idx += 1
            
            # Step forward
            if end >= text_len:
                break
            start = end - self.chunk_overlap
            if start >= end:
                start = end - 50 # Safeguard to ensure forward progress
                
        return chunks

    def process_all_documents(self) -> List[Dict[str, Any]]:
        all_chunks = []
        if not os.path.exists(self.dataset_dir):
            print(f"[DocumentProcessor] Warning: Dataset directory {self.dataset_dir} does not exist.")
            return all_chunks
            
        for root, dirs, files in os.walk(self.dataset_dir):
            for file_name in files:
                if file_name.endswith('.txt'):
                    if file_name == 'combined_scraped_data.txt':
                        if len([f for f in files if f.endswith('.txt')]) > 1:
                            continue
                            
                    file_path = os.path.join(root, file_name)
                    # Determine category based on subdirectory name
                    rel_dir = os.path.relpath(root, self.dataset_dir)
                    category = rel_dir if rel_dir != "." else "General"
                    # Replace underscores with spaces for cleaner semantic reading
                    category_clean = category.replace("_", " ")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        file_chunks = self.chunk_document(content, file_name, category=category_clean)
                        all_chunks.extend(file_chunks)
                    except Exception as e:
                        print(f"[DocumentProcessor] Error reading {file_path}: {e}")
                        
        print(f"[DocumentProcessor] Processed documents, generated {len(all_chunks)} chunks.")
        return all_chunks
