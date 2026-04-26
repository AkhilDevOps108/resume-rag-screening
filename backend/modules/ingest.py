"""
Document Ingestion Module
Handles multi-document upload, parsing, and chunking
Supports PDF, TXT, and Markdown files
"""

import os
from typing import List, Dict, Tuple
from pathlib import Path
import markdown
from datetime import datetime
import hashlib
import re

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None


class DocumentChunk:
    """Represents a chunk of a document"""
    def __init__(self, content: str, doc_id: str, doc_name: str, chunk_idx: int, 
                 start_char: int, end_char: int, metadata: Dict = None):
        self.content = content
        self.doc_id = doc_id
        self.doc_name = doc_name
        self.chunk_idx = chunk_idx
        self.start_char = start_char
        self.end_char = end_char
        self.metadata = metadata or {}
        self.chunk_id = f"{doc_id}_chunk_{chunk_idx}"
    
    def to_dict(self):
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "chunk_idx": self.chunk_idx,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "metadata": self.metadata
        }


class DocumentProcessor:
    """Process and chunk documents"""
    
    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def _normalize_text(self, text: str) -> str:
        """Normalize extracted text before chunking."""
        content = text or ""
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        content = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", content)
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r"[ \t]+", " ", content)
        return content.strip()

    def _split_into_units(self, text: str) -> List[str]:
        """Split text into paragraph/sentence units for better chunk boundaries."""
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        units = []

        for paragraph in paragraphs:
            if len(paragraph) <= self.chunk_size:
                units.append(paragraph)
                continue

            sentences = [piece.strip() for piece in re.split(r"(?<=[.!?])\s+", paragraph) if piece.strip()]
            if sentences:
                units.extend(sentences)
            else:
                units.append(paragraph)

        return units

    def _make_chunk(self, content: str, doc_id: str, doc_name: str, chunk_idx: int, start_char: int) -> DocumentChunk:
        normalized_content = content.strip()
        content_hash = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()
        return DocumentChunk(
            content=normalized_content,
            doc_id=doc_id,
            doc_name=doc_name,
            chunk_idx=chunk_idx,
            start_char=start_char,
            end_char=start_char + len(normalized_content),
            metadata={
                "created_at": datetime.now().isoformat(),
                "file_path": doc_name,
                "content_hash": content_hash,
            }
        )
    
    def parse_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        extraction_attempts = []

        if pdfplumber is not None:
            try:
                text_parts = []
                with pdfplumber.open(file_path) as pdf:
                    for page_index, page in enumerate(pdf.pages, 1):
                        page_text = (page.extract_text(x_tolerance=2, y_tolerance=2) or "").strip()
                        if page_text:
                            text_parts.append(f"[Page {page_index}]\n{page_text}")
                pdfplumber_text = "\n\n".join(text_parts).strip()
                if pdfplumber_text:
                    return pdfplumber_text
                extraction_attempts.append("pdfplumber returned no text")
            except Exception as exc:
                extraction_attempts.append(f"pdfplumber failed: {exc}")

        if PyPDF2 is not None:
            try:
                text_parts = []
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page_index, page in enumerate(reader.pages, 1):
                        page_text = (page.extract_text() or "").strip()
                        if page_text:
                            text_parts.append(f"[Page {page_index}]\n{page_text}")
                pypdf2_text = "\n\n".join(text_parts).strip()
                if pypdf2_text:
                    return pypdf2_text
                extraction_attempts.append("PyPDF2 returned no text")
            except Exception as exc:
                extraction_attempts.append(f"PyPDF2 failed: {exc}")

        print(f"Error parsing PDF {file_path}: {'; '.join(extraction_attempts) or 'no available parser'}")
        return ""
    
    def parse_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Error parsing TXT {file_path}: {e}")
            return ""
    
    def parse_markdown(self, file_path: str) -> str:
        """Extract text from Markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                md_text = f.read()
            # For now, just return the raw markdown text
            # In production, could convert to HTML then extract text
            return md_text.strip()
        except Exception as e:
            print(f"Error parsing Markdown {file_path}: {e}")
            return ""
    
    def parse_document(self, file_path: str) -> str:
        """Parse document based on file extension"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return self.parse_pdf(file_path)
        elif file_ext == '.txt':
            return self.parse_txt(file_path)
        elif file_ext in ['.md', '.markdown']:
            return self.parse_markdown(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
    
    def chunk_text(self, text: str, doc_id: str, doc_name: str) -> List[DocumentChunk]:
        """Split text into overlapping chunks"""
        chunks = []
        
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return chunks

        units = self._split_into_units(normalized_text)
        
        current_chunk = ""
        current_start = 0
        chunk_idx = 0

        for unit in units:
            candidate = unit if not current_chunk else f"{current_chunk}\n{unit}"
            if len(candidate) <= self.chunk_size:
                if current_chunk:
                    current_chunk = candidate
                else:
                    current_chunk = unit
            else:
                if current_chunk:
                    chunks.append(self._make_chunk(current_chunk, doc_id, doc_name, chunk_idx, current_start))
                    chunk_idx += 1

                # Handle overlap
                overlap_text = current_chunk[-self.overlap:] if len(current_chunk) > self.overlap else ""
                current_start += len(current_chunk) - len(overlap_text)
                current_chunk = f"{overlap_text}\n{unit}".strip() if overlap_text else unit
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(self._make_chunk(current_chunk, doc_id, doc_name, chunk_idx, current_start))
        
        return chunks
    
    def process_file(self, file_path: str, doc_id: str = None) -> List[DocumentChunk]:
        """Process a single file and return chunks"""
        if not doc_id:
            doc_id = Path(file_path).stem
        
        doc_name = Path(file_path).name
        
        # Parse document
        text = self.parse_document(file_path)
        
        if not text:
            return []
        
        # Chunk the text
        chunks = self.chunk_text(text, doc_id, doc_name)
        
        return chunks
    
    def process_files(self, file_paths: List[str]) -> List[DocumentChunk]:
        """Process multiple files and return all chunks"""
        all_chunks = []
        
        for file_path in file_paths:
            chunks = self.process_file(file_path)
            all_chunks.extend(chunks)
        
        return all_chunks


if __name__ == "__main__":
    processor = DocumentProcessor(chunk_size=512, overlap=64)
    # Test with sample files if they exist
    print("Document processor initialized successfully")
