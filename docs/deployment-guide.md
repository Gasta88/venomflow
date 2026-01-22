# VenomFlow Deployment Guide

## Prerequisites

### System Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **System Resources**:
  - Minimum: 4GB RAM, 2 CPU cores, 20GB disk
  - Recommended: 8GB RAM, 4 CPU cores, 50GB disk

### Software Dependencies

- **Git**: For cloning the repository
- **bash**: For running shell scripts
- **Python 3.11+**: For running utility scripts locally (optional)

## Development Deployment

### 1. Clone Repository

```bash
git clone https://github.com/Gasta88/venomflow.git
cd venomflow
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Database credentials
POSTGRES_USER=venomflow_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=venomflow

# Dagster database (separate from main DB)
DAGSTER_POSTGRES_USER=dagster_user
DAGSTER_POSTGRES_PASSWORD=your_dagster_password_here
DAGSTER_POSTGRES_DB=dagster

# API keys
NCBI_API_KEY=your_ncbi_api_key_here

# Grafana admin
GRAFANA_ADMIN_PASSWORD=your_grafana_password_here
```

### 3. Start Services

```bash
docker-compose up -d
```

Wait for all services to start (may take 1-2 minutes):

```bash
docker-compose ps
```

### 4. Initialize Database

```bash
chmod +x scripts/init_database.sh
./scripts/init_database.sh
```

### 5. Seed Test Data (Optional)

```bash
docker-compose exec api python /home/user/webapp/scripts/seed_test_data.py
```

### 6. Verify Installation

```bash
python scripts/verify_infrastructure.py
```

### 7. Access Services

- **GraphQL API**: http://localhost:8000/graphql
- **Dagster UI**: http://localhost:3001
- **Grafana**: http://localhost:3000 (admin/your_password)
- **Prometheus**: http://localhost:9090

## Production Deployment

### Architecture Overview

For production, we recommend a cloud-native architecture:

```
┌─────────────┐
│   Route 53  │ (DNS)
└──────┬──────┘
       │
┌──────▼──────┐
│     ALB     │ (Load Balancer)
└──────┬──────┘
       │
┌──────▼──────────────────────┐
│      ECS/EKS Cluster         │
│  ┌──────┐  ┌──────┐         │
│  │ API  │  │Dagster│         │
│  └──────┘  └──────┘         │
└─────────────────────────────┘
       │              │
┌──────▼─────┐  ┌────▼────┐
│  RDS       │  │ElastiCache│
│(PostgreSQL)│  │  (Redis)  │
└────────────┘  └───────────┘
```

### AWS Deployment

#### 1. Database Setup (RDS)

```bash
# Create PostgreSQL RDS instance
aws rds create-db-instance \
  --db-instance-identifier venomflow-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.3 \
  --master-username venomflow_admin \
  --master-user-password <secure-password> \
  --allocated-storage 50 \
  --backup-retention-period 7 \
  --multi-az
```

#### 2. Cache Setup (ElastiCache)

```bash
# Create Redis ElastiCache cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id venomflow-redis \
  --cache-node-type cache.t3.small \
  --engine redis \
  --num-cache-nodes 1
```

#### 3. Container Registry

```bash
# Create ECR repositories
aws ecr create-repository --repository-name venomflow/api
aws ecr create-repository --repository-name venomflow/dagster

# Build and push images
docker build -t venomflow/api:latest ./api
docker tag venomflow/api:latest <account-id>.dkr.ecr.<region>.amazonaws.com/venomflow/api:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/venomflow/api:latest

docker build -t venomflow/dagster:latest ./dagster
docker tag venomflow/dagster:latest <account-id>.dkr.ecr.<region>.amazonaws.com/venomflow/dagster:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/venomflow/dagster:latest
```

#### 4. ECS Task Definitions

**API Task Definition** (`api-task-def.json`):

```json
{
  "family": "venomflow-api",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "<account-id>.dkr.ecr.<region>.amazonaws.com/venomflow/api:latest",
      "memory": 1024,
      "cpu": 512,
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "POSTGRES_HOST",
          "value": "<rds-endpoint>"
        },
        {
          "name": "REDIS_HOST",
          "value": "<elasticache-endpoint>"
        }
      ],
      "secrets": [
        {
          "name": "POSTGRES_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:<region>:<account-id>:secret:venomflow/db-password"
        }
      ]
    }
  ]
}
```

#### 5. Load Balancer

```bash
# Create Application Load Balancer
aws elbv2 create-load-balancer \
  --name venomflow-alb \
  --subnets <subnet-1> <subnet-2> \
  --security-groups <sg-id>

# Create target group
aws elbv2 create-target-group \
  --name venomflow-api-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id <vpc-id> \
  --health-check-path /health
```

### Kubernetes Deployment

#### 1. Create Namespace

```bash
kubectl create namespace venomflow
```

#### 2. Create Secrets

```bash
kubectl create secret generic venomflow-db-secret \
  --from-literal=username=venomflow_user \
  --from-literal=password=<secure-password> \
  -n venomflow
```

#### 3. Deploy PostgreSQL (StatefulSet)

```yaml
# postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: venomflow
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: venomflow-db-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: venomflow-db-secret
              key: password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
```

#### 4. Deploy API (Deployment)

```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: venomflow-api
  namespace: venomflow
spec:
  replicas: 3
  selector:
    matchLabels:
      app: venomflow-api
  template:
    metadata:
      labels:
        app: venomflow-api
    spec:
      containers:
      - name: api
        image: <your-registry>/venomflow/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: POSTGRES_HOST
          value: postgres
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: venomflow-db-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: venomflow-db-secret
              key: password
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### 5. Create Service & Ingress

```yaml
# api-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: venomflow-api
  namespace: venomflow
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: venomflow-api
---
# api-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: venomflow-ingress
  namespace: venomflow
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.venomflow.com
    secretName: venomflow-tls
  rules:
  - host: api.venomflow.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: venomflow-api
            port:
              number: 8000
```

## Monitoring Setup

### Prometheus

```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: venomflow
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
      - job_name: 'venomflow-api'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - venomflow
```

### Grafana Dashboards

Import pre-built dashboards:
1. FastAPI metrics dashboard (ID: 14280)
2. PostgreSQL dashboard (ID: 9628)
3. Redis dashboard (ID: 11835)

## Backup Strategy

### Database Backups

```bash
# Automated daily backups
0 2 * * * /home/user/webapp/scripts/backup.sh
```

### Disaster Recovery

1. **Database**: Automated RDS snapshots (7-day retention)
2. **Application State**: GitOps with all configs in version control
3. **Secrets**: AWS Secrets Manager / Kubernetes Secrets

## Security Checklist

- [ ] Use strong passwords for all services
- [ ] Enable SSL/TLS for all connections
- [ ] Configure firewall rules (security groups)
- [ ] Enable database encryption at rest
- [ ] Set up VPC with private subnets
- [ ] Implement API authentication (JWT)
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Secrets stored in vault (not in code)
- [ ] Rate limiting on API endpoints

## Scaling Guidelines

### Horizontal Scaling

```bash
# Scale API replicas
kubectl scale deployment venomflow-api --replicas=5 -n venomflow

# Scale Dagster workers
kubectl scale deployment dagster-workers --replicas=3 -n venomflow
```

### Vertical Scaling

Adjust resource limits in deployment manifests based on metrics.

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs <service-name>
# or
kubectl logs -f deployment/venomflow-api -n venomflow
```

### Database Connection Issues

```bash
# Test database connectivity
psql -h <host> -U venomflow_user -d venomflow -c "SELECT 1"
```

### Performance Issues

```bash
# Check resource usage
docker stats
# or
kubectl top pods -n venomflow
```

## Maintenance

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose build
docker-compose up -d
```

### Database Migrations

```bash
# Run Alembic migrations (future)
alembic upgrade head
```

## Support

For issues and questions:
- **GitHub Issues**: https://github.com/Gasta88/venomflow/issues
- **Documentation**: https://venomflow.readthedocs.io
