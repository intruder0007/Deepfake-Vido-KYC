"""
Video Processing Utilities
Handles video preprocessing, frame extraction, and optimization
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    Processes video for KYC verification
    Optimizes for low-resolution inputs while maintaining accuracy
    """
    
    def __init__(self,
                 target_fps: int = 30,
                 target_resolution: Tuple[int, int] = (640, 480)):
        self.target_fps = target_fps
        self.target_resolution = target_resolution
    
    def extract_frames(self, video_path: str, sample_rate: int = 1) -> List[np.ndarray]:
        """
        Extract frames from video file
        sample_rate: Extract every nth frame (reduce file size)
        """
        frames = []
        
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                logger.error(f"Failed to open video: {video_path}")
                return frames
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                if frame_count % sample_rate == 0:
                    # Resize if needed
                    frame = self.resize_frame(frame)
                    frames.append(frame)
                
                frame_count += 1
            
            cap.release()
            logger.info(f"Extracted {len(frames)} frames from {video_path}")
            
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
        
        return frames
    
    def resize_frame(self, frame: np.ndarray, 
                     target_resolution: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """
        Resize frame to target resolution while maintaining aspect ratio
        """
        if target_resolution is None:
            target_resolution = self.target_resolution
        
        h, w = frame.shape[:2]
        target_w, target_h = target_resolution
        
        # Calculate aspect ratio
        aspect_ratio = w / h
        target_aspect = target_w / target_h
        
        if aspect_ratio > target_aspect:
            # Frame is wider - fit to width
            new_w = target_w
            new_h = int(target_w / aspect_ratio)
        else:
            # Frame is taller - fit to height
            new_h = target_h
            new_w = int(target_h * aspect_ratio)
        
        # Resize
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Pad to target resolution
        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        y_offset = (target_h - new_h) // 2
        x_offset = (target_w - new_w) // 2
        
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        return canvas
    
    def enhance_low_resolution_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Enhance low-resolution frames for better feature detection
        """
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # Apply bilateral filter to reduce noise while preserving edges
        enhanced = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        return enhanced
    
    def get_video_metadata(self, video_path: str) -> dict:
        """Get video metadata"""
        metadata = {
            "fps": 0,
            "frame_count": 0,
            "resolution": (0, 0),
            "duration": 0.0
        }
        
        try:
            cap = cv2.VideoCapture(video_path)
            
            if cap.isOpened():
                metadata["fps"] = cap.get(cv2.CAP_PROP_FPS)
                metadata["frame_count"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                metadata["resolution"] = (
                    int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                )
                
                if metadata["fps"] > 0:
                    metadata["duration"] = metadata["frame_count"] / metadata["fps"]
                
                cap.release()
        
        except Exception as e:
            logger.error(f"Error getting metadata: {str(e)}")
        
        return metadata
    
    def validate_video(self, video_path: str) -> Tuple[bool, str]:
        """Validate if video is suitable for KYC verification"""
        try:
            metadata = self.get_video_metadata(video_path)
            
            # Minimum duration: 3 seconds
            if metadata["duration"] < 3:
                return False, "Video too short (minimum 3 seconds)"
            
            # Maximum duration: 60 seconds
            if metadata["duration"] > 60:
                return False, "Video too long (maximum 60 seconds)"
            
            # Minimum frames
            if metadata["frame_count"] < 30:
                return False, "Insufficient frames"
            
            # Minimum resolution
            if metadata["resolution"][0] < 320 or metadata["resolution"][1] < 240:
                return False, "Video resolution too low"
            
            # Minimum FPS
            if metadata["fps"] < 15:
                return False, "Video frame rate too low"
            
            return True, "Video validation passed"
        
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def create_video_from_frames(self, frames: List[np.ndarray], 
                                output_path: str,
                                fps: int = 30) -> bool:
        """Create video file from frames"""
        try:
            if not frames:
                logger.error("No frames provided")
                return False
            
            h, w = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
            
            for frame in frames:
                out.write(frame)
            
            out.release()
            logger.info(f"Video created: {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error creating video: {str(e)}")
            return False
