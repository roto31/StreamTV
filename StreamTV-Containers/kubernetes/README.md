# StreamTV Kubernetes Distribution

Complete Kubernetes manifests for deploying StreamTV in a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (v1.20+)
- kubectl configured
- PersistentVolume provisioner (for data storage)
- Ingress controller (optional, for external access)

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Create ConfigMap and Secrets

```bash
# Update configmap.yaml with your settings
kubectl apply -f configmap.yaml

# Create secrets (update with your values)
kubectl apply -f secrets.yaml
# Or create from command line:
kubectl create secret generic streamtv-secrets \
  --from-literal=youtube-api-key='your-key' \
  --from-literal=access-token='your-token' \
  -n streamtv
```

### 3. Create PersistentVolumeClaims

```bash
kubectl apply -f pvc.yaml
```

### 4. Deploy StreamTV

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### 5. (Optional) Create Ingress

```bash
# Update ingress.yaml with your domain
kubectl apply -f ingress.yaml
```

### 6. Check Status

```bash
kubectl get pods -n streamtv
kubectl get svc -n streamtv
kubectl logs -f deployment/streamtv -n streamtv
```

## Using Kustomize

```bash
# Apply all resources
kubectl apply -k .

# With custom image
kubectl apply -k . --dry-run=client -o yaml | \
  sed 's|streamtv:latest|your-registry/streamtv:v1.0.0|' | \
  kubectl apply -f -
```

## Configuration

### ConfigMap

Update `configmap.yaml` with your settings:

```yaml
data:
  base_url: "http://streamtv.example.com"
  plex-base-url: "http://plex.example.com:32400"
```

### Secrets

Create secrets for sensitive data:

```bash
kubectl create secret generic streamtv-secrets \
  --from-literal=youtube-api-key='your-key' \
  --from-literal=archive-org-username='username' \
  --from-literal=archive-org-password='password' \
  --from-literal=access-token='token' \
  --from-literal=plex-token='plex-token' \
  -n streamtv
```

### PersistentVolumes

Update storage class in `pvc.yaml`:

```yaml
storageClassName: fast-ssd  # Your storage class
```

## Scaling

### Horizontal Scaling

**Important**: StreamTV uses SQLite by default, which doesn't support multiple replicas. For scaling:

1. **Use PostgreSQL** (recommended):
   - Deploy PostgreSQL as a separate service
   - Update `STREAMTV_DATABASE_URL` to use PostgreSQL
   - Set `replicas: 3` in deployment.yaml

2. **Or use ReadWriteMany storage**:
   - Update PVCs to use ReadWriteMany access mode
   - Use a storage class that supports it (e.g., NFS)

### Vertical Scaling

Update resource limits in `deployment.yaml`:

```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "1"
  limits:
    memory: "4Gi"
    cpu: "4"
```

## Access Methods

### LoadBalancer Service

```bash
kubectl get svc streamtv -n streamtv
# Access via EXTERNAL-IP:8410
```

### NodePort Service

```bash
kubectl get svc streamtv-nodeport -n streamtv
# Access via <node-ip>:30410
```

### Ingress

Update `ingress.yaml` with your domain and access via:
- http://streamtv.example.com

### Port Forwarding (Development)

```bash
kubectl port-forward deployment/streamtv 8410:8410 -n streamtv
# Access at http://localhost:8410
```

## Monitoring

### Health Checks

Health checks are configured in the deployment:

```bash
# Check pod health
kubectl describe pod <pod-name> -n streamtv

# Check health endpoint
kubectl exec -it deployment/streamtv -n streamtv -- \
  curl http://localhost:8410/api/health
```

### Logs

```bash
# All pods
kubectl logs -f deployment/streamtv -n streamtv

# Specific pod
kubectl logs -f <pod-name> -n streamtv

# Previous container (if restarted)
kubectl logs -f <pod-name> -n streamtv --previous
```

### Metrics

```bash
# Resource usage
kubectl top pod -n streamtv

# Detailed metrics
kubectl describe pod <pod-name> -n streamtv
```

## Updates and Rollouts

### Rolling Update

```bash
# Update image
kubectl set image deployment/streamtv \
  streamtv=streamtv:v1.1.0 -n streamtv

# Check rollout status
kubectl rollout status deployment/streamtv -n streamtv

# Rollback if needed
kubectl rollout undo deployment/streamtv -n streamtv
```

### Blue-Green Deployment

Create a second deployment with different labels and switch services.

## Backup and Restore

### Backup

```bash
# Backup data PVC
kubectl exec -n streamtv <pod-name> -- \
  tar czf /tmp/backup.tar.gz -C /app/data .

kubectl cp streamtv/<pod-name>:/tmp/backup.tar.gz ./backup.tar.gz
```

### Restore

```bash
# Copy backup to pod
kubectl cp ./backup.tar.gz streamtv/<pod-name>:/tmp/

# Extract in pod
kubectl exec -n streamtv <pod-name> -- \
  tar xzf /tmp/backup.tar.gz -C /app/data
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n streamtv

# Check events
kubectl get events -n streamtv --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n streamtv
```

### PVC Issues

```bash
# Check PVC status
kubectl get pvc -n streamtv

# Describe PVC
kubectl describe pvc streamtv-data-pvc -n streamtv
```

### Service Not Accessible

```bash
# Check service
kubectl get svc -n streamtv
kubectl describe svc streamtv -n streamtv

# Check endpoints
kubectl get endpoints -n streamtv
```

## Production Considerations

1. **Use StatefulSet** for ordered deployment and stable network IDs
2. **Configure resource quotas** and limits
3. **Enable network policies** for security
4. **Use secrets management** (e.g., External Secrets Operator)
5. **Set up monitoring** (Prometheus, Grafana)
6. **Configure backup strategy** for persistent volumes
7. **Use Helm charts** for easier management

## See Also

- [Docker Distribution](../docker/README.md)
- [Docker Compose Distribution](../docker-compose/README.md)
- [Podman Distribution](../podman/README.md)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
