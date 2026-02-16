/**
 * KYC Video Verification System - Frontend
 * Handles video capture, liveness challenges, and real-time analysis
 */

class KYCVerificationSystem {
    constructor() {
        // Configuration
        this.apiBaseUrl = 'http://localhost:5000/api/v1';
        this.sessionId = null;
        this.userId = 'user_' + Date.now();
        
        // Video settings
        this.videoStream = null;
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.captureInterval = null;
        this.frameCount = 0;
        
        // State
        this.state = 'idle'; // idle, initializing, recording, completed
        this.currentChallenge = null;
        this.challenges = ['head_turn', 'blink', 'mouth_open', 'smile', 'nod'];
        this.completedChallenges = [];
        
        // Elements
        this.elements = {
            webcam: document.getElementById('webcam'),
            overlay: document.getElementById('overlay'),
            canvas: document.getElementById('overlay'),
            loadingSpinner: document.getElementById('loadingSpinner'),
            sessionInfo: document.getElementById('sessionInfo'),
            sessionId: document.getElementById('sessionId'),
            sessionStatus: document.getElementById('sessionStatus'),
            challengeBox: document.getElementById('challengeBox'),
            challengeTitle: document.getElementById('challengeTitle'),
            challengeInstruction: document.getElementById('challengeInstruction'),
            analysisResults: document.getElementById('analysisResults'),
            faceStatus: document.getElementById('faceStatus'),
            faceDetectionText: document.getElementById('faceDetectionText'),
            messages: document.getElementById('messages'),
            startBtn: document.getElementById('startBtn'),
            nextChallengeBtn: document.getElementById('nextChallengeBtn'),
            submitBtn: document.getElementById('submitBtn'),
            cancelBtn: document.getElementById('cancelBtn'),
            resultScreen: document.getElementById('resultScreen'),
            resultCard: document.getElementById('resultCard'),
            resultContent: document.getElementById('resultContent'),
            newVerificationBtn: document.getElementById('newVerificationBtn')
        };
        
        // Initialize
        this.initializeEventListeners();
        this.initializeCamera();
    }
    
    initializeEventListeners() {
        this.elements.startBtn.addEventListener('click', () => this.startVerification());
        this.elements.nextChallengeBtn.addEventListener('click', () => this.performNextChallenge());
        this.elements.submitBtn.addEventListener('click', () => this.completeVerification());
        this.elements.cancelBtn.addEventListener('click', () => this.cancel());
        this.elements.newVerificationBtn.addEventListener('click', () => this.reset());
    }
    
    async initializeCamera() {
        try {
            const constraints = {
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                },
                audio: false
            };
            
            this.videoStream = await navigator.mediaDevices.getUserMedia(constraints);
            this.elements.webcam.srcObject = this.videoStream;
            
            // Wait for video to load
            this.elements.webcam.onloadedmetadata = () => {
                this.elements.loadingSpinner.classList.add('hidden');
                this.showMessage('Camera initialized. Ready for verification.', 'success');
            };
            
            // Setup recording
            this.setupRecording();
            
        } catch (error) {
            this.showMessage('Camera access denied: ' + error.message, 'error');
            console.error('Camera error:', error);
        }
    }
    
    setupRecording() {
        try {
            const options = { mimeType: 'video/webm;codecs=vp9' };
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options.mimeType = 'video/webm';
            }
            
            this.mediaRecorder = new MediaRecorder(this.videoStream, options);
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.onRecordingComplete();
            };
            
        } catch (error) {
            console.error('Recording setup error:', error);
            this.showMessage('Recording setup failed', 'error');
        }
    }
    
    async startVerification() {
        try {
            this.elements.startBtn.disabled = true;
            this.showMessage('Starting verification...', 'info');
            
            // Start session
            const response = await fetch(`${this.apiBaseUrl}/kyc/start-session`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.userId })
            });
            
            const data = await response.json();
            this.sessionId = data.session_id;
            
            this.elements.sessionId.textContent = this.sessionId.substring(0, 8) + '...';
            this.elements.sessionStatus.textContent = 'Active';
            
            // Start recording
            this.recordedChunks = [];
            this.mediaRecorder.start();
            this.state = 'recording';
            
            // Start capturing frames
            this.captureInterval = setInterval(() => this.captureFrame(), 100);
            
            // Start first challenge
            this.performNextChallenge();
            
            this.showMessage('Verification started. Follow the on-screen instructions.', 'success');
            
        } catch (error) {
            this.showMessage('Error starting verification: ' + error.message, 'error');
            this.elements.startBtn.disabled = false;
        }
    }
    
    async performNextChallenge() {
        try {
            this.elements.nextChallengeBtn.classList.add('hidden');
            
            if (this.completedChallenges.length >= this.challenges.length) {
                this.elements.submitBtn.classList.remove('hidden');
                this.elements.challengeBox.classList.add('hidden');
                this.showMessage('All challenges completed. Ready to submit.', 'info');
                return;
            }
            
            this.currentChallenge = this.challenges[this.completedChallenges.length];
            
            // Request challenge
            const response = await fetch(`${this.apiBaseUrl}/kyc/send-challenge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    challenge_type: this.currentChallenge
                })
            });
            
            const data = await response.json();
            
            // Display challenge
            this.elements.challengeBox.classList.remove('hidden');
            this.elements.challengeTitle.textContent = this.formatChallengeTitle(this.currentChallenge);
            this.elements.challengeInstruction.textContent = data.instruction;
            
            // Start timer
            this.startChallengeTimer(data.timeout);
            
            this.showMessage(`Challenge: ${data.instruction}`, 'info');
            
        } catch (error) {
            this.showMessage('Error performing challenge: ' + error.message, 'error');
        }
    }
    
    formatChallengeTitle(challenge) {
        const titles = {
            'head_turn': 'Turn Your Head',
            'blink': 'Blink Your Eyes',
            'mouth_open': 'Open Your Mouth',
            'smile': 'Smile',
            'nod': 'Nod Your Head'
        };
        return titles[challenge] || challenge;
    }
    
    startChallengeTimer(duration) {
        const timerBar = document.getElementById('timerBar');
        const timerText = document.getElementById('timerText');
        let elapsed = 0;
        
        const timerInterval = setInterval(() => {
            elapsed++;
            const remaining = Math.max(0, duration - elapsed);
            const progress = (elapsed / duration) * 100;
            
            timerBar.style.width = Math.min(progress, 100) + '%';
            timerText.textContent = Math.ceil(remaining) + 's';
            
            if (remaining <= 0) {
                clearInterval(timerInterval);
                this.completeChallenge();
            }
        }, 1000);
    }
    
    completeChallenge() {
        this.completedChallenges.push(this.currentChallenge);
        this.elements.nextChallengeBtn.classList.remove('hidden');
        this.showMessage('Challenge recorded. Click Next to continue.', 'success');
    }
    
    async captureFrame() {
        try {
            const canvas = document.createElement('canvas');
            canvas.width = this.elements.webcam.videoWidth;
            canvas.height = this.elements.webcam.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(this.elements.webcam, 0, 0);
            
            // Convert to base64
            const frameData = canvas.toDataURL('image/jpeg', 0.7);
            
            // Send to backend
            await fetch(`${this.apiBaseUrl}/kyc/upload-video-frame`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    frame: frameData
                })
            }).then(response => response.json())
              .then(data => {
                  this.updateAnalysisDisplay(data);
              });
            
            this.frameCount++;
            
        } catch (error) {
            console.error('Frame capture error:', error);
        }
    }
    
    updateAnalysisDisplay(data) {
        // Update face detection status
        if (data.face_detected) {
            this.elements.faceDetectionText.textContent = '✓ Face detected';
            this.elements.faceDetectionText.style.color = '#43a047';
        } else {
            this.elements.faceDetectionText.textContent = '✗ No face detected';
            this.elements.faceDetectionText.style.color = '#e53935';
        }
        
        // Update analysis results
        this.elements.analysisResults.classList.remove('hidden');
        
        // Liveness score
        const livenessPercent = Math.round((data.liveness_score || 0) * 100);
        document.getElementById('livenessScore').textContent = livenessPercent + '%';
        document.getElementById('livenessBar').style.width = livenessPercent + '%';
        
        // Deepfake score
        const deepfakePercent = Math.round((data.deepfake_score || 0) * 100);
        document.getElementById('deepfakeScore').textContent = deepfakePercent + '%';
        document.getElementById('deepfakeBar').style.width = deepfakePercent + '%';
    }
    
    async completeVerification() {
        try {
            this.elements.submitBtn.disabled = true;
            this.showMessage('Processing verification...', 'info');
            
            // Stop recording
            clearInterval(this.captureInterval);
            this.mediaRecorder.stop();
            
            // Get verification result
            const response = await fetch(`${this.apiBaseUrl}/kyc/complete-verification`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: this.sessionId })
            });
            
            const result = await response.json();
            
            // Stop video stream
            this.videoStream.getTracks().forEach(track => track.stop());
            
            // Display result
            this.displayResult(result);
            
        } catch (error) {
            this.showMessage('Error completing verification: ' + error.message, 'error');
        }
    }
    
    displayResult(result) {
        this.elements.webcam.style.display = 'none';
        this.elements.challengeBox.classList.add('hidden');
        this.elements.analysisResults.classList.add('hidden');
        this.elements.controls = document.querySelector('.controls');
        this.elements.controls.style.display = 'none';
        
        this.elements.resultScreen.classList.remove('hidden');
        
        const status = result.status;
        const isApproved = status === 'PASSED';
        
        document.getElementById('resultTitle').textContent = 
            isApproved ? '✓ Verification Approved' : '✗ Verification Failed';
        
        document.getElementById('resultCard').className = 
            isApproved ? 'result-card approved' : 'result-card rejected';
        
        let contentHtml = `
            <div class="result-details">
                <h3>${isApproved ? 'Identity Verified' : 'Verification Not Completed'}</h3>
                <p>${result.recommendations ? result.recommendations[0] : 'Verification process complete'}</p>
        `;
        
        if (result.alerts && result.alerts.length > 0) {
            contentHtml += '<div class="alerts"><h4>Alerts:</h4><ul>';
            result.alerts.forEach(alert => {
                contentHtml += `<li>${alert.message}</li>`;
            });
            contentHtml += '</ul></div>';
        }
        
        contentHtml += '</div>';
        
        document.getElementById('resultContent').innerHTML = contentHtml;
    }
    
    showMessage(message, type = 'info') {
        const messagesDiv = this.elements.messages;
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.textContent = message;
        
        messagesDiv.appendChild(messageEl);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            messageEl.remove();
        }, 5000);
    }
    
    cancel() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
            clearInterval(this.captureInterval);
        }
        
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
        }
        
        this.showMessage('Verification cancelled', 'info');
        this.reset();
    }
    
    reset() {
        this.state = 'idle';
        this.sessionId = null;
        this.completedChallenges = [];
        this.frameCount = 0;
        this.recordedChunks = [];
        
        // Hide result screen
        this.elements.resultScreen.classList.add('hidden');
        this.elements.webcam.style.display = 'block';
        document.querySelector('.controls').style.display = 'flex';
        
        // Reset buttons
        this.elements.startBtn.disabled = false;
        this.elements.nextChallengeBtn.classList.add('hidden');
        this.elements.submitBtn.classList.add('hidden');
        this.elements.submitBtn.disabled = false;
        
        this.elements.challengeBox.classList.add('hidden');
        this.elements.analysisResults.classList.add('hidden');
        
        this.elements.sessionId.textContent = 'None';
        this.elements.sessionStatus.textContent = 'Idle';
        
        // Reinitialize camera
        this.initializeCamera();
    }
    
    onRecordingComplete() {
        console.log('Recording completed');
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    new KYCVerificationSystem();
});
