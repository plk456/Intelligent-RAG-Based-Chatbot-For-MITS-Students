@echo off

echo Deploying MITS Chatbot to Kubernetes...

REM Create the namespace
kubectl create namespace mits-chatbot || echo Namespace already exists

REM Apply the ConfigMap
kubectl apply -f configmap.yaml -n mits-chatbot

REM Apply the deployments
kubectl apply -f deployment.yaml -n mits-chatbot

REM Apply the services
kubectl apply -f service.yaml -n mits-chatbot

echo.
echo MITS Chatbot deployed to Kubernetes!
echo Frontend service is available at http://localhost:3000
echo Backend service is available at http://localhost:5678
pause