#!/bin/bash

# Deploy the MITS Chatbot to Kubernetes

# Create the namespace
kubectl create namespace mits-chatbot || true

# Apply the ConfigMap
kubectl apply -f configmap.yaml -n mits-chatbot

# Apply the deployments
kubectl apply -f deployment.yaml -n mits-chatbot

# Apply the services
kubectl apply -f service.yaml -n mits-chatbot

echo "MITS Chatbot deployed to Kubernetes!"
echo "Frontend service is available at http://localhost:3000"
echo "Backend service is available at http://localhost:5678"