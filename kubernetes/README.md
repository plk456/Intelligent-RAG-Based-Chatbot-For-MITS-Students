# Kubernetes Deployment for MITS Chatbot

This directory contains the Kubernetes configuration files for deploying the MITS Chatbot.

## Prerequisites

- Kubernetes cluster (minikube, GKE, EKS, AKS, etc.)
- kubectl CLI
- Docker (for building images)

## Deployment Steps

### 1. Build Docker Images

First, build the frontend image:
```bash
docker build -t mits-chatbot-frontend:latest -f docker/Dockerfile ..
```

For the backend, you can use the official n8n image or build a custom one:
```bash
docker build -f docker/Dockerfile.n8n -t mits-chatbot-backend:latest ..
```

### 2. Deploy to Kubernetes

Apply the Kubernetes configurations:
```bash
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

Or use the deployment script:
```bash
./deploy.sh
```

### 3. Check Deployment Status

```bash
kubectl get pods
kubectl get services
```

### 4. Access the Application

- Frontend will be available through the LoadBalancer service
- Backend API will be accessible within the cluster at port 5678

## Configuration

The ConfigMap contains the workflow and dataset files needed by n8n. You may need to update the ConfigMap with your actual workflow data.

## Scaling

To scale the deployment:
```bash
kubectl scale deployment mits-chatbot-frontend --replicas=3
kubectl scale deployment mits-chatbot-backend --replicas=3
```