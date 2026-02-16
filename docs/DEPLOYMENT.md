# Deployment Guide

## Development Deployment

### Local Machine Setup

```bash
# 1. Clone and setup
cd "Deepfake Video KYC"
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Configure environment
copy .env.example .env

# 4. Run backend
python main.py

# 5. In another terminal, serve frontend
cd frontend/public
python -m http.server 8000

# 6. Access:
# Frontend: http://localhost:8000
# Backend: http://localhost:5000
# API docs: http://localhost:5000/api/v1
```

## Docker Deployment

### Single Container

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", \
     "--timeout", "120", "--access-logfile", "-", \
     "--error-logfile", "-", "main:app"]
```

Build and run:

```bash
# Build image
docker build -t kyc-verification:1.0 .

# Run container
docker run \
  --name kyc-verification \
  -p 5000:5000 \
  -e FLASK_ENV=production \
  -e SECRET_KEY=your-secret-key \
  -v kyc-logs:/app/logs \
  kyc-verification:1.0

# View logs
docker logs -f kyc-verification

# Stop container
docker stop kyc-verification
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: .
    container_name: kyc-backend
    ports:
      - "5000:5000"
    environment:
      FLASK_ENV: production
      SECRET_KEY: ${SECRET_KEY}
      DATABASE_URL: postgresql://user:password@db:5432/kyc_db
      SLACK_WEBHOOK_URL: ${SLACK_WEBHOOK_URL}
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    container_name: kyc-postgres
    environment:
      POSTGRES_USER: kyc_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: kyc_db
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

  frontend:
    image: nginx:alpine
    container_name: kyc-frontend
    ports:
      - "80:80"
    volumes:
      - ./frontend/public:/usr/share/nginx/html
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres-data:
```

Start services:

```bash
# Create .env file with variables
echo "SECRET_KEY=your-production-secret-key" > .env
echo "DB_PASSWORD=secure-db-password" >> .env
echo "SLACK_WEBHOOK_URL=https://hooks.slack.com/..." >> .env

# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

## Kubernetes Deployment

### Prerequisites
- Kubernetes cluster (GKE, AKS, EKS, or local minikube)
- kubectl configured
- helm (optional)

### Deployment Manifests

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kyc-verification
  labels:
    app: kyc-verification
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kyc-verification
  template:
    metadata:
      labels:
        app: kyc-verification
    spec:
      containers:
      - name: backend
        image: kyc-verification:1.0
        ports:
        - containerPort: 5000
        env:
        - name: FLASK_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: kyc-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: kyc-verification-service
spec:
  selector:
    app: kyc-verification
  type: LoadBalancer
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5000

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: kyc-verification-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: kyc-verification
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

Deploy:

```bash
# Create secrets
kubectl create secret generic kyc-secrets \
  --from-literal=database-url=postgresql://user:pass@db:5432/kyc

# Deploy
kubectl apply -f k8s-deployment.yaml

# Check status
kubectl get deployments
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/kyc-verification

# Scale manually
kubectl scale deployment kyc-verification --replicas=5
```

## Production Checklist

### Security
- [ ] Change SECRET_KEY to random value
- [ ] Enable HTTPS/TLS (certificate from provider)
- [ ] Configure CORS allowlist
- [ ] Enable database encryption at rest
- [ ] Configure network policies
- [ ] Set up WAF (Web Application Firewall)
- [ ] Enable audit logging
- [ ] Regular security patches

### Performance
- [ ] Set up CDN for frontend assets
- [ ] Enable database connection pooling
- [ ] Configure Redis cache (optional)
- [ ] Set up rate limiting (100 req/min per IP)
- [ ] Configure request timeouts
- [ ] Enable gzip compression

### Monitoring
- [ ] Set up health checks
- [ ] Configure alerting
- [ ] Set up log aggregation (ELK, Splunk)
- [ ] Monitor resource usage
- [ ] Track API response times
- [ ] Monitor alert volume

### Alerting
- [ ] Configure email server
- [ ] Set up Slack webhook
- [ ] Set up SMS alerts
- [ ] Configure escalation policies
- [ ] Test alert dispatch

### Backup & Recovery
- [ ] Daily database backups
- [ ] Off-site backup storage
- [ ] Backup encryption
- [ ] Recovery time objective (RTO): 4 hours
- [ ] Recovery point objective (RPO): 24 hours
- [ ] Test recovery procedures

### Compliance
- [ ] GDPR: Data deletion policy
- [ ] PCI-DSS: Data protection measures
- [ ] SOC2: Audit controls
- [ ] Privacy: Terms of service updated
- [ ] Compliance: Regular audits scheduled

## Nginx Configuration

Create `nginx.conf`:

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    upstream backend {
        server backend:5000;
    }

    server {
        listen 80;
        server_name kyc-verification.institution.com;

        # API endpoints
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Frontend
        location / {
            root /usr/share/nginx/html;
            try_files $uri /index.html;
            
            # Cache static assets
            expires 1d;
            add_header Cache-Control "public, immutable";
        }

        # Static assets with long cache
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            root /usr/share/nginx/html;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
    }
}
```

## Monitoring Setup

### Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'kyc-backend'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
```

### ELK Stack Setup

```bash
# Run Elasticsearch, Logstash, Kibana
docker-compose -f elk-stack.yml up -d

# Configure log forwarding from Flask app
# Logs accessible at http://localhost:5601
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Out of memory | Increase container memory limit, reduce frame size |
| High latency | Check CPU usage, scale horizontally, optimize algorithms |
| Database connection errors | Verify connection string, check network policies |
| SSL certificate errors | Renew certificate, verify in reverse proxy |
| Alert delivery failures | Check email/Slack configuration, verify credentials |

## Performance Tuning

### Backend
```python
# config.py optimization
LIVENESS_THRESHOLD = 0.5      # Adjust based on requirements
DEEPFAKE_THRESHOLD = 0.6      # Find optimal balance
FRAME_SAMPLING_RATE = 3       # Process every 3rd frame for speed
TARGET_RESOLUTION = (480, 360) # Lower for faster processing
```

### Database
```sql
-- Index frequently queried columns
CREATE INDEX idx_session_id ON sessions(session_id);
CREATE INDEX idx_user_id ON sessions(user_id);
CREATE INDEX idx_alert_severity ON alerts(severity);
CREATE INDEX idx_alert_timestamp ON alerts(timestamp DESC);

-- Vacuum and analyze
VACUUM ANALYZE;
```

## Rollback Procedure

```bash
# If latest deployment has issues

# Kubernetes
kubectl rollout undo deployment/kyc-verification

# Docker
docker rm -f kyc-verification
docker run -d --name kyc-verification kyc-verification:0.9

# Database migrations (if any)
python manage.py db downgrade
```

## Support & Maintenance

- Monitor logs regularly
- Check alert volume trends
- Update dependencies monthly
- Perform security audits quarterly
- Test disaster recovery annually
- Review and optimize performance regularly
