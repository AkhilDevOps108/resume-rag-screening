"""
FastAPI Backend Server
Main application orchestrating both Standard and Advanced RAG modes
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import tempfile
import json
import time
import traceback
import re
import requests
import importlib
from pathlib import Path
from dotenv import load_dotenv

# Import all modules
from modules.ingest import DocumentProcessor, DocumentChunk
from modules.embeddings import EmbeddingStore
from modules.retriever import StandardRAGRetriever
from modules.hybrid_search import HybridSearcher
from modules.reranker import AdvancedReranker
from modules.semantic_graph import SemanticGraph
from modules.context_optimizer import ContextOptimizer, ContextCompressor
from modules.prompt_builder import PromptBuilder, ResponseFormatter
from modules.metrics import MetricsCollector, RAGBenchmark, AdvancedRAGMetrics

# Initialize FastAPI
app = FastAPI(title="Advanced Context-Aware RAG", version="1.0.0")

# Load runtime environment variables from backend/.env
load_dotenv()
# If GEMINI_API_KEY is not set in .env, allow local dev fallback from .env.example.
if not os.getenv("GEMINI_API_KEY"):
    load_dotenv(".env.example", override=False)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
class RAGSystem:
    def __init__(self):
        self.documents = []
        self.chunks = []
        self.embedding_store = None
        self.standard_retriever = None
        self.hybrid_searcher = None
        self.advanced_reranker = None
        self.semantic_graph = None
        self.metrics_collector = MetricsCollector()
        self.benchmark = RAGBenchmark()
        self.processor = DocumentProcessor(chunk_size=512, overlap=64)
        self.optimizer = ContextOptimizer()
        self.compressor = ContextCompressor()
        self.prompt_builder = PromptBuilder()
        self.data_dir = Path(os.getenv("DATA_DIR", "./data")).resolve()
        self.index_dir = self.data_dir / "index"
        self.chunks_path = self.data_dir / "chunks.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def initialize_retrieval(self):
        """Initialize retrieval components"""
        if self.embedding_store:
            self.standard_retriever = StandardRAGRetriever(self.embedding_store)
            self.hybrid_searcher = HybridSearcher(self.embedding_store, alpha=0.7)
            self.advanced_reranker = AdvancedReranker(self.embedding_store)
            
            # Build semantic graph
            self.semantic_graph = SemanticGraph(self.embedding_store)
            chunk_metadata = [chunk.to_dict() for chunk in self.chunks]
            self.semantic_graph.add_chunks(self.chunks, chunk_metadata)
    
    def add_documents(self, file_paths: List[str], append: bool = True):
        """Add documents to the system"""
        new_chunks = self.processor.process_files(file_paths)

        seen_hashes = {
            (chunk.metadata or {}).get("content_hash")
            for chunk in self.chunks
            if (chunk.metadata or {}).get("content_hash")
        }
        new_chunks = [
            chunk for chunk in new_chunks
            if (chunk.metadata or {}).get("content_hash") not in seen_hashes
        ]

        if not new_chunks:
            raise ValueError("No new valid text could be extracted from the uploaded files")

        if append and self.chunks:
            self.chunks.extend(new_chunks)
        else:
            self.chunks = new_chunks
        
        # Initialize embedding store once and append only new chunks.
        if self.embedding_store is None or not append:
            self.embedding_store = EmbeddingStore(persistence_dir=str(self.index_dir))
            self.embedding_store.add_chunks(self.chunks)
        else:
            self.embedding_store.add_chunks(new_chunks)
        
        # Initialize retrieval components
        self.initialize_retrieval()
        self.save_state()
        
        return {
            "chunks_added": len(new_chunks),
            "total_chunks": len(self.chunks)
        }

    def save_state(self) -> None:
        """Persist chunk metadata and vector index to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        serialized_chunks = [chunk.to_dict() for chunk in self.chunks]
        self.chunks_path.write_text(json.dumps(serialized_chunks, indent=2), encoding="utf-8")
        if self.embedding_store:
            self.embedding_store.save(str(self.index_dir))

    def load_state(self) -> bool:
        """Load persisted chunk/index state from disk, if available."""
        if not self.chunks_path.exists():
            return False

        try:
            raw_chunks = json.loads(self.chunks_path.read_text(encoding="utf-8"))
        except Exception:
            return False

        restored_chunks = []
        for item in raw_chunks:
            restored_chunks.append(
                DocumentChunk(
                    content=item.get("content", ""),
                    doc_id=item.get("doc_id", ""),
                    doc_name=item.get("doc_name", ""),
                    chunk_idx=item.get("chunk_idx", 0),
                    start_char=item.get("start_char", 0),
                    end_char=item.get("end_char", 0),
                    metadata=item.get("metadata", {}),
                )
            )

        self.chunks = restored_chunks
        self.embedding_store = EmbeddingStore(persistence_dir=str(self.index_dir))
        loaded = self.embedding_store.load(str(self.index_dir))
        if not loaded and self.chunks:
            self.embedding_store.add_chunks(self.chunks)

        self.initialize_retrieval()
        return len(self.chunks) > 0

# Initialize RAG system
rag_system = RAGSystem()
rag_system.load_state()


def _build_context(retrieved_docs: List[Dict], limit: int = 5) -> str:
    """Create compact context string for answer generation."""
    context_parts = []
    for idx, doc in enumerate(retrieved_docs[:limit], 1):
        context_parts.append(
            f"[Source {idx}] {doc.get('doc_name', 'Unknown')}\n{doc.get('content', '')}"
        )
    return "\n\n".join(context_parts)


def _fallback_answer(query: str, retrieved_docs: List[Dict]) -> str:
    """Fallback answer when external LLM is not configured."""
    if not retrieved_docs:
        return "I could not find relevant content in the uploaded documents for this question."

    def _clean_text(text: str) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        text = text.replace("©", "")
        return text

    combined_text = _clean_text(" ".join(doc.get("content", "") for doc in retrieved_docs[:5]))

    # Small heuristic for common resume-style experience questions.
    experience_match = re.search(r"(\d+)\s+years?(?:\s+in\s+it)?", combined_text, flags=re.IGNORECASE)
    if re.search(r"(experience|exp|years?)", query, flags=re.IGNORECASE) and experience_match:
        years = experience_match.group(1)
        candidate_label = "the candidate"
        if retrieved_docs:
            inferred_table = _extract_candidate_table(retrieved_docs[:5])
            if inferred_table and inferred_table[0].get("candidate_name"):
                candidate_label = inferred_table[0]["candidate_name"]
        return (
            f"Based on the retrieved documents, {candidate_label} appears to have {years} years of experience. "
            "This is extracted directly from the profile text in the uploaded resume."
        )

    top_docs = retrieved_docs[:3]
    citations = ", ".join(
        f"[{i + 1}] {doc.get('doc_name', 'Unknown')}"
        for i, doc in enumerate(top_docs)
    )

    preview = " ".join(_clean_text(doc.get("content", "")[:260]) for doc in top_docs if doc.get("content"))
    preview = preview.strip() or "Relevant context was retrieved, but no extractable snippet was available."

    return (
        f"Based on the retrieved context, here is a concise answer to '{query}':\n\n"
        f"{preview}.\n\n"
        f"Sources: {citations}"
    )


def _clean_generated_answer(answer: str) -> str:
    """Trim obvious truncated tails from model output before sending to the UI."""
    text = (answer or "").strip()
    if not text:
        return text

    text = re.sub(r"[*_`#]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Drop a trailing broken fragment like: Here' / Here" / Becau / Her
    if re.search(r"[A-Za-z]['\"]?$", text) and not re.search(r"[.!?]['\"]?$", text):
        text = re.sub(r"\s+[A-Za-z][A-Za-z'\"]*$", "", text).strip()

    # Remove a trailing orphaned markdown-style lead-in or incomplete possessive clause.
    text = re.sub(r"(?:\s*[-*]\s*|\s+)\*\*[^*]*$", "", text).strip()
    text = re.sub(r"\s+(?:Her|His|Their|Here|This|That|These|Those)\s*$", "", text).strip()

    # If the answer ends without sentence punctuation, trim back to the last full sentence.
    if text and not re.search(r"[.!?]['\"]?$", text):
        last_punct = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
        if last_punct > 40:
            text = text[:last_punct + 1].strip()

    return text


def _is_likely_incomplete_answer(answer: str) -> bool:
    """Detect obvious truncated or unfinished model outputs."""
    text = (answer or "").strip()
    if not text or len(text) < 20:
        return True

    if text.endswith((",", ":", ";", "-", "/", "(", "[", "{", "'", '"')):
        return True

    if text.count('"') % 2 != 0:
        return True

    if text.count("(") != text.count(")"):
        return True

    if re.search(r"\b(and|or|but|because|with|including|such as)\s*$", text, flags=re.IGNORECASE):
        return True

    if not re.search(r"[.!?]['\"]?$", text):
        return True

    return False


def _resolve_gemini_api_key() -> str:
    """Resolve Gemini key from common environment variable names."""
    candidates = [
        os.getenv("GEMINI_API_KEY", ""),
        os.getenv("GOOGLE_API_KEY", ""),
        os.getenv("GOOGLE_GENAI_API_KEY", ""),
    ]

    for candidate in candidates:
        value = (candidate or "").strip().strip('"').strip("'")
        if not value:
            continue
        if value.lower() in {
            "your_key_here",
            "your_api_key_here",
            "replace_me",
            "changeme",
        }:
            continue
        return value

    return ""


def _infer_answer_style(query: str) -> str:
    """Infer response style from query intent."""
    q = (query or "").strip().lower()

    concise_patterns = [
        r"\bwho\s+is\s+best\b",
        r"\bbest\s+for\b",
        r"\bbest\s+candidate\b",
        r"\btop\s+candidate\b",
        r"\bmost\s+suitable\b",
        r"\bbetter\s+fit\b",
        r"\bstronger\s+candidate\b",
        r"\bwho\s+should\s+we\s+hire\b",
        r"\bwho\s+to\s+hire\b",
        r"\bbetter\b",
        r"\bwhich\s+candidate\b",
        r"\bshort\s+answer\b",
        r"\bconcise\b",
        r"\bbrief\b",
    ]
    detailed_patterns = [
        r"\bexplain\b",
        r"\bwhy\b",
        r"\bcompare\b",
        r"\bdetailed\b",
        r"\bin\s+detail\b",
        r"\bpros\s+and\s+cons\b",
    ]

    if any(re.search(p, q) for p in concise_patterns):
        return "concise"
    if any(re.search(p, q) for p in detailed_patterns):
        return "detailed"
    return "balanced"


def _is_candidate_ranking_query(query: str) -> bool:
    """Detect candidate ranking/selection intent."""
    q = (query or "").strip().lower()
    ranking_signal = re.search(
        r"\b(best|better|top|suitable|fit|stronger|select|choose|hire|shortlist)\b", q
    )
    candidate_signal = re.search(
        r"\b(candidate|candidates|profile|profiles|resume|resumes|person|who)\b", q
    )
    return bool(ranking_signal and candidate_signal)


def _extract_candidate_name(text: str, fallback_doc_name: str, fallback_index: int) -> str:
    """Extract candidate name from chunk text with safe fallback."""
    content = (text or "").strip()

    def _sanitize_name(raw_name: str, min_tokens: int = 2) -> str:
        name = (raw_name or "").strip()
        name = re.sub(r"[_\-]+", " ", name)
        name = re.sub(r"\s+", " ", name).strip()
        name = re.sub(r"\b(?:Experience|Skills|Summary|Resume|CV|Profile)\b.*$", "", name, flags=re.IGNORECASE).strip()

        # Remove common non-name leading tokens that appear in noisy resume headers.
        leading_noise = {
            "azure", "aws", "gcp", "devops", "engineer", "developer",
            "frontend", "backend", "full", "stack", "cloud", "candidate",
            "resume", "profile", "senior", "junior"
        }
        tokens = name.split()
        while tokens and tokens[0].lower().strip(".") in leading_noise:
            tokens = tokens[1:]
        name = " ".join(tokens).strip()

        # Keep letters/periods/spaces only and normalize again.
        name = re.sub(r"[^A-Za-z.\s]", "", name)
        name = re.sub(r"\s+", " ", name).strip()

        # Validate that at least two likely name tokens remain.
        name_tokens = [t for t in name.split() if t]
        valid_tokens = [
            t for t in name_tokens
            if re.fullmatch(r"[A-Z][a-z]+|[A-Z]\.?(?:[A-Z][a-z]+)?", t)
        ]
        if len(valid_tokens) < min_tokens:
            return ""

        # Normalize single-letter initials without trailing noise.
        normalized = []
        for token in valid_tokens:
            if re.fullmatch(r"[A-Z]\.??", token):
                normalized.append(token[0])
            else:
                normalized.append(token)
        return " ".join(normalized)

    patterns = [
        r"\bName\s*[:\-]\s*([A-Z][A-Za-z.]*(?:\s+[A-Z][A-Za-z.]*){0,4}?)(?=\s+(?:Experience|Skills|Summary)\b|\s*[\n,;:.]|$)",
        r"\bCandidate\s*[:\-]\s*([A-Z][A-Za-z.]*(?:\s+[A-Z][A-Za-z.]*){0,4}?)(?=\s+(?:Experience|Skills|Summary)\b|\s*[\n,;:.]|$)",
        r"-\s*([A-Z][A-Za-z.]*(?:\s+[A-Z][A-Za-z.]*){1,4})(?=\s*(?:\n|$))",
        r"^\s*([A-Z][A-Za-z.]*(?:\s+[A-Z][A-Za-z.]*){0,4})\s*[:\-]",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, flags=re.MULTILINE)
        if match:
            cleaned = _sanitize_name(match.group(1), min_tokens=2)
            if cleaned:
                return cleaned

    raw_doc_name = (fallback_doc_name or "").strip()
    base_name = re.sub(r"\.[A-Za-z0-9]+$", "", raw_doc_name)
    base_name = _sanitize_name(base_name, min_tokens=1)
    if base_name and not re.match(r"^tmp", base_name, flags=re.IGNORECASE):
        return base_name

    return f"Candidate {fallback_index}"


def _normalize_chunk_text(text: str) -> str:
    """Normalize noisy extracted text for parsing and prompt quality."""
    content = text or ""
    content = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", content)
    content = re.sub(r"\s+", " ", content).strip()
    return content


def _choose_better_candidate_name(current_name: str, new_name: str) -> str:
    """Choose the more complete candidate name between two aliases."""
    current = (current_name or "").strip()
    new = (new_name or "").strip()

    if not current:
        return new
    if not new:
        return current
    if re.fullmatch(r"Candidate\s+\d+", current, flags=re.IGNORECASE):
        return new
    if re.fullmatch(r"Candidate\s+\d+", new, flags=re.IGNORECASE):
        return current

    current_tokens = current.split()
    new_tokens = new.split()

    def _name_specificity(tokens: List[str]) -> tuple:
        full_tokens = sum(1 for token in tokens if len(token.replace('.', '')) > 1)
        total_chars = sum(len(token.replace('.', '')) for token in tokens)
        return (full_tokens, total_chars, len(tokens))

    # Prefer the alias with more tokens when one looks like a shortened variant.
    current_prefix = " ".join(current_tokens[:2]).lower() if len(current_tokens) >= 2 else current.lower()
    new_prefix = " ".join(new_tokens[:2]).lower() if len(new_tokens) >= 2 else new.lower()
    if current_prefix and current_prefix == new_prefix:
        if len(new_tokens) != len(current_tokens):
            return new if len(new_tokens) > len(current_tokens) else current
        return new if _name_specificity(new_tokens) > _name_specificity(current_tokens) else current

    # Otherwise prefer the longer, more descriptive name.
    return new if _name_specificity(new_tokens) > _name_specificity(current_tokens) else current


def _extract_candidate_table(retrieved_docs: List[Dict]) -> List[Dict]:
    """Create lightweight candidate table from retrieved chunks."""
    skill_keywords = [
        "Azure", "DevOps", "Terraform", "AKS", "Docker", "Kubernetes", "CI/CD",
        "React", "Next.js", "TypeScript", "Redux", "Tailwind", "FastAPI", "Python",
    ]

    by_candidate = {}
    for idx, doc in enumerate(retrieved_docs, 1):
        content = _normalize_chunk_text(doc.get("content", ""))
        name = _extract_candidate_name(content, doc.get("doc_name", ""), idx)
        candidate_key = doc.get("doc_id") or doc.get("doc_name") or name

        exp_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", content, flags=re.IGNORECASE)
        years = int(exp_match.group(1)) if exp_match else None

        found_skills = [
            skill for skill in skill_keywords
            if re.search(rf"\b{re.escape(skill)}\b", content, flags=re.IGNORECASE)
        ]

        if candidate_key not in by_candidate:
            by_candidate[candidate_key] = {
                "name": name,
                "experience_years": years,
                "skills": set(found_skills),
            }
        else:
            existing = by_candidate[candidate_key]
            existing["name"] = _choose_better_candidate_name(existing["name"], name)
            if years is not None and (existing["experience_years"] is None or years > existing["experience_years"]):
                existing["experience_years"] = years
            existing["skills"].update(found_skills)

    rows = []
    for row in by_candidate.values():
        years = row["experience_years"]
        exp_label = f"{years} years" if years is not None else "Not specified"
        rows.append({
            "candidate_name": row["name"],
            "experience_years": years,
            "experience": exp_label,
            "skills": sorted(row["skills"]),
        })

    rows.sort(key=lambda r: (r["experience"] == "Not specified", -len(r["skills"]), r["candidate_name"]))
    return rows[:8]


def _mentions_any_candidate(answer: str, candidate_names: List[str]) -> bool:
    """Check whether generated answer names at least one candidate."""
    text = (answer or "").lower()
    for name in candidate_names:
        if name and name.lower() in text:
            return True
    return False


def _context_limit_for_style(style: str) -> int:
    """Set context window size based on expected answer style."""
    if style == "concise":
        return 4
    if style == "detailed":
        return 7
    return 5


def _prompt_for_style(style: str, mode: str, query: str, context: str, ranking_query: bool = False) -> str:
    """Build a prompt tuned for concise/balanced/detailed outputs."""
    if style == "concise":
        style_instruction = (
            "Return only 1-2 lines total. Start with a direct verdict in the first sentence. "
            "Add at most one short supporting sentence. No bullets or headings."
        )
    elif style == "detailed":
        style_instruction = (
            "Return 4-6 complete sentences with clear reasoning using only provided evidence. "
            "No bullets or headings."
        )
    else:
        style_instruction = (
            "Return exactly one concise verdict sentence followed by 2-4 supporting complete sentences. "
            "No bullets or headings."
        )

    ranking_instruction = ""
    if ranking_query:
        ranking_instruction = (
            "This is a candidate ranking question. Name the top candidate explicitly in the first sentence. "
            "Do not answer with generic phrases like 'a candidate'. Do not output malformed merged tokens."
        )

    return (
        "You are a RAG assistant. Use only the provided context. "
        "If evidence is insufficient, explicitly state that. Cite sources as [Source n] only when needed. "
        f"{style_instruction} {ranking_instruction} "
        "Do not produce unfinished lists or sentence fragments. The final character must be sentence-ending punctuation.\n\n"
        f"Mode: {mode}\n"
        f"Question: {query}\n\n"
        f"Context:\n{context}\n\n"
        "Answer:"
    )


def _score_candidate_for_query(query: str, candidate_row: Dict) -> float:
    """Compute a lightweight relevance score for deterministic ranking fallback."""
    query_text = (query or "").lower()
    skills = [s.lower() for s in candidate_row.get("skills", [])]
    exp_years = candidate_row.get("experience_years")
    exp_years = float(exp_years) if isinstance(exp_years, (int, float)) else 0.0

    score = exp_years
    for skill in skills:
        if skill and skill in query_text:
            score += 3.0

    if "devops" in query_text and any(s in skills for s in ["devops", "azure", "terraform", "aks", "ci/cd"]):
        score += 2.0

    return score


def _build_ranking_fallback_answer(query: str, candidate_table: List[Dict]) -> str:
    """Build concise deterministic ranking answer if LLM output quality is poor."""
    if not candidate_table:
        return "I could not identify candidate names clearly from the retrieved resumes."

    ranked = sorted(
        candidate_table,
        key=lambda row: (_score_candidate_for_query(query, row), len(row.get("skills", []))),
        reverse=True,
    )
    winner = ranked[0]
    name = winner.get("candidate_name", "Top candidate")
    exp = winner.get("experience", "Not specified")
    skills = ", ".join(winner.get("skills", [])[:4]) or "relevant skills"
    return f"{name} is the best fit for this role. They have {exp} of relevant experience with skills such as {skills}."


def _is_low_quality_ranking_answer(answer: str, candidate_names: List[str]) -> bool:
    """Detect generic, malformed, or overlong ranking answers."""
    text = (answer or "").strip()
    if not text:
        return True

    if candidate_names and not _mentions_any_candidate(text, candidate_names):
        return True

    if len(text) > 340:
        return True

    if re.search(r"[A-Za-z]{3,}[A-Z][a-z]+[A-Z][a-z]+", text):
        return True

    if "a candidate" in text.lower() and not _mentions_any_candidate(text, candidate_names):
        return True

    return False


def _generate_answer(query: str, retrieved_docs: List[Dict], mode: str) -> Dict:
    """Generate answer using Gemini if API key exists, otherwise use fallback synthesis."""
    llm_start = time.time()
    api_key = _resolve_gemini_api_key()
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
    ranking_query = _is_candidate_ranking_query(query)
    answer_style = _infer_answer_style(query)
    if ranking_query:
        answer_style = "concise"

    normalized_docs = []
    for doc in retrieved_docs:
        normalized_doc = dict(doc)
        normalized_doc["content"] = _normalize_chunk_text(doc.get("content", ""))
        normalized_docs.append(normalized_doc)

    candidate_table = _extract_candidate_table(normalized_docs) if ranking_query else []
    candidate_names = [row.get("candidate_name", "") for row in candidate_table]

    context_limit = _context_limit_for_style(answer_style)
    context = _build_context(normalized_docs, limit=context_limit)
    context_sources = min(len(normalized_docs), context_limit)
    context_chars = len(context)
    genai = None

    try:
        genai = importlib.import_module("google.generativeai")
    except Exception:
        genai = None

    if not api_key:
        llm_latency = (time.time() - llm_start) * 1000
        return {
            "answer": (
                "Answer generation is disabled because Gemini API key is not configured. "
                "Set GEMINI_API_KEY (or GOOGLE_API_KEY) in backend/.env and restart the backend."
            ),
            "answer_metadata": {
                "provider": "configuration-error",
                "model": "none",
                "mode": mode,
                "answer_style": answer_style,
                "ranking_query": ranking_query,
                "candidate_table": candidate_table,
                "reason": "missing_gemini_api_key",
                "llm_latency_ms": llm_latency,
                "context_sources": context_sources,
                "context_chars": context_chars,
            },
        }

    prompt = _prompt_for_style(answer_style, mode, query, context, ranking_query=ranking_query)

    try:
        provider = "gemini-rest"
        regeneration_count = 0

        def _call_gemini(prompt_text: str, max_tokens: int = 1200) -> str:
            nonlocal provider

            answer_text = ""
            if genai is not None:
                genai.configure(api_key=api_key)
                sdk_model = genai.GenerativeModel(model)
                sdk_response = sdk_model.generate_content(
                    prompt_text,
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": max_tokens,
                    }
                )
                answer_text = (getattr(sdk_response, "text", "") or "").strip()
                provider = "gemini-sdk"

            if not answer_text:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt_text}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": max_tokens,
                    },
                }
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                answer_text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                provider = "gemini-rest"

            return answer_text

        first_pass_tokens = 220 if ranking_query else 1200
        second_pass_tokens = 280 if ranking_query else 1400
        answer = _call_gemini(prompt, max_tokens=first_pass_tokens)

        missing_name_in_ranking = ranking_query and candidate_names and not _mentions_any_candidate(answer, candidate_names)
        if _is_likely_incomplete_answer(answer) or missing_name_in_ranking:
            regeneration_count = 1
            repair_prompt = (
                "Rewrite the answer from scratch using only the provided context. "
            "The previous output was either incomplete or did not satisfy formatting requirements. "
            "Follow the required style exactly and ensure the answer is complete. "
                "Do not use bullets. Do not end mid-sentence. End with a full sentence and final punctuation.\n\n"
            f"Known candidate names: {', '.join(candidate_names) if candidate_names else 'Not available'}\n"
                f"Mode: {mode}\n"
                f"Question: {query}\n\n"
                f"Context:\n{context}\n\n"
                "Answer:"
            )
            answer = _call_gemini(repair_prompt, max_tokens=second_pass_tokens)

        if not answer:
            raise ValueError("Gemini response did not include text output")

        answer = _clean_generated_answer(answer)

        quality_fallback_used = False
        if ranking_query and _is_low_quality_ranking_answer(answer, candidate_names):
            answer = _build_ranking_fallback_answer(query, candidate_table)
            quality_fallback_used = True

        return {
            "answer": answer,
            "answer_metadata": {
                "provider": provider,
                "model": model,
                "mode": mode,
                "answer_style": answer_style,
                "ranking_query": ranking_query,
                "candidate_table": candidate_table,
                "context_limit": context_limit,
                "regeneration_count": regeneration_count,
                "quality_fallback_used": quality_fallback_used,
                "llm_latency_ms": (time.time() - llm_start) * 1000,
                "context_sources": context_sources,
                "context_chars": context_chars,
            },
        }
    except Exception as llm_error:
        llm_latency = (time.time() - llm_start) * 1000
        return {
            "answer": (
                "I could not generate a reliable answer because the configured LLM call failed. "
                "Please retry, and if the issue persists, verify Gemini API key and model settings."
            ),
            "answer_metadata": {
                "provider": "llm-error",
                "model": model,
                "mode": mode,
                "answer_style": answer_style,
                "ranking_query": ranking_query,
                "candidate_table": candidate_table,
                "context_limit": context_limit,
                "llm_error": str(llm_error),
                "llm_latency_ms": llm_latency,
                "context_sources": context_sources,
                "context_chars": context_chars,
            },
        }

# Pydantic models
class DocumentUploadResponse(BaseModel):
    message: str
    chunks_added: int
    total_chunks: int

class RetrievalResult(BaseModel):
    mode: str
    query: str
    num_retrieved: int
    retrieved_docs: List[Dict]
    metrics: Dict

class ComparisonResult(BaseModel):
    query: str
    standard_rag: Dict
    advanced_rag: Dict
    metrics_comparison: Dict

# Routes

@app.post("/api/upload", response_model=DocumentUploadResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload and process documents"""
    file_paths = []
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="rag_upload_")
        
        for idx, file in enumerate(files, 1):
            # Preserve original upload filename so downstream candidate parsing can use it.
            original_name = os.path.basename(file.filename or f"document_{idx}.txt")
            safe_name = re.sub(r"[^A-Za-z0-9._\- ]", "_", original_name).strip()
            if not safe_name:
                safe_name = f"document_{idx}.txt"

            target_path = os.path.join(temp_dir, safe_name)
            if os.path.exists(target_path):
                stem, ext = os.path.splitext(safe_name)
                target_path = os.path.join(temp_dir, f"{stem}_{idx}{ext}")

            content = await file.read()
            with open(target_path, "wb") as out_file:
                out_file.write(content)

            file_paths.append(target_path)
        
        # Add documents
        result = rag_system.add_documents(file_paths)
        
        # Cleanup temp files
        for path in file_paths:
            if os.path.exists(path):
                os.unlink(path)
        
        return DocumentUploadResponse(
            message="Documents uploaded and processed successfully",
            chunks_added=result["chunks_added"],
            total_chunks=result["total_chunks"]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        for path in file_paths:
            if os.path.exists(path):
                os.unlink(path)
        if temp_dir and os.path.isdir(temp_dir):
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass

@app.get("/api/documents")
async def get_documents():
    """Get list of uploaded documents"""
    doc_ids = list(set(chunk.doc_id for chunk in rag_system.chunks))
    doc_names = list(set(chunk.doc_name for chunk in rag_system.chunks))
    
    return {
        "total_documents": len(doc_ids),
        "total_chunks": len(rag_system.chunks),
        "documents": list(zip(doc_ids, doc_names)),
        "graph_stats": rag_system.semantic_graph.get_graph_stats() if rag_system.semantic_graph else {}
    }

@app.api_route("/api/retrieve/standard", methods=["GET", "POST"])
async def retrieve_standard(query: str, k: int = 5):
    """Standard RAG retrieval"""
    try:
        if not rag_system.standard_retriever:
            raise HTTPException(status_code=400, detail="No documents loaded")
        
        start_time = time.time()
        result = rag_system.standard_retriever.retrieve(query, k=k)
        retrieval_latency = (time.time() - start_time) * 1000
        
        # Record metrics
        rag_system.metrics_collector.record_standard_rag({
            "query": query,
            "num_retrieved": result["num_retrieved"],
            "retrieval_scores": result["retrieval_scores"],
            "latency_ms": retrieval_latency,
            "pipeline_stages": result["pipeline_stages"],
            "total_tokens_used": result["total_tokens_used"]
        })
        
        rag_system.benchmark.add_result(
            "standard_rag", query,
            result["retrieved_docs"],
            result["retrieval_scores"],
            retrieval_latency
        )

        answer_result = _generate_answer(query, result["retrieved_docs"], "standard_rag")
        llm_latency = answer_result["answer_metadata"].get("llm_latency_ms", 0)
        end_to_end_latency = retrieval_latency + llm_latency
        
        return {
            "mode": "standard_rag",
            "query": query,
            "num_retrieved": result["num_retrieved"],
            "retrieved_docs": result["retrieved_docs"],
            "answer": answer_result["answer"],
            "answer_metadata": answer_result["answer_metadata"],
            "metrics": {
                "latency_ms": retrieval_latency,
                "end_to_end_latency_ms": end_to_end_latency,
                "pipeline_stages": result["pipeline_stages"],
                "total_tokens": result["total_tokens_used"],
                "retrieval_scores": result["retrieval_scores"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.api_route("/api/retrieve/advanced", methods=["GET", "POST"])
async def retrieve_advanced(query: str, k: int = 5):
    """Advanced RAG with graph-enhanced retrieval"""
    try:
        if not rag_system.standard_retriever:
            raise HTTPException(status_code=400, detail="No documents loaded")
        
        start_time = time.time()
        unique_docs = len(set(chunk.doc_id for chunk in rag_system.chunks))
        single_document_mode = unique_docs <= 1
        hybrid_k = max(k * 3, 10) if single_document_mode else k * 2
        final_doc_limit = 3 if single_document_mode else max(k, 4)
        rerank_k = max(final_doc_limit + 1, 4) if single_document_mode else k
        
        # Step 1: Hybrid retrieval
        hybrid_result = rag_system.hybrid_searcher.search(query, k=hybrid_k)
        retrieved_docs = hybrid_result["retrieved_docs"]
        
        # Step 2: Reranking
        reranking_result = rag_system.advanced_reranker.rerank(query, retrieved_docs, k=rerank_k)
        retrieved_docs = reranking_result["reranked_docs"]
        
        # Step 3: Semantic graph traversal
        graph_data = {"num_nodes": 0, "num_hops": 0, "paths_explored": []}
        if rag_system.semantic_graph:
            for doc in retrieved_docs[:3]:  # Explore from top 3 docs
                neighbors = rag_system.semantic_graph.get_neighbors(doc["chunk_id"], hops=2)
                graph_data["num_nodes"] += sum(len(v) for v in neighbors.values())
                graph_data["num_hops"] = 2
        
        # Step 4: Context optimization
        optimized_docs, optimization_stats = rag_system.optimizer.optimize_context(
            retrieved_docs,
            query=query,
            compression=True,
            dedup=True,
            min_relevance=0.25 if single_document_mode else 0.3,
            max_docs=final_doc_limit,
        )
        
        retrieval_latency = (time.time() - start_time) * 1000
        
        # Extract advanced metrics
        advanced_metrics = AdvancedRAGMetrics.extract_advanced_metrics(
            graph_data, reranking_result, optimization_stats
        )
        
        # Record metrics
        rag_system.metrics_collector.record_advanced_rag({
            "query": query,
            "num_retrieved": len(optimized_docs),
            "retrieval_scores": [doc.get("reranking_score", 0) for doc in optimized_docs],
            "latency_ms": retrieval_latency,
            "pipeline_stages": ["hybrid_search", "reranking", "graph_traversal", "context_optimization"],
            "total_tokens_used": optimization_stats.get("final_tokens", 0),
            **advanced_metrics
        })
        
        rag_system.benchmark.add_result(
            "advanced_rag", query,
            optimized_docs,
            [doc.get("reranking_score", 0) for doc in optimized_docs],
            retrieval_latency,
            advanced_metrics
        )

        answer_result = _generate_answer(query, optimized_docs, "advanced_rag")
        llm_latency = answer_result["answer_metadata"].get("llm_latency_ms", 0)
        end_to_end_latency = retrieval_latency + llm_latency
        
        return {
            "mode": "advanced_rag",
            "query": query,
            "num_retrieved": len(optimized_docs),
            "retrieved_docs": optimized_docs,
            "answer": answer_result["answer"],
            "answer_metadata": answer_result["answer_metadata"],
            "metrics": {
                "latency_ms": retrieval_latency,
                "end_to_end_latency_ms": end_to_end_latency,
                "pipeline_stages": ["hybrid_search", "reranking", "graph_traversal", "context_optimization"],
                "total_tokens": optimization_stats.get("final_tokens", 0),
                "token_reduction_pct": optimization_stats.get("token_reduction", 0) * 100,
                "graph_metrics": graph_data,
                "reranking_strategies": reranking_result.get("strategies", []),
                "optimization_filters": optimization_stats.get("applied_filters", []),
                "single_document_mode": single_document_mode,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.api_route("/api/retrieve", methods=["GET", "POST"])
async def retrieve(query: str, k: int = 5):
    """Primary retrieval endpoint (Advanced RAG)."""
    return await retrieve_advanced(query, k)

@app.api_route("/api/compare", methods=["GET", "POST"])
async def compare_modes(query: str, k: int = 5):
    """Compare both RAG modes side by side"""
    try:
        # Standard RAG
        standard = await retrieve_standard(query, k)
        
        # Advanced RAG
        advanced = await retrieve_advanced(query, k)
        
        standard_avg_score = (
            sum(standard["metrics"]["retrieval_scores"]) / len(standard["metrics"]["retrieval_scores"])
            if standard["metrics"].get("retrieval_scores") else 0
        )
        advanced_avg_score = (
            sum(doc.get("reranking_score", 0) for doc in advanced["retrieved_docs"]) / len(advanced["retrieved_docs"])
            if advanced.get("retrieved_docs") else 0
        )

        # Create comparison
        comparison = {
            "query": query,
            "standard_rag": {
                "num_docs": standard["num_retrieved"],
                "metrics": standard["metrics"],
                "avg_score": standard_avg_score,
                "answer": standard.get("answer", ""),
                "answer_metadata": standard.get("answer_metadata", {}),
                "top_docs": [
                    {
                        "title": doc["doc_name"],
                        "score": doc.get("cosine_score", 0),
                        "content_length": len(doc["content"].split())
                    }
                    for doc in standard["retrieved_docs"][:3]
                ]
            },
            "advanced_rag": {
                "num_docs": advanced["num_retrieved"],
                "metrics": advanced["metrics"],
                "avg_score": advanced_avg_score,
                "answer": advanced.get("answer", ""),
                "answer_metadata": advanced.get("answer_metadata", {}),
                "top_docs": [
                    {
                        "title": doc["doc_name"],
                        "score": doc.get("reranking_score", 0),
                        "content_length": len(doc["content"].split()),
                        "compressed": doc.get("compressed", False)
                    }
                    for doc in advanced["retrieved_docs"][:3]
                ]
            },
            "comparison_metrics": {
                "latency_difference_ms": advanced["metrics"]["latency_ms"] - standard["metrics"]["latency_ms"],
                "token_reduction_pct": advanced["metrics"].get("token_reduction_pct", 0),
                "score_improvement": advanced_avg_score - standard_avg_score,
                "graph_nodes_explored": advanced["metrics"]["graph_metrics"]["num_nodes"],
            }
        }
        
        return comparison
    except HTTPException:
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics")
async def get_metrics():
    """Get aggregated metrics"""
    return {
        "standard_rag": rag_system.metrics_collector.get_standard_stats(),
        "advanced_rag": rag_system.metrics_collector.get_advanced_stats(),
        "comparison": rag_system.metrics_collector.compare_modes(),
        "benchmark": rag_system.benchmark.get_detailed_comparison()
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "documents_loaded": len(set(chunk.doc_id for chunk in rag_system.chunks)),
        "chunks_indexed": len(rag_system.chunks),
        "ready": len(rag_system.chunks) > 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
