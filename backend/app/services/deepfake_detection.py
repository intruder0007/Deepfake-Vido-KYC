"""
Deepfake Detection Service
Analyzes micro-textures, blink rates, temporal inconsistencies,
and other indicators of AI-generated or manipulated content.
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from scipy import signal
from scipy.fftpack import fft
import warnings

warnings.filterwarnings('ignore')

# Try to import MediaPipe
try:
    import mediapipe as mp
    try:
        mp_face_mesh = mp.solutions.face_mesh
        MEDIAPIPE_AVAILABLE = True
    except (AttributeError, ImportError):
        MEDIAPIPE_AVAILABLE = False
except ImportError:
    MEDIAPIPE_AVAILABLE = False

# Always load OpenCV cascade classifiers as fallback
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)


@dataclass
class DeepfakeIndicator:
    """Indicator of potential deepfake"""
    indicator_type: str
    confidence: float
    details: Dict


class DeepfakeDetector:
    """
    Detects deepfakes and face manipulation through:
    - Micro-texture analysis
    - Blink rate and pattern analysis  
    - Temporal inconsistencies
    - Frequency domain analysis (FFT)
    - Face geometry inconsistencies
    """
    
    def __init__(self, history_size: int = 30):
        self.history_size = history_size
        self.use_mediapipe = MEDIAPIPE_AVAILABLE
        
        if self.use_mediapipe:
            try:
                self.face_mesh = mp_face_mesh.FaceMesh(
                    static_image_mode=False,
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
            except Exception:
                self.use_mediapipe = False
        
        # History for temporal analysis
        self.frame_history = []
        self.blink_history = []
        self.face_geometry_history = []
        self.eye_gaze_history = []
    
    def detect_faces_cascade(self, frame: np.ndarray) -> List[Tuple]:
        """
        Detect faces using OpenCV cascade classifier with preprocessing.
        Returns list of face rectangles (x, y, w, h).
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Preprocess for better detection
            # Apply histogram equalization to improve contrast
            gray = cv2.equalizeHist(gray)
            
            # Try multiple scale factors for more reliable detection
            faces = []
            for scale_factor in [1.05, 1.1, 1.2]:
                detected = face_cascade.detectMultiScale(
                    gray, 
                    scaleFactor=scale_factor, 
                    minNeighbors=4, 
                    minSize=(20, 20),
                    maxSize=(frame.shape[1]-10, frame.shape[0]-10)
                )
                faces.extend(detected)
            
            # Remove duplicates
            if faces:
                faces = self._remove_duplicate_faces(faces)
            
            return faces
        except Exception:
            return []
    
    def _remove_duplicate_faces(self, faces: List[Tuple]) -> List[Tuple]:
        """Remove duplicate/overlapping face detections."""
        if len(faces) <= 1:
            return list(faces)
        
        # Keep only the largest faces
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        
        unique_faces = [faces[0]]
        for face in faces[1:]:
            x, y, w, h = face
            is_duplicate = False
            for ux, uy, uw, uh in unique_faces:
                overlap = (min(x+w, ux+uw) - max(x, ux)) * (min(y+h, uy+uh) - max(y, uy))
                if overlap > (w * h * 0.3):
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_faces.append(face)
        
        return unique_faces[:1]  # Return only the top face
    
    def analyze_micro_textures(self, frame: np.ndarray, face_region: Tuple) -> Dict:
        """
        Analyze texture patterns that are artifacts of deepfakes
        (e.g., smooth transitions, blending artifacts at face boundary)
        """
        try:
            if face_region is None:
                # Analyze whole frame when face region not available
                # Use center region as approximation
                h, w = frame.shape[:2]
                x, y = int(w * 0.1), int(h * 0.1)
                w_region, h_region = int(w * 0.8), int(h * 0.8)
                face_crop = frame[y:y+h_region, x:x+w_region]
            else:
                x, y, w, h = face_region
                face_crop = frame[y:y+h, x:x+w]
            
            # Convert to grayscale for texture analysis
            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            
            # Compute Laplacian for edge/texture detection
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            laplacian_variance = np.var(laplacian)
            
            # Compute local binary patterns (simplified)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Analyze texture smoothness using Gabor filters
            smoothness = self._analyze_smoothness(gray)
            
            # Boundary artifacts (common in face swaps)
            boundary_artifacts = self._detect_boundary_artifacts(face_crop, face_region if face_region else (0, 0, face_crop.shape[1], face_crop.shape[0]))
            
            # Compression artifacts
            compression_artifacts = self._detect_compression_artifacts(gray)
            
            return {
                "laplacian_variance": float(laplacian_variance),
                "edge_density": float(edge_density),
                "smoothness_score": float(smoothness),
                "boundary_artifacts_confidence": float(boundary_artifacts),
                "compression_artifacts_confidence": float(compression_artifacts),
                "anomaly_score": self._compute_texture_anomaly_score(
                    laplacian_variance, edge_density, smoothness, boundary_artifacts
                )
            }
        except Exception as e:
            return {
                "laplacian_variance": 0.0,
                "edge_density": 0.0,
                "smoothness_score": 0.5,
                "boundary_artifacts_confidence": 0.0,
                "compression_artifacts_confidence": 0.0,
                "anomaly_score": 0.2,
                "error": str(e)
            }
    
    def _analyze_smoothness(self, gray_face: np.ndarray) -> float:
        """Analyze if texture is unnaturally smooth (deepfake indicator)"""
        # Apply median filter to enhance smooth regions
        median = cv2.medianBlur(gray_face, 5)
        
        # Calculate difference from original
        diff = cv2.absdiff(gray_face, median)
        smoothness = 1.0 - (np.mean(diff) / 255.0)
        
        return np.clip(smoothness, 0, 1)
    
    def _detect_boundary_artifacts(self, face_crop: np.ndarray, face_region: Tuple) -> float:
        """Detect unnatural transitions at face boundaries"""
        h, w = face_crop.shape[:2]
        
        # Extract border regions
        border_size = min(20, h // 5, w // 5)
        
        if border_size < 5:
            return 0.0
        
        # Analyze top, bottom, left, right borders
        borders = [
            face_crop[:border_size, :],  # Top
            face_crop[-border_size:, :],  # Bottom
            face_crop[:, :border_size],  # Left
            face_crop[:, -border_size:]   # Right
        ]
        
        # Calculate variance in borders (high variance = artifacts)
        border_variances = []
        for border in borders:
            if border.size > 0:
                gray_border = cv2.cvtColor(border, cv2.COLOR_BGR2GRAY) if len(border.shape) == 3 else border
                border_variances.append(np.var(gray_border))
        
        artifact_score = np.mean(border_variances) / 100.0 if border_variances else 0.0
        return np.clip(artifact_score, 0, 1)
    
    def _detect_compression_artifacts(self, gray_face: np.ndarray) -> float:
        """Detect JPEG and codec compression artifacts"""
        # Apply DCT and analyze frequency patterns
        dct = cv2.dct(np.float32(gray_face) / 255.0)
        
        # Compression creates artifacts at specific frequencies
        # High energy at block boundaries indicates compression
        block_artifacts = 0.0
        
        for i in range(0, gray_face.shape[0], 8):
            for j in range(0, gray_face.shape[1], 8):
                block_end_i = min(i + 8, dct.shape[0])
                block_end_j = min(j + 8, dct.shape[1])
                
                block = dct[i:block_end_i, j:block_end_j]
                
                if block.size > 0:
                    # Check edges of DCT block
                    edges = np.concatenate([
                        block[0, :],
                        block[-1, :],
                        block[:, 0],
                        block[:, -1]
                    ])
                    
                    block_artifacts += np.sum(np.abs(edges))
        
        artifact_score = block_artifacts / (gray_face.shape[0] * gray_face.shape[1])
        return np.clip(artifact_score / 100.0, 0, 1)
    
    def _compute_texture_anomaly_score(self, laplacian_var: float, edge_density: float,
                                      smoothness: float, boundary_artifacts: float) -> float:
        """Compute overall texture anomaly score"""
        # Deepfakes often have: low laplacian variance, low edge density, high smoothness
        texture_score = (
            (1.0 - np.clip(laplacian_var / 1000.0, 0, 1)) * 0.3 +
            (1.0 - edge_density) * 0.3 +
            smoothness * 0.2 +
            boundary_artifacts * 0.2
        )
        
        return np.clip(texture_score, 0, 1)
    
    def analyze_blink_patterns(self, landmarks: np.ndarray) -> Dict:
        """
        Analyze blink rates and patterns.
        Deepfakes often have unnatural blink patterns.
        """
        # Eye aspect ratio
        LEFT_EYE = [362, 385, 387, 263, 373, 380]
        RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        
        def eye_aspect_ratio(eye_points):
            A = np.linalg.norm(eye_points[1] - eye_points[5])
            B = np.linalg.norm(eye_points[2] - eye_points[4])
            C = np.linalg.norm(eye_points[0] - eye_points[3])
            return (A + B) / (2.0 * C) if C > 0 else 0
        
        left_eye = landmarks[LEFT_EYE]
        right_eye = landmarks[RIGHT_EYE]
        
        left_ear = eye_aspect_ratio(left_eye)
        right_ear = eye_aspect_ratio(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0
        
        self.blink_history.append(avg_ear)
        
        # Keep history limited
        if len(self.blink_history) > self.history_size:
            self.blink_history.pop(0)
        
        analysis = {
            "current_ear": float(avg_ear),
            "blink_rate": self._calculate_blink_rate(),
            "blink_pattern_anomaly": self._detect_blink_pattern_anomaly(),
            "blink_duration_anomaly": self._detect_blink_duration_anomaly()
        }
        
        return analysis
    
    def _calculate_blink_rate(self) -> float:
        """Calculate blinks per minute from history"""
        if len(self.blink_history) < 10:
            return 0.0
        
        # Detect blinks (transitions below threshold)
        EAR_THRESHOLD = 0.15
        blinks = 0
        was_closed = False
        
        for ear in self.blink_history:
            is_closed = ear < EAR_THRESHOLD
            if was_closed and not is_closed:
                blinks += 1
            was_closed = is_closed
        
        # Normalize to blinks per minute (assuming ~30 fps)
        blink_rate = (blinks / len(self.blink_history)) * 60 * 30 / 60
        
        return float(blink_rate)
    
    def _detect_blink_pattern_anomaly(self) -> float:
        """Detect unnatural blink patterns"""
        if len(self.blink_history) < 20:
            return 0.0
        
        # Deepfakes may have regular/periodic blink patterns
        # Calculate autocorrelation
        history_array = np.array(self.blink_history)
        
        if np.std(history_array) < 1e-6:
            return 1.0  # Completely flat pattern is suspicious
        
        correlation = signal.correlate(history_array, history_array, mode='full')
        correlation = correlation[len(correlation)//2:]
        correlation = correlation / correlation[0]
        
        # Check for periodicity (peaks at regular intervals)
        periodicity_score = np.max(correlation[10:min(50, len(correlation))])
        
        # High periodicity is anomalous
        return float(np.clip(periodicity_score - 0.5, 0, 1))
    
    def _detect_blink_duration_anomaly(self) -> float:
        """Detect unnatural blink durations"""
        if len(self.blink_history) < 10:
            return 0.0
        
        EAR_THRESHOLD = 0.15
        blink_durations = []
        in_blink = False
        duration = 0
        
        for ear in self.blink_history:
            is_closed = ear < EAR_THRESHOLD
            
            if is_closed:
                if not in_blink:
                    in_blink = True
                    duration = 1
                else:
                    duration += 1
            else:
                if in_blink:
                    blink_durations.append(duration)
                    in_blink = False
                    duration = 0
        
        if not blink_durations:
            return 0.0
        
        # Normal blink duration is 100-400ms (~3-12 frames at 30fps)
        durations = np.array(blink_durations)
        abnormal_count = np.sum((durations < 2) | (durations > 15))
        
        anomaly_score = abnormal_count / len(blink_durations) if blink_durations else 0.0
        
        return float(np.clip(anomaly_score, 0, 1))
    
    def analyze_face_geometry(self, landmarks: np.ndarray) -> Dict:
        """
        Analyze facial geometry for consistency and natural proportions
        """
        # Key facial measurements
        nose_tip = landmarks[1]
        chin = landmarks[152]
        left_eye = landmarks[33]
        right_eye = landmarks[263]
        left_mouth = landmarks[61]
        right_mouth = landmarks[291]
        
        # Distances
        face_height = np.linalg.norm(chin - nose_tip)
        face_width = np.linalg.norm(right_eye - left_eye)
        mouth_width = np.linalg.norm(right_mouth - left_mouth)
        
        # Ratios (should be relatively consistent)
        mouth_face_ratio = mouth_width / (face_height + 1e-6)
        width_height_ratio = face_width / (face_height + 1e-6)
        
        # Store history
        self.face_geometry_history.append({
            "face_height": face_height,
            "face_width": face_width,
            "mouth_width": mouth_width,
            "mouth_face_ratio": mouth_face_ratio,
            "width_height_ratio": width_height_ratio
        })
        
        if len(self.face_geometry_history) > self.history_size:
            self.face_geometry_history.pop(0)
        
        # Analyze consistency
        consistency_score = self._analyze_geometry_consistency()
        
        return {
            "face_height": float(face_height),
            "face_width": float(face_width),
            "mouth_face_ratio": float(mouth_face_ratio),
            "width_height_ratio": float(width_height_ratio),
            "geometry_consistency_score": consistency_score
        }
    
    def _analyze_geometry_consistency(self) -> float:
        """Analyze if facial geometry is consistent (low variance = suspicious)"""
        if len(self.face_geometry_history) < 5:
            return 0.0
        
        ratios = np.array([h["width_height_ratio"] for h in self.face_geometry_history])
        
        # Natural variation should have some variance
        consistency = np.std(ratios)
        
        # Consistency score: high variance is good, low variance is suspicious
        # Normal std ~ 0.05-0.1, suspicious < 0.02
        anomaly = max(0, 1.0 - (consistency / 0.1))
        
        return float(np.clip(anomaly, 0, 1))
    
    def analyze_temporal_consistency(self, frame: np.ndarray) -> Dict:
        """
        Analyze temporal consistency - e.g., flickering, unnatural transitions
        """
        self.frame_history.append(frame.copy())
        
        if len(self.frame_history) > self.history_size:
            self.frame_history.pop(0)
        
        if len(self.frame_history) < 3:
            return {"temporal_anomaly": 0.0, "frame_differences": []}
        
        # Calculate frame differences (optical flow approximation)
        frame_diffs = []
        
        for i in range(1, len(self.frame_history)):
            prev = cv2.cvtColor(self.frame_history[i-1], cv2.COLOR_BGR2GRAY)
            curr = cv2.cvtColor(self.frame_history[i], cv2.COLOR_BGR2GRAY)
            
            diff = cv2.absdiff(prev, curr)
            mean_diff = np.mean(diff)
            frame_diffs.append(mean_diff)
        
        # Detect unusual patterns
        frame_diffs_array = np.array(frame_diffs)
        
        # High variance in frame differences or sudden spikes indicate artifacts
        if len(frame_diffs_array) > 1:
            variance = np.var(frame_diffs_array)
            anomaly_score = np.clip(variance / 1000.0, 0, 1)
        else:
            anomaly_score = 0.0
        
        return {
            "temporal_anomaly": float(anomaly_score),
            "mean_frame_difference": float(np.mean(frame_diffs)) if frame_diffs else 0.0,
            "frame_difference_variance": float(np.var(frame_diffs_array)) if len(frame_diffs_array) > 0 else 0.0
        }
    
    def process_frame(self, frame: np.ndarray) -> Dict:
        """
        Process frame for deepfake indicators
        Returns comprehensive deepfake analysis
        """
        if frame is None or frame.size == 0:
            return {
                "face_detected": False,
                "deepfake_score": 0.0,
                "indicators": {}
            }
        
        try:
            # Detect face using robust cascade classifier with preprocessing
            faces = self.detect_faces_cascade(frame)
            face_detected = len(faces) > 0
            
            if not face_detected:
                return {
                    "face_detected": False,
                    "deepfake_score": 0.0,
                    "indicators": {}
                }
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Try MediaPipe first, fall back to OpenCV
            if self.use_mediapipe:
                try:
                    results = self.face_mesh.process(frame_rgb)
                    
                    if results.multi_face_landmarks:
                        landmarks = np.array([
                            [lm.x * frame.shape[1], lm.y * frame.shape[0], lm.z]
                            for lm in results.multi_face_landmarks[0].landmark
                        ])
                    else:
                        landmarks = None
                except Exception:
                    landmarks = None
            else:
                landmarks = None
            
            if landmarks is None:
                # Face detected but no landmarks - use basic texture analysis only
                texture_analysis = self.analyze_micro_textures(frame, None)
                
                # Without full facial landmarks, use conservative score
                deepfake_score = texture_analysis.get("anomaly_score", 0) * 0.5 + 0.2  # Add baseline
                
                analysis = {
                    "face_detected": True,
                    "deepfake_score": float(np.clip(deepfake_score, 0, 1)),
                    "is_likely_deepfake": deepfake_score > 0.6,
                    "indicators": {
                        "texture": texture_analysis,
                        "note": "Limited analysis - face detected but detailed landmarks unavailable"
                    }
                }
                
                return analysis
            
            # Get face bounding box
            x_coords = landmarks[:, 0]
            y_coords = landmarks[:, 1]
            
            x_min, x_max = int(np.min(x_coords)), int(np.max(x_coords))
            y_min, y_max = int(np.min(y_coords)), int(np.max(y_coords))
            
            # Add padding
            padding = int((x_max - x_min) * 0.2)
            x_min = max(0, x_min - padding)
            y_min = max(0, y_min - padding)
            x_max = min(frame.shape[1], x_max + padding)
            y_max = min(frame.shape[0], y_max + padding)
            
            face_region = (x_min, y_min, x_max - x_min, y_max - y_min)
            
            # Perform all analyses
            texture_analysis = self.analyze_micro_textures(frame, face_region)
            blink_analysis = self.analyze_blink_patterns(landmarks)
            geometry_analysis = self.analyze_face_geometry(landmarks)
            temporal_analysis = self.analyze_temporal_consistency(frame)
            
            # Calculate composite deepfake score
            deepfake_score = (
                texture_analysis.get("anomaly_score", 0) * 0.35 +
                blink_analysis.get("blink_pattern_anomaly", 0) * 0.25 +
                geometry_analysis.get("geometry_consistency_score", 0) * 0.2 +
                temporal_analysis.get("temporal_anomaly", 0) * 0.2
            )
            
            analysis = {
                "face_detected": True,
                "deepfake_score": float(np.clip(deepfake_score, 0, 1)),
                "is_likely_deepfake": deepfake_score > 0.5,
                "indicators": {
                    "texture": texture_analysis,
                    "blink": blink_analysis,
                    "geometry": geometry_analysis,
                    "temporal": temporal_analysis
                }
            }
            
            return analysis
        except Exception as e:
            return {
                "face_detected": False,
                "deepfake_score": 0.0,
                "indicators": {"error": str(e)}
            }
            
            # Perform all analyses
            texture_analysis = self.analyze_micro_textures(frame, face_region)
            blink_analysis = self.analyze_blink_patterns(landmarks)
            geometry_analysis = self.analyze_face_geometry(landmarks)
            temporal_analysis = self.analyze_temporal_consistency(frame)
            
            # Calculate composite deepfake score
            deepfake_score = (
                texture_analysis.get("anomaly_score", 0) * 0.35 +
                blink_analysis.get("blink_pattern_anomaly", 0) * 0.25 +
                geometry_analysis.get("geometry_consistency_score", 0) * 0.2 +
                temporal_analysis.get("temporal_anomaly", 0) * 0.2
            )
            
            analysis = {
                "face_detected": True,
                "deepfake_score": float(np.clip(deepfake_score, 0, 1)),
                "is_likely_deepfake": deepfake_score > 0.5,
                "indicators": {
                    "texture": texture_analysis,
                    "blink": blink_analysis,
                    "geometry": geometry_analysis,
                    "temporal": temporal_analysis
                }
            }
            
            return analysis
        except Exception as e:
            return {
                "face_detected": False,
                "deepfake_score": 0.0,
                "indicators": {"error": str(e)}
            }
    
    def reset(self):
        """Reset detector state"""
        self.frame_history = []
        self.blink_history = []
        self.face_geometry_history = []
        self.eye_gaze_history = []
