# Amazon Managed Prometheus Integration

## Overview

This guide covers integrating zero2prod with Amazon Managed Service for Prometheus (AMP).

## Application Changes

The application now exposes Prometheus metrics at `/metrics` endpoint with:
- `http_requests_total` - Counter for HTTP requests by method, path, and status
- `subscription_requests_total` - Counter for subscription requests

## Setup Steps

### 1. Create AMP Scraper (AWS Console)

1. Navigate to Amazon Managed Service for Prometheus
2. Select your workspace
3. Go to "All scrapers" → "Create scraper"
4. Configure:
   - **Source**: Select your EKS cluster
   - **Scraper alias**: `zero2prod-scraper`
   - **Configuration**: Upload `k8s/amp-scraper-config.yaml`
   - **Destination**: Your AMP workspace

### 2. Create AMP Scraper (AWS CLI)

```bash
# Get your EKS cluster ARN
CLUSTER_ARN=$(aws eks describe-cluster --name <your-cluster-name> --query 'cluster.arn' --output text)

# Get your AMP workspace ARN
WORKSPACE_ARN=$(aws amp describe-workspace --workspace-id <workspace-id> --query 'workspace.arn' --output text)

# Create scraper
aws amp create-scraper \
  --alias zero2prod-scraper \
  --source eksConfiguration="{clusterArn=$CLUSTER_ARN,subnetIds=[subnet-xxx,subnet-yyy]}" \
  --scrape-configuration configurationBlob="$(base64 -i k8s/amp-scraper-config.yaml)" \
  --destination ampConfiguration="{workspaceArn=$WORKSPACE_ARN}"
```

### 3. Deploy Application

```bash
kubectl apply -k k8s/overlays/dev
```

### 4. Verify Metrics

Test locally:
```bash
kubectl port-forward svc/zero2prod-service 8000:80
curl http://localhost:8000/metrics
```

## Query Metrics in AMP

Example PromQL queries:

```promql
# Total HTTP requests
http_requests_total

# Request rate per minute
rate(http_requests_total[1m])

# Subscription requests
subscription_requests_total
```

## Grafana Integration

Connect Amazon Managed Grafana to your AMP workspace to visualize metrics.

## Cost Considerations

- AMP charges for ingested samples and query samples processed
- Scraper runs every 30 seconds (configurable in scraper config)
- Monitor usage via CloudWatch metrics: `ActiveSeries`, `IngestionRate`
