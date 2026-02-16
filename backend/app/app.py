"""
Flask Backend API for KYC Verification
Handles video upload, processing, and verification results
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid
import base64
import cv2
import numpy as np
from typing import Dict, Tuple
import logging

from app.services.liveness_detection import LivenessDetector, ChallengeType
from app.services.deepfake_detection import DeepfakeDetector
from app.services.spoof_alerting import SpoofAlertingService, AlertType, AlertSeverity
from app.utils.video_processor import VideoProcessor
from app.utils.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.config['TEMP_FOLDER'] = Config.TEMP_FOLDER

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

# Initialize services
liveness_detector = LivenessDetector(confidence_threshold=0.7)
deepfake_detector = DeepfakeDetector(history_size=30)
spoof_alerter = SpoofAlertingService()

# Active sessions
active_sessions = {}


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "KYC Verification"}), 200


@app.route('/api/v1/kyc/start-session', methods=['POST'])
def start_verification_session():
    """Start a new KYC verification session"""
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        session_id = str(uuid.uuid4())
        
        active_sessions[session_id] = {
            "user_id": user_id,
            "session_id": session_id,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "video_frames": [],
            "analysis_results": {}
        }
        
        logger.info(f"Started verification session {session_id} for user {user_id}")
        
        return jsonify({
            "session_id": session_id,
            "user_id": user_id,
            "status": "active",
            "message": "KYC verification session started"
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting session: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/kyc/send-challenge', methods=['POST'])
def send_liveness_challenge():
    """Send an interactive liveness challenge"""
    try:
        data = request.json
        session_id = data.get('session_id')
        challenge_type = data.get('challenge_type', 'head_turn')
        
        if session_id not in active_sessions:
            return jsonify({"error": "Invalid session_id"}), 400
        
        # Get challenge
        try:
            challenge = ChallengeType[challenge_type.upper()]
        except KeyError:
            return jsonify({"error": f"Invalid challenge_type: {challenge_type}"}), 400
        
        challenge_details = liveness_detector.generate_challenge(challenge)
        
        active_sessions[session_id]["current_challenge"] = {
            "type": challenge_type,
            "instruction": challenge_details.get("instruction"),
            "timeout": challenge_details.get("timeout")
        }
        
        logger.info(f"Challenge {challenge_type} sent for session {session_id}")
        
        return jsonify({
            "session_id": session_id,
            "challenge_type": challenge_type,
            "instruction": challenge_details.get("instruction"),
            "timeout": challenge_details.get("timeout"),
            "message": "Liveness challenge sent"
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending challenge: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/kyc/upload-video-frame', methods=['POST'])
def upload_video_frame():
    """Upload a video frame for processing"""
    try:
        data = request.json
        session_id = data.get('session_id')
        frame_data = data.get('frame')  # Base64 encoded
        
        if session_id not in active_sessions:
            return jsonify({"error": "Invalid session_id"}), 400
        
        if not frame_data:
            return jsonify({"error": "frame data is required"}), 400
        
        # Decode frame
        frame_bytes = base64.b64decode(frame_data.split(',')[1] if ',' in frame_data else frame_data)
        frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({"error": "Failed to decode frame"}), 400
        
        # Store frame
        active_sessions[session_id]["video_frames"].append(frame)
        
        # Perform immediate analysis
        liveness_result = liveness_detector.process_frame(frame)
        deepfake_result = deepfake_detector.process_frame(frame)
        
        # Store analysis
        if "frame_analysis" not in active_sessions[session_id]:
            active_sessions[session_id]["frame_analysis"] = []
        
        active_sessions[session_id]["frame_analysis"].append({
            "liveness": liveness_result,
            "deepfake": deepfake_result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Check for alerts
        if not liveness_result.get("face_detected"):
            spoof_alerter.create_alert(
                alert_type=AlertType.FACE_NOT_DETECTED,
                session_id=session_id,
                severity=AlertSeverity.MEDIUM,
                message="Face not detected in frame",
                details={"frame_count": len(active_sessions[session_id]["video_frames"])},
                user_id=active_sessions[session_id]["user_id"]
            )
        
        return jsonify({
            "session_id": session_id,
            "frame_received": True,
            "liveness_score": liveness_result.get("liveness_score", 0),
            "deepfake_score": deepfake_result.get("deepfake_score", 0),
            "face_detected": liveness_result.get("face_detected", False)
        }), 200
        
    except Exception as e:
        logger.error(f"Error uploading frame: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/kyc/complete-verification', methods=['POST'])
def complete_verification():
    """Complete KYC verification and get results"""
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if session_id not in active_sessions:
            return jsonify({"error": "Invalid session_id"}), 400
        
        session = active_sessions[session_id]
        
        if not session.get("frame_analysis"):
            return jsonify({"error": "No frames analyzed"}), 400
        
        # Calculate aggregate scores
        liveness_scores = [f["liveness"]["liveness_score"] for f in session["frame_analysis"] if f["liveness"].get("face_detected")]
        deepfake_scores = [f["deepfake"]["deepfake_score"] for f in session["frame_analysis"] if f["deepfake"].get("face_detected")]
        
        avg_liveness = np.mean(liveness_scores) if liveness_scores else 0
        avg_deepfake = np.mean(deepfake_scores) if deepfake_scores else 0
        
        # Aggregate analysis
        deepfake_analysis = {
            "deepfake_score": float(avg_deepfake),
            "face_detected": len([f for f in session["frame_analysis"] if f["deepfake"].get("face_detected")]) > 0,
            "indicators": {}
        }
        
        liveness_analysis = {
            "liveness_score": float(avg_liveness),
            "face_detected": len([f for f in session["frame_analysis"] if f["liveness"].get("face_detected")]) > 0
        }
        
        # Get verification result
        verification_result = spoof_alerter.evaluate_verification_result(
            session_id=session_id,
            user_id=session["user_id"],
            deepfake_analysis=deepfake_analysis,
            liveness_analysis=liveness_analysis
        )
        
        # Update session status
        session["status"] = "completed"
        session["verification_result"] = verification_result
        
        logger.info(f"Verification completed for session {session_id}: {verification_result['status']}")
        
        return jsonify(verification_result), 200
        
    except Exception as e:
        logger.error(f"Error completing verification: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/kyc/get-session-status', methods=['GET'])
def get_session_status():
    """Get status of a verification session"""
    try:
        session_id = request.args.get('session_id')
        
        if not session_id or session_id not in active_sessions:
            return jsonify({"error": "Invalid session_id"}), 400
        
        session = active_sessions[session_id]
        
        return jsonify({
            "session_id": session_id,
            "user_id": session["user_id"],
            "status": session["status"],
            "frames_processed": len(session.get("frame_analysis", [])),
            "created_at": session["created_at"]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/alerts/active', methods=['GET'])
def get_active_alerts():
    """Get active alerts (for operations team dashboard)"""
    try:
        alerts = spoof_alerter.get_active_alerts()
        
        return jsonify({
            "active_alerts": alerts,
            "count": len(alerts)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/alerts/statistics', methods=['GET'])
def get_alert_statistics():
    """Get alert statistics"""
    try:
        stats = spoof_alerter.get_alert_statistics()
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting alert statistics: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/alerts/<alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    try:
        data = request.json
        acknowledged_by = data.get('acknowledged_by', 'unknown')
        
        success = spoof_alerter.acknowledge_alert(alert_id, acknowledged_by)
        
        if success:
            return jsonify({"message": "Alert acknowledged"}), 200
        else:
            return jsonify({"error": "Alert not found"}), 404
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large"}), 413


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    from datetime import datetime
    app.run(debug=False, host='0.0.0.0', port=5000)
