# Quick Start Guide

## Start in 5 Minutes

### 1. Prerequisites Check
- Python 3.8+ installed: `python --version`
- Modern web browser with camera access
- ~500MB disk space

### 2. Installation (2 minutes)

```bash
# Navigate to project
cd "Deepfake Video KYC"

# Create virtual environment
python -m venv venv

# Activate environment
venv\Scripts\activate  # Windows
# OR
source venv/bin/activate  # MacOS/Linux

# Install dependencies
pip install -r backend/requirements.txt

# Verify (should run without errors)
python -c "import cv2, mediapipe; print('✓ Ready')"
```

### 3. Start Backend (1 minute)

```bash
# Run Flask backend
python main.py

# You should see:
# * Serving Flask app
# * Running on http://0.0.0.0:5000
```

### 4. Start Frontend (1 minute)

In a NEW terminal:

```bash
# Navigate to frontend
cd frontend/public

# Start simple HTTP server
python -m http.server 8000

# You should see:
# Serving HTTP on 0.0.0.0 port 8000
```

### 5. Access Application (1 minute)

Open your browser to: **http://localhost:8000**

## First Test Run

1. **Click "Start Verification"**
   - Browser will request camera access → Click "Allow"
   - You'll see your video feed

2. **Follow Challenges**
   - "Turn Your Head" - Move head left and right
   - "Blink Your Eyes" - Blink normally
   - "Open Your Mouth" - Open mouth
   - "Smile" - Smile
   - "Nod Your Head" - Nod

3. **Watch Analysis**
   - See liveness and deepfake scores in real-time
   - Watch face detection status

4. **Get Result**
   - Click "Complete Verification"
   - See approval or rejection with reasons

## Common Issues & Fixes

### "Camera not detected"
✓ Check browser permissions
✓ Try different browser (Chrome/Firefox/Edge)
✓ Use HTTPS in production

### "Low liveness score"
✓ Improve lighting
✓ Move closer to camera
✓ Ensure face is fully visible

### "Cannot connect to backend"
✓ Verify backend is running (`http://localhost:5000/health`)
✓ Check firewall settings
✓ Try accessing from incognito window

### "CORS errors in console"
✓ Backend CORS is enabled by default
✓ Check browser console for actual error
✓ Verify API endpoint URLs in JavaScript

## Configuration for Testing

### Adjust Detection Sensitivity

Edit `backend/app/utils/config.py`:

```python
# Make verification stricter
LIVENESS_THRESHOLD = 0.7       # was 0.5
DEEPFAKE_THRESHOLD = 0.5       # was 0.6

# Reload backend after changes
```

### Enable Test Alerts

In `backend/app/utils/config.py`:

```python
ALERT_SLACK_ENABLED = True
SLACK_WEBHOOK_URL = 'your-webhook-url'

# Or configure email
ALERT_EMAIL_ENABLED = True
MAIL_SERVER = 'smtp.gmail.com'
```

## Testing Different Scenarios

### Scenario 1: Normal Legitimate User
- Well-lit environment
- Face centered in frame
- Follow challenge instructions
- Result: ✓ APPROVED

### Scenario 2: Poor Lighting
- Dim lighting
- Will see low liveness scores
- May get warning alerts
- Result: May be REJECTED

### Scenario 3: Partial Face
- Only half of face visible
- Face detection fails
- Alert generated
- Result: ✗ REJECTED

### Scenario 4: Multiple People
- Two faces in frame
- Currently handles single face only
- Alert generated
- Result: ✗ REJECTED

## API Testing with curl

### Check Backend Health
```bash
curl http://localhost:5000/health
```

### Start Session
```bash
curl -X POST http://localhost:5000/api/v1/kyc/start-session \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user_123"}'
```

### Get Active Alerts
```bash
curl http://localhost:5000/api/v1/alerts/active
```

### Get Alert Statistics
```bash
curl http://localhost:5000/api/v1/alerts/statistics
```

## File Locations Reference

```
Deepfake Video KYC/
├── main.py                         ← Run this to start backend
├── frontend/public/index.html      ← Open this in browser
├── backend/app/app.py              ← Flask app (don't run directly)
├── backend/app/services/
│   ├── liveness_detection.py       ← Liveness logic
│   ├── deepfake_detection.py       ← Deepfake detection logic
│   └── spoof_alerting.py           ← Alert system
├── backend/app/utils/config.py     ← Configuration file
└── README.md                        ← Full documentation
```

## Performance Tips

### For Faster Processing
```python
# In config.py
TARGET_RESOLUTION = (480, 360)  # Lower resolution
FRAME_SAMPLING_RATE = 2          # Process every 2nd frame
```

### For Better Accuracy
```python
# In config.py
TARGET_RESOLUTION = (640, 480)   # Higher resolution
FRAME_SAMPLING_RATE = 1          # Process every frame
```

## Next Steps

### For Development
1. Review code in `backend/app/services/`
2. Add custom challenges in `liveness_detection.py`
3. Tune detection thresholds
4. Read `docs/ARCHITECTURE.md` for deepfake detection details

### For Deployment
1. Follow `docs/DEPLOYMENT.md`
2. Set up production environment
3. Configure alert services
4. Run test suite (`python -m pytest tests/`)

### For Production
1. Change `SECRET_KEY` in config
2. Enable HTTPS
3. Set up database (PostgreSQL recommended)
4. Configure monitoring and logging
5. Set up backup procedures
6. Review security checklist

## Getting Help

**Check Logs:**
```bash
# Backend logs show in terminal where it runs
python main.py
```

**Browser Console:**
- Press F12 in browser
- Look for JavaScript errors in Console tab
- Network tab shows API requests

**Common Solutions:**
- Clear browser cache: Ctrl+Shift+Delete
- Restart backend
- Check firewall settings
- Try different browser

**Documentation:**
- README.md - Full documentation
- docs/ARCHITECTURE.md - System design
- docs/DEPLOYMENT.md - Deployment guide

---

**Enjoy testing the system!**

For production deployment, see [DEPLOYMENT.md](docs/DEPLOYMENT.md)
For technical details, see [ARCHITECTURE.md](docs/ARCHITECTURE.md)
