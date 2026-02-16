"""
Liveness Detection Service
Implements interactive liveness challenges requiring real-time user actions
such as head movement and facial gestures.
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time

"""
Liveness Detection Service
Implements interactive liveness challenges requiring real-time user actions
such as head movement and facial gestures.
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time

# Try to import MediaPipe, fallback to OpenCV if not available
try:
    import mediapipe as mp
    try:
        mp_face_mesh = mp.solutions.face_mesh
        mp_face_detection = mp.solutions.face_detection
        MEDIAPIPE_AVAILABLE = True
    except (AttributeError, ImportError):
        MEDIAPIPE_AVAILABLE = False
except ImportError:
    MEDIAPIPE_AVAILABLE = False

# Always load OpenCV cascade classifiers as fallback
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)
eye_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_eye.xml'
)


class ChallengeType(Enum):
    """Types of liveness challenges"""
    HEAD_TURN = "head_turn"
    BLINK = "blink"
    MOUTH_OPEN = "mouth_open"
    SMILE = "smile"
    NOD = "nod"


@dataclass
class LivenessResult:
    """Result of liveness challenge"""
    is_live: bool
    challenge_type: ChallengeType
    confidence: float
    details: Dict


class LivenessDetector:
    """
    Detects liveness through interactive challenges and facial action units.
    Works with low-resolution webcams and mobile cameras.
    Falls back to OpenCV if MediaPipe is unavailable.
    """
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
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
                self.face_detection = mp_face_detection.FaceDetection(
                    model_selection=1,
                    min_detection_confidence=0.5
                )
            except Exception:
                self.use_mediapipe = False
        
        # Challenge state tracking
        self.challenge_history = []
        self.prev_frame_landmarks = None
        self.blink_counter = 0
        self.eye_closed_frames = 0
        
    def detect_blink(self, landmarks: Optional[np.ndarray] = None) -> Tuple[bool, float]:
        """
        Detect eye blink using eye aspect ratio (EAR).
        Returns: (blink_detected, confidence)
        """
        if landmarks is None or len(landmarks) == 0:
            return False, 0.0
        
        # Eye landmarks indices (MediaPipe face mesh)
        LEFT_EYE = [362, 385, 387, 263, 373, 380]
        RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        
        try:
            # Ensure we have enough landmarks
            if len(landmarks) < 400:
                return False, 0.0
            
            def eye_aspect_ratio(eye_points):
                # Vertical distance between upper and lower eyelid
                A = np.linalg.norm(eye_points[1] - eye_points[5])
                B = np.linalg.norm(eye_points[2] - eye_points[4])
                # Horizontal distance between eye corners
                C = np.linalg.norm(eye_points[0] - eye_points[3])
                return (A + B) / (2.0 * C) if C > 0 else 0
            
            left_eye_points = landmarks[LEFT_EYE]
            right_eye_points = landmarks[RIGHT_EYE]
            
            left_ear = eye_aspect_ratio(left_eye_points)
            right_ear = eye_aspect_ratio(right_eye_points)
            
            avg_ear = (left_ear + right_ear) / 2.0
            
            # Blink threshold
            EAR_THRESHOLD = 0.15
            
            is_blink = avg_ear < EAR_THRESHOLD
            confidence = 1.0 - avg_ear if is_blink else 0.0
            
            return is_blink, min(confidence, 1.0)
        except:
            return False, 0.0
    
    def detect_head_movement(self, current_landmarks: Optional[np.ndarray] = None) -> Tuple[bool, float, Dict]:
        """
        Detect significant head movement by tracking facial landmarks position.
        Returns: (movement_detected, confidence, details)
        """
        if current_landmarks is None:
            return False, 0.0, {"reason": "no_landmarks"}
        
        if self.prev_frame_landmarks is None:
            self.prev_frame_landmarks = current_landmarks
            return False, 0.0, {"reason": "no_previous_frame"}
        
        try:
            # Calculate centroid displacement
            prev_centroid = np.mean(self.prev_frame_landmarks, axis=0)
            curr_centroid = np.mean(current_landmarks, axis=0)
            
            displacement = np.linalg.norm(curr_centroid - prev_centroid)
            
            # Movement threshold (adjust based on camera resolution)
            MOVEMENT_THRESHOLD = 15.0
            
            movement_detected = displacement > MOVEMENT_THRESHOLD
            confidence = min(displacement / MOVEMENT_THRESHOLD, 1.0) if movement_detected else 0.0
            
            self.prev_frame_landmarks = current_landmarks.copy()
            
            return movement_detected, confidence, {
                "displacement": displacement,
                "movement_types": ["head_movement"] if movement_detected else []
            }
        except:
            return False, 0.0, {"reason": "processing_error"}
    
    def detect_mouth_open(self, landmarks: Optional[np.ndarray] = None) -> Tuple[bool, float]:
        """
        Detect mouth open gesture.
        Returns: (mouth_open, confidence)
        """
        if landmarks is None or len(landmarks) < 400:
            return False, 0.0
        
        try:
            # Mouth landmarks indices
            MOUTH_TOP = 13
            MOUTH_BOTTOM = 14
            
            mouth_top = landmarks[MOUTH_TOP]
            mouth_bottom = landmarks[MOUTH_BOTTOM]
            
            mouth_distance = np.linalg.norm(mouth_bottom - mouth_top)
            
            # Mouth distance threshold
            MOUTH_THRESHOLD = 20.0
            
            mouth_open = mouth_distance > MOUTH_THRESHOLD
            confidence = min(mouth_distance / MOUTH_THRESHOLD, 1.0) if mouth_open else 0.0
            
            return mouth_open, min(confidence, 1.0)
        except:
            return False, 0.0
    
    def detect_motion_in_frame(self, frame: np.ndarray) -> float:
        """
        Detect motion by comparing frame intensity changes.
        Returns motion confidence score (0-1).
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if self.prev_frame_landmarks is None:
                self.prev_frame_landmarks = gray.copy()
                return 0.2  # Some default liveness when no prev frame
            
            # Calculate frame difference
            frame_diff = cv2.absdiff(gray, self.prev_frame_landmarks)
            motion_magnitude = np.median(frame_diff)
            
            # Normalize motion to 0-1 range
            motion_score = min(motion_magnitude / 50.0, 1.0)
            
            self.prev_frame_landmarks = gray.copy()
            return motion_score
        except:
            return 0.1

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
            
            # Remove duplicates - faces that overlap significantly
            if faces:
                faces = self._remove_duplicate_faces(faces)
            
            return faces
        except Exception:
            return []
    
    def _remove_duplicate_faces(self, faces: List[Tuple]) -> List[Tuple]:
        """Remove duplicate/overlapping face detections."""
        if len(faces) <= 1:
            return list(faces)
        
        # Keep only the largest faces (likely the most confident)
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        
        unique_faces = [faces[0]]
        for face in faces[1:]:
            x, y, w, h = face
            is_duplicate = False
            for ux, uy, uw, uh in unique_faces:
                # Calculate overlap
                overlap = (min(x+w, ux+uw) - max(x, ux)) * (min(y+h, uy+uh) - max(y, uy))
                if overlap > (w * h * 0.3):  # 30% overlap threshold
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_faces.append(face)
        
        return unique_faces[:1]  # Return only the top face

    def process_frame(self, frame: np.ndarray) -> Dict:
        """
        Process a single frame for liveness detection.
        Returns analysis results including detected actions.
        """
        if frame is None or frame.size == 0:
            return {
                "face_detected": False,
                "liveness_score": 0.0,
                "detections": {}
            }
        
        try:
            # Detect face using robust cascade classifier with preprocessing
            faces = self.detect_faces_cascade(frame)
            face_detected = len(faces) > 0
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            if self.use_mediapipe:
                try:
                    results = self.face_mesh.process(frame_rgb)
                    
                    if results.multi_face_landmarks:
                        landmarks = np.array([
                            [lm.x, lm.y, lm.z] for lm in results.multi_face_landmarks[0].landmark
                        ])
                    else:
                        landmarks = None
                except Exception:
                    landmarks = None
            else:
                landmarks = None
            
            # Perform liveness checks
            if landmarks is not None:
                blink_detected, blink_conf = self.detect_blink(landmarks)
                move_detected, move_conf, move_details = self.detect_head_movement(landmarks)
                mouth_open, mouth_conf = self.detect_mouth_open(landmarks)
            else:
                # Use fallback motion detection when MediaPipe landmarks unavailable
                blink_detected, blink_conf = False, 0.0
                move_detected, move_conf, move_details = False, self.detect_motion_in_frame(frame), {"reason": "motion_fallback"}
                mouth_open, mouth_conf = False, 0.0
            
            # Calculate overall liveness score
            liveness_score = (
                blink_conf * 0.3 +  # 30% weight on blinking
                move_conf * 0.4 +   # 40% weight on head movement
                mouth_conf * 0.3    # 30% weight on mouth movement
            )
            
            # If no landmarks but face detected, apply baseline liveness score
            if landmarks is None and face_detected:
                liveness_score = max(liveness_score, 0.5)
            
            return {
                "face_detected": face_detected,
                "liveness_score": float(liveness_score),
                "is_likely_live": liveness_score > self.confidence_threshold,
                "detections": {
                    "blink": {"detected": blink_detected, "confidence": float(blink_conf)},
                    "head_movement": {"detected": move_detected, "confidence": float(move_conf), "details": move_details},
                    "mouth_open": {"detected": mouth_open, "confidence": float(mouth_conf)}
                }
            }
        except Exception as e:
            return {
                "face_detected": False,
                "liveness_score": 0.0,
                "detections": {"error": str(e)}
            }
    
    def generate_challenge(self, challenge_type: ChallengeType) -> Dict:
        """Generate an interactive liveness challenge"""
        challenges = {
            ChallengeType.HEAD_TURN: {
                "instruction": "Please turn your head to the left and then to the right",
                "expected_actions": ["horizontal_turn"],
                "timeout": 8.0
            },
            ChallengeType.BLINK: {
                "instruction": "Please blink your eyes",
                "expected_actions": ["blink"],
                "timeout": 5.0
            },
            ChallengeType.MOUTH_OPEN: {
                "instruction": "Please open your mouth",
                "expected_actions": ["mouth_open"],
                "timeout": 5.0
            },
            ChallengeType.SMILE: {
                "instruction": "Please smile",
                "expected_actions": ["smile"],
                "timeout": 5.0
            },
            ChallengeType.NOD: {
                "instruction": "Please nod your head",
                "expected_actions": ["vertical_nod"],
                "timeout": 5.0
            }
        }
        
        return challenges.get(challenge_type, {})
    
    def calculate_liveness_confidence(self, detections: List[Dict]) -> float:
        """
        Calculate overall liveness confidence from multiple detections.
        """
        if not detections:
            return 0.0
        
        scores = [d["liveness_score"] for d in detections if d.get("face_detected")]
        
        if not scores:
            return 0.0
        
        # Use average with decay for older frames
        weighted_sum = sum(score * (0.9 ** i) for i, score in enumerate(reversed(scores)))
        weight_sum = sum(0.9 ** i for i in range(len(scores)))
        
        return weighted_sum / weight_sum if weight_sum > 0 else 0.0
    
    def reset(self):
        """Reset detector state"""
        self.prev_frame_landmarks = None
        self.challenge_history = []
        self.blink_counter = 0
        self.eye_closed_frames = 0
