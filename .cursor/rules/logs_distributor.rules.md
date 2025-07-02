# Cursor Rules: Logs Distributor Project Plan

## 1. Project Structure

- `app/main.py`: FastAPI server for log ingestion
- `app/distributor.py`: Async log distributor logic
- `app/redis_queue.py`: Redis queue interface
- `app/health_check.py`: Analyzer health check logic
- `app/config.py`: Configuration (Redis, analyzers, etc.)
- `app/models.py`: Pydantic models for log packets, etc.

## 2. Implementation Plan

### A. Log Ingestion Server (FastAPI + Uvicorn)
- Endpoint: `POST /ingest`
- Receives log packets from agents and pushes to Redis queue

### B. Redis Log Queue
- Stores incoming log packets for distribution
- Use Redis (Docker for local dev)

### C. Asynchronous Log Distributor
- Pops log packets from Redis
- Distributes to analyzers based on weights
- Use asyncio, HTTPX

### D. Log Analyzer Health Check
- Periodically checks health of each analyzer via `GET /health`
- Exclude unhealthy analyzers from distribution

### E. Analyzer Configuration
- Store analyzer endpoints and weights in config or env vars

### F. Log Analyzer Context (for testing)
- Simple FastAPI servers with `/analyze` and `/health` endpoints

## 3. Steps to Build

1. Set up FastAPI server with `/ingest` endpoint
2. Implement Redis queue interface (`RPUSH`, `BLPOP`)
3. Build async log distributor (background task)
4. Implement analyzer health check
5. Add configuration management
6. (Optional) Build dummy log analyzers for testing
7. Write tests and validate end-to-end

## 4. Tech Stack
- Python 3.9+
- FastAPI, Uvicorn
- Redis, redis-py
- HTTPX
- Pydantic
- Docker (optional)

## 5. Example Flow
1. Agent → `POST /ingest` (FastAPI)
2. FastAPI → `RPUSH` to Redis
3. Distributor → `BLPOP` from Redis
4. Distributor → `POST /analyze` (to analyzer, weighted)
5. Distributor ← `GET /health` (periodic health check) 