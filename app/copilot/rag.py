"""
Unified RAG System for RNA Design Documents

This module provides a comprehensive RAG system that supports both text and multimodal
document processing using ChromaDB for vector storage and CLIP for multimodal embeddings.
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import torch
from transformers import CLIPProcessor, CLIPModel
import markdown

logger = logging.getLogger(__name__)


class DocumentMetadata:
    """Metadata for document management"""
    
    def __init__(self, file_path: str, title: str = "", authors: str = "", 
                 year: int = None, doi: str = "", abstract: str = ""):
        self.file_path = file_path
        self.title = title
        self.authors = authors
        self.year = year
        self.doi = doi
        self.abstract = abstract
        self.file_hash = self._calculate_file_hash()
        self.last_updated = datetime.now().isoformat()
    
    def _calculate_file_hash(self) -> str:
        """Calculate MD5 hash of the file for change detection"""
        try:
            with open(self.file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "file_path": self.file_path,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "abstract": self.abstract,
            "file_hash": self.file_hash,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        """Create from dictionary"""
        instance = cls(
            file_path=data["file_path"],
            title=data.get("title", ""),
            authors=data.get("authors", ""),
            year=data.get("year"),
            doi=data.get("doi", ""),
            abstract=data.get("abstract", "")
        )
        instance.file_hash = data.get("file_hash", "")
        instance.last_updated = data.get("last_updated", "")
        return instance


class RNADesignRAGSystem:
    """
    Unified RAG system for processing PDF and Markdown documents.
    Supports both text and images from PDF documents, and text content from Markdown files.
    Uses ChromaDB for vector storage and CLIP for multimodal embeddings.
    """

    def __init__(self, data_directory: str = "data", chroma_db_path: str = "data/chroma_db"):
        """Initialize the RAG system"""
        self.data_directory = Path(data_directory)
        self.chroma_db_path = Path(chroma_db_path)
        self.images_directory = self.data_directory / "images"
        self.is_building = False
        
        # Create directories
        self.data_directory.mkdir(exist_ok=True)
        self.chroma_db_path.mkdir(exist_ok=True)
        self.images_directory.mkdir(exist_ok=True)
        
        # Initialize models
        self.text_embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collections
        self.text_collection = self.chroma_client.get_or_create_collection(
            name="pdf_texts",
            metadata={"description": "PDF text chunks with embeddings"}
        )
        
        self.image_collection = self.chroma_client.get_or_create_collection(
            name="pdf_images",
            metadata={"description": "PDF images with CLIP embeddings"}
        )
        
        # Metadata storage
        self.documents_metadata = {}
        self.images_metadata = {}
        self._load_metadata()
        
        logger.info("RAG system initialized successfully")

    def _load_metadata(self):
        """Load metadata from JSON files"""
        metadata_file = self.chroma_db_path / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                    self.documents_metadata = data.get("documents", {})
                    self.images_metadata = data.get("images", {})
                logger.info(f"Loaded metadata: {len(self.documents_metadata)} documents, {len(self.images_metadata)} images")
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
                self.documents_metadata = {}
                self.images_metadata = {}

    def _save_metadata(self):
        """Save metadata to JSON file"""
        try:
            metadata_file = self.chroma_db_path / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump({
                    "documents": self.documents_metadata,
                    "images": self.images_metadata
                }, f, indent=4)
            logger.info("Metadata saved successfully")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of the file"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ""

    def _extract_text_from_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text from PDF and split into chunks"""
        try:
            reader = PdfReader(pdf_path)
            text_chunks = []
            
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    # Split text into chunks
                    chunk_size = 1000
                    chunk_overlap = 200
                    
                    for i in range(0, len(text), chunk_size - chunk_overlap):
                        chunk_text = text[i:i + chunk_size]
                        if chunk_text.strip():
                            text_chunks.append({
                                "text": chunk_text.strip(),
                                "page": page_num,
                                "chunk_id": f"{pdf_path.stem}_page_{page_num}_chunk_{i//(chunk_size - chunk_overlap)}"
                            })
            
            logger.info(f"Extracted {len(text_chunks)} text chunks from {pdf_path.name}")
            return text_chunks
            
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            return []

    def _extract_images_from_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract images from PDF and generate descriptions"""
        try:
            images = convert_from_path(pdf_path, dpi=200)
            extracted_images = []
            
            for page_num, image in enumerate(images, 1):
                # Save image
                image_filename = f"{pdf_path.stem}_page_{page_num}.png"
                image_path = self.images_directory / image_filename
                image.save(image_path, 'PNG')
                
                # Generate description using CLIP
                description = self._generate_image_description(image)
                
                # Optional: Extract text from image using OCR
                ocr_text = ""
                try:
                    ocr_text = pytesseract.image_to_string(image)
                    ocr_text = ocr_text.strip()
                except Exception as e:
                    logger.debug(f"OCR failed for {image_path}: {e}")
                
                image_info = {
                    "image_path": str(image_path),
                    "description": description,
                    "ocr_text": ocr_text,
                    "page": page_num,
                    "source_file": str(pdf_path),
                    "image_hash": self._calculate_file_hash(image_path)
                }
                
                extracted_images.append(image_info)
            
            logger.info(f"Extracted {len(extracted_images)} images from {pdf_path.name}")
            return extracted_images
            
        except Exception as e:
            logger.error(f"Failed to extract images from {pdf_path}: {e}")
            return []

    def _generate_image_description(self, image: Image.Image) -> str:
        """Generate description for image using CLIP"""
        try:
            # Resize image if too large
            if image.size[0] > 512 or image.size[1] > 512:
                image = image.resize((512, 512), Image.Resampling.LANCZOS)
            
            # Generate description using CLIP
            inputs = self.clip_processor(images=image, return_tensors="pt")
            
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return f"Image from PDF document (CLIP features extracted)"
            
        except Exception as e:
            logger.error(f"Failed to generate image description: {e}")
            return "Image from PDF document"

    def _get_text_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get text embeddings using sentence transformers"""
        try:
            embeddings = self.text_embedder.encode(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate text embeddings: {e}")
            return np.array([])

    def _get_image_embeddings(self, images: List[Image.Image]) -> np.ndarray:
        """Get image embeddings using CLIP"""
        try:
            embeddings = []
            for image in images:
                # Resize image if needed
                if image.size[0] > 512 or image.size[1] > 512:
                    image = image.resize((512, 512), Image.Resampling.LANCZOS)
                
                inputs = self.clip_processor(images=image, return_tensors="pt")
                
                with torch.no_grad():
                    image_features = self.clip_model.get_image_features(**inputs)
                    image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                    embeddings.append(image_features.numpy().flatten())
            
            return np.array(embeddings)
        except Exception as e:
            logger.error(f"Failed to generate image embeddings: {e}")
            return np.array([])

    def _process_markdown(self, file_path: Path) -> Tuple[List[str], Dict[str, Any]]:
        """Process a Markdown file and extract text chunks"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract text chunks by splitting on headers and paragraphs
            lines = content.split('\n')
            chunks = []
            current_chunk = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk).strip()
                        if chunk_text:
                            chunks.append(chunk_text)
                        current_chunk = []
                elif line.startswith('#'):
                    # Save previous chunk if exists
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk).strip()
                        if chunk_text:
                            chunks.append(chunk_text)
                        current_chunk = []
                    # Start new chunk with header
                    current_chunk = [line]
                else:
                    current_chunk.append(line)
            
            # Add final chunk
            if current_chunk:
                chunk_text = '\n'.join(current_chunk).strip()
                if chunk_text:
                    chunks.append(chunk_text)
            
            # Extract metadata
            metadata = {
                'file_type': 'markdown',
                'file_name': file_path.name,
                'file_path': str(file_path),
                'total_chunks': len(chunks),
                'content_length': len(content)
            }
            
            # Try to extract title from first header
            if chunks and chunks[0].startswith('#'):
                metadata['title'] = chunks[0].replace('#', '').strip()
            
            logger.info(f"Extracted {len(chunks)} text chunks from {file_path.name}")
            return chunks, metadata
            
        except Exception as e:
            logger.error(f"Failed to process markdown file {file_path}: {e}")
            return [], {}

    def add_document(self, file_path: str, title: str = "", authors: str = "", 
                     year: int = None, doi: str = "", abstract: str = "") -> bool:
        """Add a PDF or Markdown document to the RAG system"""
        file_path_obj = Path(file_path)
        if not file_path_obj.is_file():
            logger.error(f"Invalid file path: {file_path}")
            return False
        
        file_extension = file_path_obj.suffix.lower()
        if file_extension not in [".pdf", ".md"]:
            logger.error(f"Unsupported file type: {file_extension}. Only PDF and Markdown files are supported.")
            return False

        doc_hash = self._calculate_file_hash(file_path_obj)
        if doc_hash in self.documents_metadata:
            logger.info(f"Document {file_path_obj.name} already exists")
            return True

        logger.info(f"Processing document: {file_path_obj.name}")
        
        try:
            text_chunks = []
            image_chunks = []
            
            if file_extension == ".pdf":
                # Extract text from PDF
                text_chunks = self._extract_text_from_pdf(file_path_obj)
                if not text_chunks:
                    logger.warning(f"No text extracted from {file_path_obj.name}")
                    return False
                
                # Extract images from PDF
                image_chunks = self._extract_images_from_pdf(file_path_obj)
                
            elif file_extension == ".md":
                # Process Markdown file
                text_chunks_raw, md_metadata = self._process_markdown(file_path_obj)
                if not text_chunks_raw:
                    logger.warning(f"No text extracted from {file_path_obj.name}")
                    return False
                
                # Convert to text_chunks format
                text_chunks = []
                for i, chunk_text in enumerate(text_chunks_raw):
                    text_chunks.append({
                        "text": chunk_text,
                        "chunk_id": i,
                        "page": 0  # Markdown doesn't have pages
                    })
                
                # Use extracted title if available
                if not title and "title" in md_metadata:
                    title = md_metadata["title"]
            
            # Process text chunks
            if text_chunks:
                texts = [chunk["text"] for chunk in text_chunks]
                text_embeddings = self._get_text_embeddings(texts)
                
                if len(text_embeddings) > 0:
                    # Add to ChromaDB
                    ids = [f"{doc_hash}_{chunk['chunk_id']}" for chunk in text_chunks]
                    metadatas = [{
                        "source": str(file_path_obj),
                        "page": chunk["page"],
                        "chunk_id": chunk["chunk_id"],
                        "file_type": file_extension,
                        "title": title or "",
                        "authors": authors or "",
                        "year": year or 0,
                        "doi": doi or "",
                        "abstract": abstract or ""
                    } for chunk in text_chunks]
                    
                    self.text_collection.add(
                        ids=ids,
                        embeddings=text_embeddings.tolist(),
                        documents=texts,
                        metadatas=metadatas
                    )
                    
                    logger.info(f"Added {len(text_chunks)} text chunks to ChromaDB")

            # Process image chunks (only for PDF files)
            if image_chunks and file_extension == ".pdf":
                images = [Image.open(chunk["image_path"]) for chunk in image_chunks]
                image_embeddings = self._get_image_embeddings(images)
                
                if len(image_embeddings) > 0:
                    # Add to ChromaDB
                    ids = [f"{doc_hash}_{chunk['image_hash']}" for chunk in image_chunks]
                    metadatas = [{
                        "source": chunk["source_file"],
                        "page": chunk["page"],
                        "image_path": chunk["image_path"],
                        "description": chunk["description"],
                        "ocr_text": chunk["ocr_text"],
                        "title": title or "",
                        "authors": authors or "",
                        "year": year or 0,
                        "doi": doi or "",
                        "abstract": abstract or ""
                    } for chunk in image_chunks]
                    
                    documents = [chunk["description"] for chunk in image_chunks]
                    
                    self.image_collection.add(
                        ids=ids,
                        embeddings=image_embeddings.tolist(),
                        documents=documents,
                        metadatas=metadatas
                    )
                    
                    logger.info(f"Added {len(image_chunks)} image chunks to ChromaDB")

            # Update metadata
            self.documents_metadata[doc_hash] = {
                "file_path": str(file_path_obj),
                "title": title,
                "authors": authors,
                "year": year,
                "doi": doi,
                "abstract": abstract,
                "text_chunks": len(text_chunks),
                "image_chunks": len(image_chunks)
            }
            
            for chunk in image_chunks:
                self.images_metadata[chunk["image_hash"]] = chunk
            
            self._save_metadata()
            
            logger.info(f"Successfully processed document: {file_path_obj.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process document {file_path_obj.name}: {e}")
            return False

    def add_documents_from_directory(self) -> int:
        """Add all PDF and Markdown documents from the data directory"""
        pdf_files = list(self.data_directory.glob("*.pdf"))
        md_files = list(self.data_directory.glob("*.md"))
        all_files = pdf_files + md_files
        added_count = 0
        
        # Only set building state if there are files to process
        if all_files:
            self.is_building = True
        
        try:
            for file_path in all_files:
                if self.add_document(str(file_path)):
                    added_count += 1
            
            logger.info(f"Added {added_count} documents from directory")
        finally:
            # Clear building state when done
            self.is_building = False
        
        return added_count

    def search_documents(self, query: str, k: int = 30, include_images: bool = True) -> List[Dict[str, Any]]:
        """Search documents using multimodal retrieval"""
        try:
            results = []
            
            # Text search
            query_embedding = self.text_embedder.encode([query])[0]
            text_results = self.text_collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=k
            )
            
            for i, (doc, metadata, distance) in enumerate(zip(
                text_results['documents'][0],
                text_results['metadatas'][0],
                text_results['distances'][0]
            )):
                # Calculate similarity score (higher is better)
                similarity_score = 1 - distance
                results.append({
                    "type": "text",
                    "content": doc,
                    "metadata": metadata,
                    "score": similarity_score,
                    "rank": i + 1
                })
            
            # Image search if requested
            if include_images:
                try:
                    # Use text embedding for image search to avoid dimension mismatch
                    image_results = self.image_collection.query(
                        query_embeddings=[query_embedding.tolist()],
                        n_results=k
                    )
                except Exception as e:
                    logger.warning(f"Image search failed due to dimension mismatch: {e}")
                    # Skip image search if there's a dimension mismatch
                    image_results = {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
                
                for i, (doc, metadata, distance) in enumerate(zip(
                    image_results['documents'][0],
                    image_results['metadatas'][0],
                    image_results['distances'][0]
                )):
                    similarity_score = 1 - distance
                    results.append({
                        "type": "image",
                        "content": doc,
                        "metadata": metadata,
                        "score": similarity_score,
                        "rank": i + 1
                    })
            
            # Sort by score
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # Debug logging
            logger.info(f"Search query: '{query}'")
            logger.info(f"Found {len(results)} results")
            for i, result in enumerate(results[:3]):  # Log top 3 results
                logger.info(f"Result {i+1}: score={result['score']:.3f}, type={result['type']}, content_preview={result['content'][:100]}...")
            
            return results[:k]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_rag_context(self, query: str, max_chunks: int = 15) -> Tuple[str, List[Dict[str, Any]]]:
        """Get RAG context for a query with citations (text-only for compatibility)"""
        try:
            results = self.search_documents(query, k=max_chunks, include_images=False)
            
            if not results:
                return "No relevant documents found in the knowledge base.", []
            
            # Build context with citations
            context_parts = []
            citations = []
            seen_sources = set()
            citation_number = 1
            
            for result in results:
                source = result['metadata']['source']
                page = result['metadata']['page']
                source_key = f"{source}_{page}"
                
                # Skip if we've already seen this source+page combination
                if source_key in seen_sources:
                    continue
                    
                seen_sources.add(source_key)
                
                # Create citation
                citation = self._format_citation(result, citation_number)
                citations.append(citation)
                
                # Add to context with better formatting
                content = result['content'].strip()
                if content:
                    context_parts.append(f"[{citation_number}] {content}")
                    citation_number += 1
            
            context = "\n\n".join(context_parts)
            
            # Add a summary header to make the context more useful
            if context:
                context = f"""RELEVANT LITERATURE FOR QUERY: '{query}'

{context}

IMPORTANT INSTRUCTIONS:
- The above literature contains relevant information about the query
- Use this information to provide a comprehensive and accurate answer
- Include specific details, metrics, and technical information from the literature
- If the literature contains tables, figures, or performance data, incorporate these details into your response
- Base your answer primarily on the provided literature context"""
            
            logger.info(f"RAG context generated: {len(context)} characters, {len(citations)} citations")
            return context, citations
            
        except Exception as e:
            logger.error(f"Failed to get RAG context: {e}")
            return "No relevant context found.", []
    def get_multimodal_context(self, query: str, max_text_chunks: int = 5, 
                              max_images: int = 3) -> Tuple[str, List[Dict[str, Any]]]:
        """Get multimodal context including both text and images"""
        try:
            results = self.search_documents(query, k=max_text_chunks + max_images, include_images=True)
            
            text_contexts = []
            image_contexts = []
            citations = []
            seen_sources = set()
            
            for result in results:
                source = result["metadata"]["source"]
                page = result["metadata"]["page"]
                source_key = f"{source}_{page}"
                
                # Skip if we've already seen this source+page combination
                if source_key in seen_sources:
                    continue
                    
                seen_sources.add(source_key)
                
                if result["type"] == "text":
                    text_contexts.append(result["content"])
                    citations.append({
                        "text": f"Text from {Path(result['metadata']['source']).stem}, Page {result['metadata']['page']}",
                        "source": result["metadata"]["source"],
                        "page": result["metadata"]["page"],
                        "score": result["score"],
                        "type": "text"
                    })
                elif result["type"] == "image":
                    image_contexts.append(result)
                    citations.append({
                        "text": f"Image from {Path(result['metadata']['source']).stem}, Page {result['metadata']['page']}",
                        "source": result["metadata"]["source"],
                        "page": result["metadata"]["page"],
                        "score": result["score"],
                        "type": "image"
                    })
            
            # Combine contexts
            context_parts = []
            if text_contexts:
                context_parts.append("TEXT CONTEXT:\n" + "\n\n".join(text_contexts))
            
            if image_contexts:
                image_descriptions = [f"Image: {img['content']}" for img in image_contexts]
                context_parts.append("IMAGE CONTEXT:\n" + "\n".join(image_descriptions))
            
            context = "\n\n".join(context_parts) if context_parts else "No relevant context found."
            return context, citations
            
        except Exception as e:
            logger.error(f"Failed to get multimodal context: {e}")
            return "No relevant context found.", []

    def _format_citation(self, result: Dict[str, Any], citation_number: int) -> Dict[str, Any]:
        """Format a citation for a search result"""
        metadata = result['metadata']
        
        # Create citation text
        authors = metadata.get('authors', 'Unknown Authors')
        title = metadata.get('title', 'Untitled')
        year = metadata.get('year', 'Unknown Year')
        doi = metadata.get('doi', '')
        
        citation_text = f"[{citation_number}] {authors} ({year}). {title}"
        if doi:
            citation_text += f". DOI: {doi}"
        
        return {
            "number": citation_number,
            "text": citation_text,
            "title": title,
            "authors": authors,
            "year": year,
            "doi": doi,
            "source_file": metadata.get('source', ''),
            "similarity_score": result['score'],
            "content_preview": result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
        }

    def get_document_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific document"""
        for doc_hash, metadata in self.documents_metadata.items():
            if metadata.get("file_path") == file_path:
                return metadata
        return None

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all processed documents"""
        documents = []
        for doc_hash, metadata in self.documents_metadata.items():
            documents.append({
                "hash": doc_hash,
                "title": metadata.get("title", "Untitled"),
                "authors": metadata.get("authors", "Unknown"),
                "year": metadata.get("year", "Unknown"),
                "doi": metadata.get("doi", "N/A"),
                "file_path": metadata.get("file_path", ""),
                "text_chunks": metadata.get("text_chunks", 0),
                "image_chunks": metadata.get("image_chunks", 0)
            })
        return documents

    def remove_document(self, file_path: str) -> bool:
        """Remove a document from the system"""
        try:
            # Find document by file path
            doc_hash_to_remove = None
            for doc_hash, metadata in self.documents_metadata.items():
                if metadata.get("file_path") == file_path:
                    doc_hash_to_remove = doc_hash
                    break
            
            if not doc_hash_to_remove:
                logger.warning(f"Document not found: {file_path}")
                return False
            
            # Remove from metadata
            del self.documents_metadata[doc_hash_to_remove]
            
            # Remove from ChromaDB (simplified approach)
            # In production, you'd want more sophisticated handling
            self._save_metadata()
            
            logger.info(f"Removed document: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove document {file_path}: {e}")
            return False

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            "total_documents": len(self.documents_metadata),
            "total_images": len(self.images_metadata),
            "text_collection_count": self.text_collection.count(),
            "image_collection_count": self.image_collection.count(),
            "data_directory": str(self.data_directory),
            "chroma_db_path": str(self.chroma_db_path),
            "is_building": self.is_building,
            "vector_store_initialized": True,
            "image_processing_available": True
        }
