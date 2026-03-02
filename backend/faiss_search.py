"""
FAISS-powered instant face search with AUTO-REBUILD
Uses Facebook AI Similarity Search for lightning-fast vector matching
Auto-rebuilds index every 100 new faces
"""
import numpy as np
import faiss
import logging
from typing import List, Dict, Any, Optional
import pickle
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class FAISSFaceSearch:
    """
    Lightning-fast face search using FAISS indexing
    Speed: 0.1-0.5 seconds for 100K faces (vs 20+ seconds brute force)
    Auto-rebuilds every 100 new faces
    """
    
    def __init__(self, dimension: int = 512):
        self.dimension = dimension
        self.index = None
        self.face_metadata = []
        self.is_trained = False
        self.last_build_count = 0  # Track face count at last build
        self.rebuild_threshold = 100  # Rebuild every 100 faces
        
    def needs_rebuild(self, current_face_count: int) -> bool:
        """Check if index needs rebuilding"""
        if not self.is_trained:
            return True
        
        new_faces = current_face_count - self.last_build_count
        should_rebuild = new_faces >= self.rebuild_threshold
        
        if should_rebuild:
            logger.info(f"🔄 Index needs rebuild: {new_faces} new faces since last build")
        
        return should_rebuild
        
    def build_index(self, embeddings: np.ndarray, metadata: List[Dict]):
        """
        Build FAISS index from embeddings
        
        Args:
            embeddings: (N, 512) array of face embeddings
            metadata: List of face metadata dicts
        """
        try:
            n_faces = len(embeddings)
            logger.info(f"🔨 Building FAISS index for {n_faces} faces...")
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            
            # Create index
            # Use IndexFlatIP for exact cosine similarity (small datasets)
            # Can upgrade to IndexIVFFlat for large datasets (>100K faces)
            if n_faces < 50000:
                # Exact search for <50K faces
                self.index = faiss.IndexFlatIP(self.dimension)
            else:
                # Approximate search for large datasets
                nlist = min(100, n_faces // 100)  # number of clusters
                quantizer = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
                self.index.train(embeddings)
            
            # Add vectors to index
            self.index.add(embeddings)
            self.face_metadata = metadata
            self.is_trained = True
            self.last_build_count = n_faces  # Track build count
            
            logger.info(f"✅ FAISS index built: {n_faces} faces indexed")
            
        except Exception as e:
            logger.error(f"Error building FAISS index: {e}")
            raise
    
    def search(self, query_embedding: np.ndarray, top_k: int = 100) -> List[Dict[str, Any]]:
        """
        Search for similar faces using FAISS (INSTANT!)
        
        Args:
            query_embedding: (512,) query vector
            top_k: Number of results to return
            
        Returns:
            List of similar faces with similarity scores
        """
        try:
            if not self.is_trained or self.index is None:
                logger.error("Index not built yet!")
                return []
            
            # Normalize query
            query_norm = query_embedding.reshape(1, -1).astype('float32')
            faiss.normalize_L2(query_norm)
            
            # Search (FAST!)
            similarities, indices = self.index.search(query_norm, top_k)
            
            # Build results
            results = []
            for i, (sim, idx) in enumerate(zip(similarities[0], indices[0])):
                if idx < 0 or idx >= len(self.face_metadata):
                    continue
                
                face_meta = self.face_metadata[idx]
                results.append({
                    **face_meta,
                    'similarity_score': float(sim) * 100,  # Convert to percentage
                    'rank': i + 1
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in FAISS search: {e}")
            return []
    
    def save(self, filepath: str):
        """Save index to disk"""
        try:
            faiss.write_index(self.index, f"{filepath}.index")
            with open(f"{filepath}.meta", 'wb') as f:
                pickle.dump(self.face_metadata, f)
            logger.info(f"✓ Saved FAISS index to {filepath}")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    def load(self, filepath: str):
        """Load index from disk"""
        try:
            self.index = faiss.read_index(f"{filepath}.index")
            with open(f"{filepath}.meta", 'rb') as f:
                self.face_metadata = pickle.load(f)
            self.is_trained = True
            logger.info(f"✓ Loaded FAISS index from {filepath}")
        except Exception as e:
            logger.error(f"Error loading index: {e}")


async def build_faiss_index_from_db(db):
    """Build FAISS index from MongoDB faces"""
    try:
        logger.info("Building FAISS index from database...")
        
        # Get all faces with embeddings
        faces = await db.faces.find(
            {'embedding': {'$exists': True, '$ne': None}},
            {'_id': 0}
        ).to_list(None)
        
        if not faces:
            logger.warning("No faces in database")
            return None
        
        # Extract embeddings and metadata
        embeddings = []
        metadata = []
        
        for face in faces:
            try:
                emb = np.array(face['embedding'], dtype=np.float32)
                embeddings.append(emb)
                
                # Store minimal metadata for fast lookup
                metadata.append({
                    'face_id': face.get('face_id', ''),
                    'name': face.get('name'),
                    'year': face.get('year'),
                    'school': face.get('school', ''),
                    'yearbook_url': face.get('yearbook_url', ''),
                    'page_url': face.get('page_url', ''),
                    'thumbnail_url': face.get('thumbnail_url'),
                    'bbox': face.get('bbox', {})
                })
            except:
                continue
        
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # Build index
        faiss_search = FAISSFaceSearch(dimension=512)
        faiss_search.build_index(embeddings_array, metadata)
        
        logger.info(f"✓ FAISS index ready with {len(metadata)} faces")
        return faiss_search
        
    except Exception as e:
        logger.error(f"Error building FAISS index: {e}")
        return None


# Global index instance
_faiss_index = None

async def get_faiss_index(db, force_rebuild=False):
    """
    Get or build FAISS index with auto-rebuild
    Rebuilds every 100 new faces automatically
    """
    global _faiss_index
    
    # Get current face count
    current_count = await db.faces.count_documents({'embedding': {'$exists': True, '$ne': None}})
    
    # Check if rebuild needed
    should_rebuild = (
        _faiss_index is None or 
        force_rebuild or 
        _faiss_index.needs_rebuild(current_count)
    )
    
    if should_rebuild:
        logger.info(f"🔄 Rebuilding FAISS index (current: {current_count} faces)")
        _faiss_index = await build_faiss_index_from_db(db)
    
    return _faiss_index
