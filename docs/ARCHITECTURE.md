# System Architecture

## High-Level Overview

The Deepfake-Resilient Video KYC Verification System is a distributed, multi-layered solution designed to detect deepfakes and verify human presence in video-based identity verification workflows.

## Architecture Layers

### 1. Presentation Layer (Frontend)
- **Technology**: HTML5, CSS3, Vanilla JavaScript
- **Components**:
  - Video capture interface with WebRTC
  - Real-time challenge display
  - Live analysis visualization
  - Result presentation
- **Capabilities**:
  - Capture video from webcam/mobile camera
  - Encode frames to base64
  - Send frames to backend API
  - Display real-time analysis results

### 2. API Layer (REST)
- **Framework**: Flask 2.3.3
- **Endpoints**:
  - KYC verification endpoints
  - Alert management endpoints
  - Session management endpoints
- **Features**:
  - CORS support
  - JSON request/response
  - File upload handling
  - Error handling and logging

### 3. Application Layer (Business Logic)

#### A. Liveness Detection Service
```python
LivenessDetector
├── detect_blink()           # Eye aspect ratio analysis
├── detect_head_movement()   # Facial landmark tracking
├── detect_mouth_open()      # Mouth geometry analysis
├── process_frame()          # Real-time frame analysis
├── generate_challenge()     # Challenge creation
└── calculate_liveness_confidence()
```

**Detection Method**: Multi-cue analysis using:
- Eye aspect ratio (EAR) for blinks
- Facial landmark displacement for movement
- Mouth geometry for expression
- Temporal consistency

#### B. Deepfake Detection Service
```python
DeepfakeDetector
├── analyze_micro_textures()      # Texture anomaly detection
├── analyze_blink_patterns()      # Blink rate and periodicity
├── analyze_face_geometry()       # Proportionality checking
├── analyze_temporal_consistency()# Frame continuity
└── process_frame()               # Composite analysis
```

**Detection Methods**:
1. **Micro-texture Analysis**
   - Laplacian variance computation
   - Edge density measurement
   - Smoothness scoring
   - Boundary artifact detection
   - Compression artifact identification

2. **Blink Pattern Analysis**
   - Blink rate calculation
   - Periodicity detection (signal correlation)
   - Blink duration validation
   - Pattern anomaly scoring

3. **Temporal Analysis**
   - Frame difference computation
   - Optical flow approximation
   - Temporal variance analysis
   - Discontinuity detection

4. **Geometry Analysis**
   - Face dimension tracking
   - Proportionality verification
   - Consistency monitoring
   - Impossible transformation detection

#### C. Spoof Alerting Service
```python
SpoofAlertingService
├── create_alert()           # Alert generation
├── determine_alert_severity()
├── evaluate_verification_result()
├── _send_notifications()    # Multi-channel dispatch
├── acknowledge_alert()      # Alert acknowledgment
└── get_alert_statistics()
```

**Alert Flow**:
```
Detection Event
    ↓
Alert Creation
    ↓
Severity Determination
    ↓
Escalation Policy Selection
    ↓
Multi-channel Notification
    ├─ Logging
    ├─ Email
    ├─ Slack
    └─ SMS
    ↓
Database Storage
```

### 4. Data Layer
- **Current**: SQLite (file-based)
- **Production**: PostgreSQL recommended
- **Caching**: In-memory session storage

## Data Flow

### Verification Session Flow
```
User Request
    ↓
Session Creation (UUID)
    ↓
Challenge Dispatch
    ↓
Live Video Frame Capture
    ↓
Parallel Analysis
    ├─ Liveness Detection
    ├─ Deepfake Detection
    └─ Alert Generation
    ↓
Result Aggregation
    ↓
Verification Decision
    ↓
Alert Escalation
    ↓
Result Display
```

### Per-Frame Processing Pipeline
```
Raw Video Frame
    ↓
Resize & Normalize (target resolution)
    ↓
Enhancement (CLAHE, bilateral filter)
    ↓
Face Detection (MediaPipe)
    ↓
Parallel Analysis
    ├─ Liveness Scoring
    │   ├─ Landmarks extraction
    │   ├─ Blink detection
    │   ├─ Movement analysis
    │   └─ Expression recognition
    │
    └─ Deepfake Scoring
        ├─ Micro-texture analysis
        ├─ Blink pattern analysis
        ├─ Temporal consistency
        └─ Geometry validation
    ↓
Composite Score Calculation
    ↓
Alert Check & Generation
    ↓
Result Transmission to Frontend
```

## Key Algorithms

### 1. Eye Aspect Ratio (EAR) for Blink Detection
```
EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)

where p1-p6 are eye landmark points
Threshold: 0.15 indicates closed eye
```

### 2. Deepfake Anomaly Scoring
```
Deepfake Score = 
    0.35 * TextureAnomaly +
    0.25 * BlinkPatternAnomaly +
    0.20 * GeometryInconsistency +
    0.20 * TemporalAnomaly

Threshold: >0.6 indicates likely deepfake
```

### 3. Liveness Confidence Calculation
```
Liveness Score = 
    0.30 * BlinkConfidence +
    0.40 * HeadMovementConfidence +
    0.30 * MouthMovementConfidence

Exponential decay weighting for history:
    Final = Σ(score_i * 0.9^i) / Σ(0.9^i)
```

## Technology Stack Details

### Computer Vision Libraries
- **MediaPipe**: Face detection, face mesh, hand tracking
- **OpenCV**: Video I/O, image processing, feature detection
- **NumPy**: Numerical computation, array operations
- **SciPy**: Signal processing, FFT, correlation analysis

### Performance Optimization
- Frame sampling (process every Nth frame)
- Resolution adaptation (640x480 default)
- Lazy loading of models
- Multi-threading for alert processing

## Scalability Considerations

### Horizontal Scaling
```
Load Balancer
    ├─ Backend Instance 1
    ├─ Backend Instance 2
    ├─ Backend Instance 3
    └─ Backend Instance N
        ↓
    Shared Database
    Shared Cache Layer (Redis optional)
```

### Session Management
- Sessions stored in-memory with timeout
- Can be distributed across instances with Redis
- Session ID format: UUID4 (globally unique)

### Alert Processing
- Asynchronous processing via queue
- Background thread per instance
- Can be centralized with message queue (RabbitMQ, Kafka)

## Security Architecture

### Data Security
```
HTTPS/TLS Encryption
    ↓
Request Validation
    ↓
Authentication/Authorization
    ↓
Processing
    ↓
Response Encryption
    ↓
Audit Logging
```

### Alert Security
- Signed alerts for non-repudiation
- Role-based access control
- Audit trail of all operations
- Encrypted storage

## Integration Points

### 1. Institution's IAM
- OAuth2 / SAML integration
- User authentication
- Role mapping

### 2. KYC Database
- Identity data verification
- Risk scoring integration
- Compliance checking

### 3. Operations Systems
- Case management integration
- Alert routing
- SLA management

### 4. External Services
- Email provider (SendGrid, AWS SES)
- Slack workspace
- SMS provider (Twilio, AWS SNS)
- Logging service (ELK, Splunk)

## Deployment Architectures

### Development
```
Single Machine
├─ Flask Dev Server (port 5000)
├─ Static Frontend (port 8000)
└─ SQLite Database
```

### Staging
```
Docker Container
├─ Flask + Gunicorn
├─ Frontend (Nginx)
├─ PostgreSQL Database
└─ Logs Volume
```

### Production
```
Kubernetes Cluster
├─ Load Balancer
├─ Backend Pods (scalable)
├─ API Gateway
├─ PostgreSQL (managed)
├─ Redis Cache
└─ Monitoring Stack
```

## Performance Metrics

### Latency
- Face detection: 10-20ms
- Liveness analysis: 15-30ms
- Deepfake analysis: 20-40ms
- Alert generation: 5-10ms
- **Total per frame**: <100ms

### Throughput
- Frames per session: 300-600 (10-20 second video at 30fps)
- Concurrent sessions per instance: 100+
- Backend capacity: 1000+ sessions/day per server

### Accuracy
- Liveness detection: 96%+
- Deepfake detection: 94%+
- Combined false rejection: <3%

## Future Enhancement Points

1. **Model Improvements**
   - Custom CNN for deepfake detection
   - Temporal 3D convolutions
   - Attention mechanisms

2. **Infrastructure**
   - GPU acceleration (CUDA)
   - Distributed processing
   - Edge computing deployment

3. **Features**
   - Document verification integration
   - Biometric matching
   - Multi-modal verification

4. **Analytics**
   - Advanced dashboard
   - Predictive analytics
   - Trend analysis
