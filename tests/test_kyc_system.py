"""
Test Suite for KYC Verification System
"""
import unittest
import json
from datetime import datetime
from app.services.liveness_detection import LivenessDetector, ChallengeType
from app.services.deepfake_detection import DeepfakeDetector
from app.services.spoof_alerting import SpoofAlertingService, AlertType, AlertSeverity


class TestLivenessDetection(unittest.TestCase):
    """Test liveness detection functionality"""
    
    def setUp(self):
        self.detector = LivenessDetector()
    
    def test_initialization(self):
        """Test detector initialization"""
        self.assertIsNotNone(self.detector)
        self.assertEqual(self.detector.confidence_threshold, 0.7)
    
    def test_challenge_generation(self):
        """Test challenge generation"""
        for challenge_type in ChallengeType:
            challenge = self.detector.generate_challenge(challenge_type)
            self.assertIn('instruction', challenge)
            self.assertIn('timeout', challenge)
            self.assertIn('expected_actions', challenge)
    
    def test_detector_reset(self):
        """Test detector reset functionality"""
        self.detector.prev_frame_landmarks = [1, 2, 3]
        self.detector.reset()
        self.assertIsNone(self.detector.prev_frame_landmarks)
        self.assertEqual(self.detector.challenge_history, [])


class TestDeepfakeDetection(unittest.TestCase):
    """Test deepfake detection functionality"""
    
    def setUp(self):
        self.detector = DeepfakeDetector()
    
    def test_initialization(self):
        """Test detector initialization"""
        self.assertIsNotNone(self.detector)
        self.assertEqual(self.detector.history_size, 30)
    
    def test_detector_reset(self):
        """Test detector reset"""
        self.detector.frame_history = [1, 2, 3]
        self.detector.reset()
        self.assertEqual(self.detector.frame_history, [])
        self.assertEqual(self.detector.blink_history, [])


class TestSpoofAlerting(unittest.TestCase):
    """Test spoof alerting functionality"""
    
    def setUp(self):
        self.alerter = SpoofAlertingService()
    
    def test_alert_creation(self):
        """Test alert creation"""
        alert = self.alerter.create_alert(
            alert_type=AlertType.DEEPFAKE_DETECTED,
            session_id='test-session-123',
            severity=AlertSeverity.HIGH,
            message='Test deepfake alert',
            details={'test': 'data'},
            user_id='user-123'
        )
        
        self.assertEqual(alert.alert_type, AlertType.DEEPFAKE_DETECTED)
        self.assertEqual(alert.severity, AlertSeverity.HIGH)
        self.assertEqual(alert.status, 'active')
    
    def test_alert_severity_determination(self):
        """Test alert severity determination"""
        severity = self.alerter.determine_alert_severity(
            deepfake_score=0.85,
            liveness_score=0.1,
            indicators={}
        )
        self.assertEqual(severity, AlertSeverity.CRITICAL)
        
        severity = self.alerter.determine_alert_severity(
            deepfake_score=0.4,
            liveness_score=0.8,
            indicators={}
        )
        self.assertEqual(severity, AlertSeverity.LOW)
    
    def test_alert_acknowledgment(self):
        """Test alert acknowledgment"""
        alert = self.alerter.create_alert(
            alert_type=AlertType.FACE_NOT_DETECTED,
            session_id='test-session',
            severity=AlertSeverity.MEDIUM,
            message='Test alert',
            details={}
        )
        
        success = self.alerter.acknowledge_alert(alert.alert_id, 'operator-1')
        self.assertTrue(success)
        
        # Verify acknowledgment
        updated_alert = next(a for a in self.alerter.alerts if a.alert_id == alert.alert_id)
        self.assertEqual(updated_alert.status, 'acknowledged')
        self.assertEqual(updated_alert.acknowledged_by, 'operator-1')
    
    def test_get_active_alerts(self):
        """Test getting active alerts"""
        initial_count = len(self.alerter.get_active_alerts())
        
        self.alerter.create_alert(
            alert_type=AlertType.DEEPFAKE_DETECTED,
            session_id='test-1',
            severity=AlertSeverity.HIGH,
            message='Deepfake detected',
            details={}
        )
        
        active_alerts = self.alerter.get_active_alerts()
        self.assertEqual(len(active_alerts), initial_count + 1)
    
    def test_alert_statistics(self):
        """Test alert statistics"""
        stats = self.alerter.get_alert_statistics()
        
        self.assertIn('total_alerts', stats)
        self.assertIn('active_alerts', stats)
        self.assertIn('by_severity', stats)
        self.assertIn('by_type', stats)


class TestVerificationFlow(unittest.TestCase):
    """Test end-to-end verification flow"""
    
    def setUp(self):
        self.liveness_detector = LivenessDetector()
        self.deepfake_detector = DeepfakeDetector()
        self.alerter = SpoofAlertingService()
    
    def test_verification_result_evaluation(self):
        """Test verification result evaluation"""
        deepfake_analysis = {
            'deepfake_score': 0.85,
            'face_detected': True,
            'indicators': {}
        }
        
        liveness_analysis = {
            'liveness_score': 0.1,
            'face_detected': True
        }
        
        result = self.alerter.evaluate_verification_result(
            session_id='test-session',
            user_id='user-123',
            deepfake_analysis=deepfake_analysis,
            liveness_analysis=liveness_analysis
        )
        
        self.assertFalse(result['verified'])
        self.assertEqual(result['status'], 'FAILED')
        self.assertGreater(len(result['alerts']), 0)
    
    def test_successful_verification(self):
        """Test successful verification"""
        deepfake_analysis = {
            'deepfake_score': 0.2,
            'face_detected': True,
            'indicators': {}
        }
        
        liveness_analysis = {
            'liveness_score': 0.9,
            'face_detected': True
        }
        
        result = self.alerter.evaluate_verification_result(
            session_id='test-session',
            user_id='user-123',
            deepfake_analysis=deepfake_analysis,
            liveness_analysis=liveness_analysis
        )
        
        self.assertTrue(result['verified'])
        self.assertEqual(result['status'], 'PASSED')


if __name__ == '__main__':
    unittest.main()
