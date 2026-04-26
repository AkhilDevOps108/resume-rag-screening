"""
Prompt Builder Module
Constructs structured prompts for LLM generation
"""

from typing import List, Dict, Optional
from datetime import datetime


class PromptBuilder:
    """Builds structured prompts for LLM"""
    
    def __init__(self, system_prompt: Optional[str] = None):
        """
        Initialize prompt builder
        
        Args:
            system_prompt: Optional system prompt template
        """
        self.system_prompt = system_prompt or self._default_system_prompt()
    
    def _default_system_prompt(self) -> str:
        """Default system prompt for RAG"""
        return """You are a helpful AI assistant. Answer the user's question based on the provided context.
If the context doesn't contain relevant information, say so clearly.
Provide clear, accurate, and concise answers with proper citations to the source documents."""
    
    def build_standard_rag_prompt(self, query: str, context: str) -> Dict:
        """
        Build standard RAG prompt
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            Prompt dict with system and user messages
        """
        user_message = f"""Based on the following context, answer the question.

CONTEXT:
{context}

QUESTION: {query}

ANSWER:"""
        
        return {
            "system": self.system_prompt,
            "user": user_message,
            "mode": "standard_rag"
        }
    
    def build_advanced_rag_prompt(self, query: str, context: str, metadata: Dict = None) -> Dict:
        """
        Build advanced RAG prompt with structured information
        
        Args:
            query: User query
            context: Optimized context
            metadata: Additional metadata about retrieved context
            
        Returns:
            Structured prompt dict
        """
        metadata = metadata or {}
        
        system_message = self.system_prompt + """

When answering:
1. Use the provided context as primary source material
2. Cite specific document references
3. Acknowledge context limitations if applicable
4. Structure your answer clearly with key points"""
        
        # Build structured user message
        context_info = f"Retrieved {metadata.get('num_docs', 'multiple')} relevant documents"
        if metadata.get('compression_ratio'):
            context_info += f"\nContext compressed to {metadata['compression_ratio']:.1%} of original size"
        
        user_message = f"""Question: {query}

Context Information:
{context_info}

Retrieved Context:
{context}

Please provide a comprehensive answer based on this context:"""
        
        return {
            "system": system_message,
            "user": user_message,
            "mode": "advanced_rag",
            "metadata": metadata
        }
    
    def build_comparison_prompt(self, query: str, standard_answer: str, advanced_answer: str) -> Dict:
        """
        Build prompt for comparing two RAG approaches
        
        Args:
            query: Original query
            standard_answer: Answer from standard RAG
            advanced_answer: Answer from advanced RAG
            
        Returns:
            Comparison prompt
        """
        user_message = f"""Compare the following two answers to the same question:

QUESTION: {query}

STANDARD RAG ANSWER:
{standard_answer}

ADVANCED RAG ANSWER:
{advanced_answer}

Analyze which answer is more comprehensive, better cited, and more helpful. Consider factors like:
- Accuracy and relevance
- Citation quality
- Comprehensiveness
- Structure and clarity"""
        
        return {
            "system": "You are a critical evaluator of AI-generated answers.",
            "user": user_message,
            "mode": "comparison"
        }
    
    def build_evidence_synthesis_prompt(self, query: str, documents: List[Dict]) -> Dict:
        """
        Build prompt for synthesizing evidence from multiple documents
        
        Args:
            query: User query
            documents: List of document dicts with evidence
            
        Returns:
            Evidence synthesis prompt
        """
        evidence_sections = []
        for i, doc in enumerate(documents, 1):
            evidence_sections.append(f"""EVIDENCE {i} (from {doc.get('doc_name', 'Unknown')}):
{doc.get('content', '')}""")
        
        evidence_text = "\n\n".join(evidence_sections)
        
        user_message = f"""Synthesize evidence from multiple sources to answer the question:

QUESTION: {query}

{evidence_text}

Task:
1. Identify key points from each source
2. Find connections and relationships between sources
3. Synthesize into a comprehensive answer
4. Note any contradictions or different perspectives
5. Provide a clear, unified response"""
        
        return {
            "system": "You are an expert at synthesizing information from multiple sources.",
            "user": user_message,
            "mode": "evidence_synthesis"
        }
    
    def format_for_llm(self, prompt_dict: Dict) -> str:
        """
        Format prompt dict for LLM API
        
        Args:
            prompt_dict: Prompt dictionary
            
        Returns:
            Formatted prompt string
        """
        return f"{prompt_dict.get('system', '')}\n\n{prompt_dict.get('user', '')}"


class ResponseFormatter:
    """Formats LLM responses with metadata"""
    
    @staticmethod
    def format_response(answer: str, metadata: Dict = None) -> Dict:
        """
        Format LLM response with metadata
        
        Args:
            answer: Generated answer
            metadata: Optional metadata dict
            
        Returns:
            Formatted response dict
        """
        metadata = metadata or {}
        
        return {
            "answer": answer,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "mode": metadata.get("mode", "unknown"),
                "retrieval_count": metadata.get("retrieval_count", 0),
                "context_tokens": metadata.get("context_tokens", 0),
                "answer_tokens": len(answer.split()),
                "latency_ms": metadata.get("latency_ms", 0),
                **metadata
            }
        }
    
    @staticmethod
    def format_comparison_response(standard_answer: Dict, advanced_answer: Dict,
                                   query: str) -> Dict:
        """
        Format side-by-side comparison response
        
        Args:
            standard_answer: Standard RAG answer dict
            advanced_answer: Advanced RAG answer dict
            query: Original query
            
        Returns:
            Comparison response dict
        """
        return {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "standard_rag": {
                "answer": standard_answer.get("answer", ""),
                "latency_ms": standard_answer.get("metadata", {}).get("latency_ms", 0),
                "retrieval_count": standard_answer.get("metadata", {}).get("retrieval_count", 0),
                "context_tokens": standard_answer.get("metadata", {}).get("context_tokens", 0),
            },
            "advanced_rag": {
                "answer": advanced_answer.get("answer", ""),
                "latency_ms": advanced_answer.get("metadata", {}).get("latency_ms", 0),
                "retrieval_count": advanced_answer.get("metadata", {}).get("retrieval_count", 0),
                "context_tokens": advanced_answer.get("metadata", {}).get("context_tokens", 0),
            }
        }


if __name__ == "__main__":
    builder = PromptBuilder()
    print("Prompt builder initialized")
