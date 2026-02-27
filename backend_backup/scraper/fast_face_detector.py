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
            
            results = []
            for face in faces:
                # Get bounding box
                bbox = face.bbox.astype(int)
                x, y, x2, y2 = bbox
                w = x2 - x
                h = y2 - y
                
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
                    'confidence': float(face.det_score)
                })
            
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
