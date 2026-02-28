"""
Fast face detection using InsightFace (10-100x faster than DeepFace)
"""
import numpy as np
from PIL import Image
import logging
import insightface
from insightface.app import FaceAnalysis

logger = logging.getLogger(__name__)

class FastFaceDetector:
    def __init__(self):
        self.app = None
        self._initialize()
    
    def _initialize(self):
        """Initialize InsightFace model"""
        try:
            logger.info("Initializing InsightFace...")
            self.app = FaceAnalysis(
                name='buffalo_l',
                providers=['CPUExecutionProvider']
            )
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("✓ InsightFace initialized")
        except Exception as e:
            logger.error(f"Failed to initialize InsightFace: {e}")
            self.app = None
    
    def detect_faces(self, image: Image.Image) -> list:
        """
        Detect faces in image - FAST!
        Returns list of face dicts with embeddings
        FILTERS: Only yearbook-style portrait photos (skips collages/group photos)
        """
        if not self.app:
            return []
        
        try:
            # Convert PIL to numpy (RGB -> BGR for InsightFace)
            img_array = np.array(image)
            if len(img_array.shape) == 2:  # Grayscale
                img_array = np.stack([img_array] * 3, axis=-1)
            
            # InsightFace expects BGR
            img_bgr = img_array[:, :, ::-1]
            
            # Detect faces
            faces = self.app.get(img_bgr)
            
            # Calculate image dimensions for filtering
            img_height, img_width = img_array.shape[:2]
            img_area = img_height * img_width
            
            # SMART FILTERING: Skip collage/group photos
            # If too many faces detected, it's likely a collage or group photo
            if len(faces) > 20:  # Typical yearbook page has max 20 portraits
                logger.debug(f"Skipping page with {len(faces)} faces (likely collage)")
                return []
            
            results = []
            for face in faces:
                # Get bounding box
                bbox = face.bbox.astype(int)
                x, y, x2, y2 = bbox
                w = x2 - x
                h = y2 - y
                
                # Calculate face area as percentage of image
                face_area = w * h
                face_percentage = (face_area / img_area) * 100
                
                # FILTER 1: Face must be reasonable size (not tiny collage faces)
                # Yearbook portraits are typically 2-15% of page
                if face_percentage < 0.5:  # Skip tiny faces (collage photos)
                    logger.debug(f"Skipping tiny face: {face_percentage:.2f}% of image")
                    continue
                
                if face_percentage > 50:  # Skip extremely large faces (likely not portrait grid)
                    logger.debug(f"Skipping huge face: {face_percentage:.2f}% of image")
                    continue
                
                # FILTER 2: Face should have reasonable aspect ratio (not stretched)
                aspect_ratio = w / h if h > 0 else 0
                if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                    logger.debug(f"Skipping face with bad aspect ratio: {aspect_ratio:.2f}")
                    continue
                
                # FILTER 3: Minimum face dimensions (skip very small faces)
                if w < 50 or h < 50:
                    logger.debug(f"Skipping small face: {w}x{h}px")
                    continue
                
                # Get embedding (512-dimensional)
                embedding = face.normed_embedding.tolist()
                
                results.append({
                    'embedding': embedding,
                    'facial_area': {
                        'x': int(x),
                        'y': int(y),
                        'w': int(w),
                        'h': int(h)
                    },
                    'x': int(x),
                    'y': int(y),
                    'w': int(w),
                    'h': int(h),
                    'confidence': float(face.det_score),
                    'face_percentage': face_percentage
                })
            
            if results:
                logger.info(f"Filtered {len(results)} valid yearbook portraits from {len(faces)} detected faces")
            
            return results
            
        except Exception as e:
            logger.debug(f"No faces detected: {str(e)}")
            return []

# Global instance
_detector = None

def get_detector():
    """Get global InsightFace detector instance"""
    global _detector
    if _detector is None:
        _detector = FastFaceDetector()
    return _detector
