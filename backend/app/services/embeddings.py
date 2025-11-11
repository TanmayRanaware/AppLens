"""Embeddings service for semantic search"""
from typing import List, Optional
from openai import OpenAI
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating embeddings"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "text-embedding-ada-002"
        self.dimension = 1536
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a text"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Chunk text into smaller pieces"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        return chunks

