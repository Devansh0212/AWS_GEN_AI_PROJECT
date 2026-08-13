import os
import sys
import json
import math
from typing import List, Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.rag.document_loader import load_local_document
from src.rag.bedrock_llm import BedrockLLM
from src.utils.logger import get_logger

logger = get_logger("rag_engine")

class SimpleVectorIndex:
    """
    Lightweight, in-memory vector index & similarity search engine for RAG demonstration.
    """
    def __init__(self, chunk_size: int = 250, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunks: List[Dict] = []

    def add_document(self, doc_text: str, doc_name: str = "doc1.txt"):
        """Splits document text into overlapping chunks."""
        words = doc_text.split()
        chunk_id = 0
        i = 0
        while i < len(words):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            self.chunks.append({
                "id": f"{doc_name}_chunk_{chunk_id}",
                "doc_name": doc_name,
                "text": chunk_text
            })
            chunk_id += 1
            i += (self.chunk_size - self.chunk_overlap)
        logger.info(f"Ingested '{doc_name}': created {len(self.chunks)} chunks.")

    def search(self, query: str, top_k: int = 2) -> List[Dict]:
        """
        Simple keyword-weighted TF-IDF / term overlap vector similarity search.
        """
        query_terms = set(query.lower().split())
        scored_chunks = []
        
        for chunk in self.chunks:
            chunk_words = chunk["text"].lower().split()
            score = sum(1 for word in chunk_words if word in query_terms)
            scored_chunks.append((score, chunk))
            
        # Sort descending by relevance score
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for score, chunk in scored_chunks[:top_k] if score > 0]

class CustomRAGEngine:
    """
    Custom Retrieval-Augmented Generation (RAG) Engine.
    """
    def __init__(self, doc_path: str = os.path.join("docs", "sample_vacation_policy.txt")):
        self.index = SimpleVectorIndex()
        self.llm = BedrockLLM()
        
        # Load and ingest default document
        if os.path.exists(doc_path):
            doc_content = load_local_document(doc_path)
            self.index.add_document(doc_content, doc_name=os.path.basename(doc_path))
        else:
            logger.warning(f"Document path '{doc_path}' not found.")

    def query(self, question: str, chat_history: Optional[List[Dict]] = None) -> Dict:
        """
        Executes RAG pipeline with Conversational Memory:
        Retrieve context -> Append chat history -> Augment Prompt -> Generate Answer.
        """
        # 1. Retrieve top-k relevant document chunks
        retrieved_chunks = self.index.search(question, top_k=2)
        
        # 2. Format past conversation history
        history_str = ""
        if chat_history:
            formatted_turns = [f"{turn.get('role', 'user').upper()}: {turn.get('content', '')}" for turn in chat_history]
            history_str = "PAST CONVERSATION HISTORY:\n" + "\n".join(formatted_turns) + "\n\n"
        
        if not retrieved_chunks:
            logger.info("No relevant context found for question.")
            context_str = "No specific enterprise document context available."
        else:
            context_str = "\n\n".join([f"[Source: {c['doc_name']}]\n{c['text']}" for c in retrieved_chunks])
            
        # 3. Construct Augmented RAG Prompt with History
        augmented_prompt = f"""You are an Enterprise Knowledge Assistant. Answer the question strictly using the provided context documents below and considering the past conversation history.

{history_str}CONTEXT DOCUMENTS:
===================
{context_str}
===================

USER QUESTION: {question}

YOUR GROUNDED ANSWER:"""

        system_prompt = "You are a precise, grounded enterprise assistant. Do not invent facts outside the provided document context."
        
        # 3. Generate Grounded Response via Bedrock
        llm_result = self.llm.generate_response(prompt=augmented_prompt, system_prompt=system_prompt)
        
        answer_text = llm_result.get("response_text")
        if not answer_text or llm_result.get("status") == "error":
            if retrieved_chunks:
                # Synthesize grounded answer directly from retrieved chunk
                extracted_section = retrieved_chunks[0]["text"]
                answer_text = f"[Grounded Context Answer]: {extracted_section}"
            else:
                answer_text = "No relevant enterprise documents found to answer your question."

        return {
            "status": "success",
            "question": question,
            "answer": answer_text,
            "retrieved_context": [c["text"] for c in retrieved_chunks],
            "sources": list(set([c["doc_name"] for c in retrieved_chunks])),
            "is_rag_grounded": True if retrieved_chunks else False
        }

if __name__ == "__main__":
    engine = CustomRAGEngine()
    res = engine.query("What is the vacation policy for contractors?")
    print("\n--- Grounded RAG Query Result ---")
    print(json.dumps(res, indent=2))
