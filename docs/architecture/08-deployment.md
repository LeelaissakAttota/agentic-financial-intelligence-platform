# Deployment Architecture
## Agentic Financial Intelligence Platform

---

## Overview

This document describes the deployment architecture for the Agentic Financial Intelligence Platform, covering local development, staging, and production environments.

---

## Environment Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEPLOYMENT ENVIRONMENTS                               │
├─────────────────┬─────────────────┬─────────────────┬───────────────────────┤
│   LOCAL DEV     │    STAGING      │   PRODUCTION    │   DR / FAILOVER       │
├─────────────────┼─────────────────┼─────────────────┼───────────────────────┤
│ docker-compose  │  Kubernetes     │  Kubernetes     │  Cross-region         │
│ (single node)   │  (dev cluster)  │  (prod cluster) │  (active-passive)     │
├─────────────────┼─────────────────┼─────────────────┼───────────────────────┤
│ SQLite/PostgreSQL│ PostgreSQL      │ PostgreSQL      │ PostgreSQL            │
│ ChromaDB (local) │ ChromaDB        │ ChromaDB        │ ChromaDB              │
│ Redis (local)    │ Redis Cluster   │ Redis Cluster   │ Redis Geo-replication │
│ No TLS           │ TLS termination │ mTLS + TLS      │ TLS                   │
│ No auth          │ SSO/OIDC        │ SSO/OIDC + MFA  │ SSO/OIDC + MFA        │
└─────────────────┴─────────────────┴─────────────────┴───────────────────────┘
```

---

## Local Development

### Prerequisites
- Docker Desktop 4.30+
- Python 3.11+
- Git
- 16GB+ RAM recommended

### Quick Start
```bash
# 1. Clone repository
git clone https://github.com/LeelaissakAttota/agentic-financial-intelligence-platform.git
cd agentic-financial-intelligence-platform

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start all services
docker-compose up -d --build

# 4. Verify health
curl http://localhost:8000/health/detailed
curl http://localhost:8501

# 5. Run tests
docker-compose exec api pytest tests/ -q
```

### Service Ports (Local)
| Service | Port | URL |
|---------|------|-----|
| API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| Streamlit | 8501 | http://localhost:8501 |
| PostgreSQL | 5432 | localhost:5432 |
| ChromaDB | 8001 | http://localhost:8001 |
| Redis | 6379 | localhost:6379 |

### Docker Compose (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: financial_research
      POSTGRES_USER: financial_research
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U financial_research"]
      interval: 10s
      timeout: 5s
      retries: 5

  chromadb:
    image: chromadb/chroma:1.5.9
    environment:
      CHROMA_SERVER_HOST: 0.0.0.0
      CHROMA_SERVER_HTTP_PORT: 8001
    volumes:
      - chroma_data:/chroma/chroma
    ports:
      - "8001:8001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/v1/heartbeat"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: development
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_USER=financial_research
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=financial_research
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8001
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
    depends_on:
      postgres:
        condition: service_healthy
      chromadb:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

  streamlit:
    build:
      context: .
      dockerfile: Dockerfile
      target: development
    environment:
      - API_URL=http://api:8000
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8001
    ports:
      - "8501:8501"
    volumes:
      - ./dashboard:/app/dashboard
      - ./src:/app/src
    depends_on:
      - api
    command: streamlit run dashboard/app.py --server.port=8501 --server.address=0.0.0.0

volumes:
  postgres_data:
  chroma_data:
  redis_data:
```

### Dockerfile (Multi-stage)
```dockerfile
# Dockerfile
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base AS development
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
EXPOSE 8000 8501

# Production stage
FROM base AS production
COPY . .
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Staging Environment (Kubernetes)

### Namespace & Resources
```yaml
# k8s/staging/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: financial-research-staging
  labels:
    environment: staging
    team: platform
```

### API Deployment
```yaml
# k8s/staging/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: financial-research-api
  namespace: financial-research-staging
  labels:
    app: financial-research-api
    version: v1.7.0-phase8
spec:
  replicas: 3
  selector:
    matchLabels:
      app: financial-research-api
  template:
    metadata:
      labels:
        app: financial-research-api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: financial-research-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: api
        image: ghcr.io/LeelaissakAttota/financial-research-api:v1.7.0-phase8
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: financial-research-config
        - secretRef:
            name: financial-research-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: financial-research-api
  namespace: financial-research-staging
spec:
  selector:
    app: financial-research-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Ingress (TLS Termination)
```yaml
# k8s/staging/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: financial-research-ingress
  namespace: financial-research-staging
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-staging"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - staging-api.financial-research.example.com
    - staging-app.financial-research.example.com
    secretName: financial-research-tls
  rules:
  - host: staging-api.financial-research.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: financial-research-api
            port:
              number: 80
  - host: staging-app.financial-research.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: financial-research-streamlit
            port:
              number: 8501
```

### ConfigMap & Secrets
```yaml
# k8s/staging/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: financial-research-config
  namespace: financial-research-staging
data:
  POSTGRES_HOST: "postgres-staging.cluster-xyz.us-east-1.rds.amazonaws.com"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "financial_research"
  CHROMA_HOST: "chromadb-staging"
  CHROMA_PORT: "8000"
  REDIS_HOST: "redis-staging.xyz.use1.cache.amazonaws.com"
  REDIS_PORT: "6379"
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "staging"
---
# k8s/staging/secrets.yaml (sealed secrets or external-secrets)
apiVersion: v1
kind: Secret
metadata:
  name: financial-research-secrets
  namespace: financial-research-staging
type: Opaque
stringData:
  POSTGRES_USER: "financial_research"
  POSTGRES_PASSWORD: "ENCRYPTED_BY_SEALED_SECRETS"
  OPENROUTER_API_KEY: "ENCRYPTED_BY_SEALED_SECRETS"
  JWT_PRIVATE_KEY: "ENCRYPTED_BY_SEALED_SECRETS"
  REDIS_PASSWORD: "ENCRYPTED_BY_SEALED_SECRETS"
```

---

## Production Environment (Kubernetes)

### High Availability Configuration
```yaml
# k8s/production/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: financial-research-api
  namespace: financial-research-prod
spec:
  replicas: 6  # Minimum 3 AZs × 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0  # Zero-downtime deployments
  selector:
    matchLabels:
      app: financial-research-api
  template:
    metadata:
      labels:
        app: financial-research-api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: financial-research-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: financial-research-api
      containers:
      - name: api
        image: ghcr.io/LeelaissakAttota/financial-research-api:v1.7.0-phase8
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: financial-research-config
        - secretRef:
            name: financial-research-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 30
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /app/.cache
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 1Gi
      - name: cache
        emptyDir:
          sizeLimit: 500Mi
---
apiVersion: v1
kind: Service
metadata:
  name: financial-research-api
  namespace: financial-research-prod
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
spec:
  selector:
    app: financial-research-api
  ports:
  - port: 443
    targetPort: 8000
    name: https
  type: LoadBalancer
```

### Pod Disruption Budget
```yaml
# k8s/production/pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: financial-research-api-pdb
  namespace: financial-research-prod
spec:
  minAvailable: 4  # Ensure 4 of 6 always available
  selector:
    matchLabels:
      app: financial-research-api
```

### Horizontal Pod Autoscaler
```yaml
# k8s/production/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: financial-research-api-hpa
  namespace: financial-research-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: financial-research-api
  minReplicas: 6
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

---

## Database Deployment

### PostgreSQL (RDS/Aurora)
```yaml
# Production: AWS Aurora PostgreSQL
# - Multi-AZ deployment (3 AZs)
# - Read replicas (2-3 for read scaling)
# - Automated backups (30-day retention)
# - Point-in-time recovery
# - Encryption at rest (KMS)
# - IAM authentication
# - Performance Insights enabled
```

### ChromaDB (Vector Store)
```yaml
# Option 1: ChromaDB Cloud (managed)
# Option 2: Self-hosted on Kubernetes
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chromadb
  namespace: financial-research-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chromadb
  template:
    spec:
      containers:
      - name: chromadb
        image: chromadb/chroma:1.5.9
        ports:
        - containerPort: 8000
        env:
        - name: CHROMA_SERVER_HOST
          value: "0.0.0.0"
        - name: CHROMA_SERVER_HTTP_PORT
          value: "8000"
        - name: PERSIST_DIRECTORY
          value: "/chroma/chroma"
        volumeMounts:
        - name: chroma-data
          mountPath: /chroma/chroma
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
      volumes:
      - name: chroma-data
        persistentVolumeClaim:
          claimName: chromadb-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: chromadb-pvc
  namespace: financial-research-prod
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: gp3
  resources:
    requests:
      storage: 100Gi
```

### Redis (ElastiCache)
```yaml
# Production: AWS ElastiCache Redis Cluster
# - Cluster mode enabled (3 shards)
# - Multi-AZ with automatic failover
# - Encryption in-transit (TLS) and at-rest
# - Redis 7.x
# - Backup retention: 7 days
```

---

## Monitoring & Observability

### Prometheus Metrics
```yaml
# k8s/monitoring/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: financial-research-api
  namespace: financial-research-prod
spec:
  selector:
    matchLabels:
      app: financial-research-api
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### Grafana Dashboards
- **API Overview**: Request rate, latency (p50/p95/p99), error rate
- **Agent Performance**: Per-agent latency, success rate, token usage
- **Database**: Connection pool, query latency, replication lag
- **Cache**: Hit rate, memory usage, eviction rate
- **LLM Costs**: Token usage, cost per model, cost per agent
- **Business**: Research completed, reports generated, alerts fired

### Alerting Rules
```yaml
# k8s/monitoring/alerts.yaml
groups:
- name: financial-research
  rules:
  - alert: APIHighLatency
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "API p95 latency > 2s"
      
  - alert: APIHighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "API error rate > 5%"
      
  - alert: DatabaseConnectionsHigh
    expr: pg_stat_database_numbackends / pg_settings_max_connections > 0.8
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "PostgreSQL connections > 80%"
      
  - alert: LLMCostSpike
    expr: rate(llm_cost_usd_total[1h]) > 100
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "LLM cost > $100/hour"
```

---

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  release:
    types: [published]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Lint (ruff)
        run: ruff check src/ tests/
      
      - name: Format check (black)
        run: black --check src/ tests/
      
      - name: Type check (mypy)
        run: mypy src/
      
      - name: Security scan (bandit)
        run: bandit -r src/ -f json -o bandit.json
      
      - name: Run tests
        run: pytest tests/ -q --tb=short
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PORT: 5432
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: financial_research
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  build-and-push:
    needs: lint-and-test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' || github.event_name == 'release'
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          target: production

  deploy-staging:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging
    steps:
      - name: Deploy to staging
        run: |
          kubectl set image deployment/financial-research-api \
            api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            -n financial-research-staging
      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/financial-research-api \
            -n financial-research-staging --timeout=300s

  deploy-production:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    environment: production
    steps:
      - name: Deploy to production
        run: |
          kubectl set image deployment/financial-research-api \
            api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.event.release.tag_name }} \
            -n financial-research-prod
      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/financial-research-api \
            -n financial-research-prod --timeout=600s
      - name: Smoke tests
        run: |
          curl -f https://api.financial-research.example.com/health/detailed
          curl -f https://api.financial-research.example.com/metrics
```

---

## Backup & Disaster Recovery

### Backup Strategy
| Component | Frequency | Retention | Method |
|-----------|-----------|-----------|--------|
| PostgreSQL | Continuous (WAL) + Daily snapshot | 30 days | pgBackRest / RDS Automated |
| ChromaDB | Daily | 14 days | Volume snapshot |
| Redis | Hourly RDB | 7 days | ElastiCache Backup |
| Config/Secrets | On change | 90 days | Git + Sealed Secrets |

### Recovery Procedures
```bash
# PostgreSQL Point-in-Time Recovery
# 1. Identify recovery target time
# 2. Restore base backup
# 3. Apply WAL up to target time
# 4. Promote replica if primary failed

# ChromaDB Recovery
# 1. Restore PVC from snapshot
# 2. Recreate deployment
# 3. Verify collection counts

# Redis Recovery
# 1. Create new cluster from backup
# 2. Update DNS/endpoints
# 3. Flush application cache
```

### RTO/RPO Targets
| Component | RTO | RPO |
|-----------|-----|-----|
| API | 5 min | 0 (stateless) |
| PostgreSQL | 15 min | < 1 min (WAL) |
| ChromaDB | 30 min | 24 hours |
| Redis | 10 min | 1 hour |

---

## Cost Optimization

### Right-Sizing
```yaml
# Regular review of resource requests/limits
# Use VPA (Vertical Pod Autoscaler) in recommendation mode
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: financial-research-api-vpa
  namespace: financial-research-prod
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: financial-research-api
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: api
      minAllowed:
        cpu: 250m
        memory: 512Mi
      maxAllowed:
        cpu: 2000m
        memory: 4Gi
```

### Spot Instances (Non-critical)
```yaml
# Use spot instances for batch workloads
# - Report generation
# - Model training
# - Backtesting
# Savings: 60-90% vs on-demand
```

---

*Document Version: 1.0*  
*Last Updated: 2026-07-18*  
*Platform: Agentic Financial Intelligence Platform v1.7.0-phase8*