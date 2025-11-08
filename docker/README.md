# Docker Configuration for MITS Chatbot

This directory contains all Docker-related configuration files for the MITS Chatbot project.

## Files

- **[Dockerfile](file:///e:/MITS/Intelligent-RAG-Based-Chatbot-For-MITS-Students/docker/Dockerfile)**: Dockerfile for the frontend Node.js application
- **[Dockerfile.n8n](file:///e:/MITS/Intelligent-RAG-Based-Chatbot-For-MITS-Students/docker/Dockerfile.n8n)**: Dockerfile for the n8n backend
- **[docker-compose.yml](file:///e:/MITS/Intelligent-RAG-Based-Chatbot-For-MITS-Students/docker/docker-compose.yml)**: Docker Compose file for running both services together
- **[.dockerignore](file:///e:/MITS/Intelligent-RAG-Based-Chatbot-For-MITS-Students/docker/.dockerignore)**: Specifies files and directories to ignore during Docker builds

## Usage

### Build and Run with Docker Compose

```bash
docker-compose -f docker-compose.yml up --build
```

### Build Images Separately

```bash
# Build frontend
docker build -t mits-chatbot-frontend -f Dockerfile ..

# Build backend
docker build -f Dockerfile.n8n -t mits-chatbot-backend ..
```

### Run Containers

```bash
# Run frontend
docker run -p 3000:3000 mits-chatbot-frontend

# Run backend
docker run -p 5678:5678 mits-chatbot-backend
```