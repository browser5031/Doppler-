"""
Production-ready face comparison using stored embeddings
No ML models needed - just math!
"""
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ProductionFaceComparison:
    """
    Lightweight face comparison using cosine similarity
    Perfect for production with 1GB RAM - no ML models needed!
    """
    
    @staticmethod
    def cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two face embeddings
        Returns: float between 0-1 (1 = identical, 0 = completely different)
        """
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1, dtype=np.float32)
            vec2 = np.array(embedding2, dtype=np.float32)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            magnitude1 = np.linalg.norm(vec1)
            magnitude2 = np.linalg.norm(vec2)
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            similarity = dot_product / (magnitude1 * magnitude2)
            
            # Clamp to 0-1 range
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    @staticmethod
    async def find_similar_faces(
        query_embedding: List[float],
        db_collection,
        top_n: int = 100,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Find similar faces by comparing embeddings using cosine similarity
        
        Args:
            query_embedding: The face embedding to search for (512 floats)
            db_collection: MongoDB collection with face embeddings
            top_n: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)
        
        Returns:
            List of similar faces with similarity scores
        """
        try:
            # Get all faces from database
            faces_cursor = db_collection.find({}, {"_id": 0})
            all_faces = await faces_cursor.to_list(None)
            
            if not all_faces:
                logger.warning("No faces in database to compare against")
                return []
            
            # Calculate similarity for each face
            similarities = []
            for face in all_faces:
                if "embedding" in face and face["embedding"]:
                    try:
                        similarity = ProductionFaceComparison.cosine_similarity(
                            query_embedding,
                            face["embedding"]
                        )
                        
                        if similarity >= min_similarity:
                            similarities.append({
                                "face_id": face.get("face_id", ""),
                                "name": face.get("name"),
                                "year": face.get("year"),
                                "school": face.get("school"),
                                "yearbook_url": face.get("yearbook_url", ""),
                                "page_url": face.get("page_url", ""),
                                "thumbnail_url": face.get("thumbnail_url"),
                                "similarity_score": similarity * 100,  # Convert to percentage
                                "bbox": face.get("bbox", {})
                            })
                    except Exception as e:
                        logger.warning(f"Skipped face due to error: {e}")
                        continue
            
            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            logger.info(f"Found {len(similarities)} similar faces (threshold: {min_similarity})")
            return similarities[:top_n]
            
        except Exception as e:
            logger.error(f"Error in find_similar_faces: {e}")
            return []
    
    @staticmethod
    def extract_embedding_from_image_bytes(image_bytes: bytes) -> List[float]:
        """
        Extract face embedding from image bytes
        This is a placeholder - in production with InsightFace unavailable,
        you'd either:
        1. Use a lightweight external API
        2. Return an error asking user to use development environment
        3. Use pre-computed embeddings
        """
        # This will be implemented with Luxand or return error
        raise NotImplementedError("Face embedding extraction requires ML model or external API")


def get_production_face_comparer():
    """Get singleton instance"""
    return ProductionFaceComparison()
