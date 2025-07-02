# Logs Distributor

A high-performance log distribution system built with FastAPI, Redis, and async HTTP clients. The system consists of three main components:

1. **Logs Ingestor** - Accepts log packets from emitters and stores them in Redis queue
2. **Logs Distributor** - Reads from Redis queue and distributes logs to analyzers based on weights
3. **Analyzers** - HTTP endpoints that receive and process log packets

## Features

- **Async Log Processing**: High-performance asynchronous log processing
- **Redis Storage**: Persistent storage of log packets with configurable TTL
- **Weight-based Distribution**: Route logs to analyzers based on configurable weights
- **Health Monitoring**: Built-in health checks for analyzers with automatic status updates
- **HTTP API**: RESTful API for submitting logs and managing analyzers
- **CORS Support**: Cross-origin resource sharing enabled
- **Configurable**: Environment-based configuration

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   Log       │───▶│   Logs       │───▶│   Redis     │───▶│   Logs       │
│  Emitters   │    │  Ingestor    │    │   Queue     │    │ Distributor  │
│             │    │  (Port 8000) │    │             │    │ (Port 8001)  │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                                                                    │
                                                                    ▼
                                                           ┌──────────────┐
                                                           │   Analyzers  │
                                                           │ (Port 9001+) │
                                                           └──────────────┘
```

### Service Separation Benefits:
- **Scalability**: Each service can be scaled independently
- **Fault Tolerance**: If one service fails, the other continues working
- **Load Distribution**: Ingestor handles high-volume ingestion, Distributor handles routing
- **Flexibility**: Different deployment strategies for each service
- **Weight-based Routing**: Distribute load across analyzers based on their capacity

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd logs_distributor
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Redis** (make sure Redis is running):
   ```bash
   # On macOS with Homebrew
   brew services start redis
   
   # On Ubuntu/Debian
   sudo systemctl start redis
   
   # Or run Redis in Docker
   docker run -d -p 6379:6379 redis:alpine
   ```

## Usage

### Starting the Services

#### Start Ingestor (Port 8000):
```bash
source venv/bin/activate && PYTHONPATH=. python scripts/start_ingestor.py
```

#### Start Distributor (Port 8001):
```bash
source venv/bin/activate && PYTHONPATH=. python scripts/start_distributor.py
```

#### Start Analyzer Stubs (for testing):
```bash
# Start analyzer 1 (Port 9001)
source venv/bin/activate && PYTHONPATH=. python scripts/start_analyzer_stub.py --id analyzer1 --name analyzer1 --port 9001

# Start analyzer 2 (Port 9002)
source venv/bin/activate && PYTHONPATH=. python scripts/start_analyzer_stub.py --id analyzer2 --name analyzer2 --port 9002
```

#### Start All Services (Development):
```bash
# Terminal 1 - Ingestor
source venv/bin/activate && PYTHONPATH=. python scripts/start_ingestor.py

# Terminal 2 - Distributor
source venv/bin/activate && PYTHONPATH=. python scripts/start_distributor.py

# Terminal 3 - Analyzer 1
source venv/bin/activate && PYTHONPATH=. python scripts/start_analyzer_stub.py --id analyzer1 --name analyzer1 --port 9001

# Terminal 4 - Analyzer 2
source venv/bin/activate && PYTHONPATH=. python scripts/start_analyzer_stub.py --id analyzer2 --name analyzer2 --port 9002
```

### Environment Variables

#### Ingestor Service:
- `INGESTOR_HOST`: Server host (default: `0.0.0.0`)
- `INGESTOR_PORT`: Server port (default: `8000`)
- `INGESTOR_RELOAD`: Enable auto-reload for development (default: `false`)

#### Distributor Service:
- `DISTRIBUTOR_HOST`: Server host (default: `0.0.0.0`)
- `DISTRIBUTOR_PORT`: Server port (default: `8001`)
- `DISTRIBUTOR_RELOAD`: Enable auto-reload for development (default: `false`)

#### Shared:
- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379`)
- `LOG_QUEUE_NAME`: Redis queue name (default: `log_queue`)
- `HTTP_TIMEOUT`: HTTP request timeout in seconds (default: `30`)

### API Endpoints

#### Ingestor Service (Port 8000)

##### Submit Logs
```http
POST /logs
Content-Type: application/json

{
  "source": "my-application",
  "messages": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "level": "INFO",
      "message": "Application started"
    },
    {
      "timestamp": "2024-01-15T10:30:01Z",
      "level": "ERROR",
      "message": "Database connection failed"
    }
  ]
}
```

##### Retrieve Stored Logs
```http
GET /logs?source={source}&limit={limit}

# Example: Get logs from specific source
GET /logs?source=my-application&limit=50
```

##### Queue Status
```http
GET /queue/status
```

##### Health Check
```http
GET /health
```

#### Distributor Service (Port 8001)

##### Add Analyzer
```http
POST /analyzers
Content-Type: application/json

{
  "id": "analyzer1",
  "name": "Primary Analyzer",
  "endpoint": "http://localhost:9001/analyze",
  "weight": 3,
  "health_check_url": "http://localhost:9001/health"
}
```

##### Remove Analyzer
```http
DELETE /analyzers/{analyzer_id}

# Example: Remove analyzer1
DELETE /analyzers/analyzer1
```

##### Get Current Analyzers
```http
GET /analyzers
```

##### Get Distribution Statistics
```http
GET /analyzers/stats
```

##### Queue Status
```http
GET /queue/status
```

##### Health Check
```http
GET /health
```

#### Analyzer Stub Endpoints (Port 9001+)

##### Health Check
```http
GET /health
```

##### Receive Log Packets
```http
POST /analyze
Content-Type: application/json

{
  "source": "my-application",
  "messages": [...]
}
```

##### Get Statistics
```http
GET /stats
```

### Testing

Run the test script to verify the complete system:

```bash
source venv/bin/activate && PYTHONPATH=. python scripts/test_weight_distribution.py
```

**Prerequisites**: 
- Redis must be running
- Ingestor (port 8000) and Distributor (port 8001) services must be running
- At least one analyzer stub should be running

### Example Workflow

1. **Start all services** (see above)

2. **Add analyzers to the distributor**:
```bash
# Add analyzer 1 (60% weight)
curl -X POST http://localhost:8001/analyzers \
  -H "Content-Type: application/json" \
  -d '{
    "id": "analyzer1",
    "name": "Analyzer 1",
    "endpoint": "http://localhost:9001/analyze",
    "weight": 3,
    "health_check_url": "http://localhost:9001/health"
  }'

# Add analyzer 2 (40% weight)
curl -X POST http://localhost:8001/analyzers \
  -H "Content-Type: application/json" \
  -d '{
    "id": "analyzer2",
    "name": "Analyzer 2",
    "endpoint": "http://localhost:9002/analyze",
    "weight": 2,
    "health_check_url": "http://localhost:9002/health"
  }'
```

3. **Send log packets**:
```bash
curl -X POST http://localhost:8000/logs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test_client",
    "messages": [
      {
        "timestamp": "2024-01-15T10:30:00Z",
        "level": "INFO",
        "message": "Test log message"
      }
    ]
  }'
```

4. **Check distribution statistics**:
```bash
curl http://localhost:8001/analyzers/stats
```

5. **Check analyzer statistics**:
```bash
curl http://localhost:9001/stats
curl http://localhost:9002/stats
```

### Additional Scripts

The `scripts/` directory contains several utility scripts:

- **`start_analyzer_stub.py`**: Start analyzer stub for testing
- **`test_weight_distribution.py`**: Test weight-based distribution
- **`load_test.py`**: Performance testing with concurrent requests
- **`monitor_service.py`**: Continuous service monitoring

For detailed information about all available scripts, see `scripts/README.md`.

## Data Models

### LogMessage
```python
class LogMessage(BaseModel):
    timestamp: str  # ISO8601 format
    level: str      # INFO, WARNING, ERROR, DEBUG, CRITICAL
    message: str
```

### LogPacket
```python
class LogPacket(BaseModel):
    source: str
    messages: List[LogMessage]
```

### Analyzer
```python
class Analyzer(BaseModel):
    id: str
    name: str
    endpoint: str
    weight: int
    status: AnalyzerStatus = AnalyzerStatus.OFFLINE
    health_check_url: str
    total_messages_processed: int = 0
```

## Example Usage

### Python Client
```python
import httpx
from datetime import datetime

async def send_logs():
    async with httpx.AsyncClient() as client:
        # Add analyzer
        analyzer_data = {
            "id": "analyzer1",
            "name": "Primary Analyzer",
            "endpoint": "http://localhost:9001/analyze",
            "weight": 3,
            "health_check_url": "http://localhost:9001/health"
        }
        await client.post("http://localhost:8001/analyzers", json=analyzer_data)
        
        # Send logs
        log_data = {
            "source": "my-app",
            "messages": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "message": "Something went wrong"
                }
            ]
        }
        
        response = await client.post("http://localhost:8000/logs", json=log_data)
        print(response.json())
```

### cURL Example
```bash
# Add analyzer
curl -X POST "http://localhost:8001/analyzers" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "analyzer1",
    "name": "Primary Analyzer",
    "endpoint": "http://localhost:9001/analyze",
    "weight": 3,
    "health_check_url": "http://localhost:9001/health"
  }'

# Send logs
curl -X POST "http://localhost:8000/logs" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "my-app",
    "messages": [
      {
        "timestamp": "2024-01-15T10:30:00Z",
        "level": "ERROR",
        "message": "Database connection failed"
      }
    ]
  }'
```

## Development

### Project Structure
```
logs_distributor/
├── app/
│   ├── __init__.py
│   ├── models.py              # Pydantic data models
│   ├── ingestor.py            # Log ingestion logic
│   ├── distributor.py         # Log distribution logic
│   ├── analyzer_stub.py       # Analyzer stub implementation
│   ├── ingestor_app.py        # Ingestor FastAPI application
│   └── distributor_app.py     # Distributor FastAPI application
├── scripts/
│   ├── start_ingestor.py      # Ingestor startup script
│   ├── start_distributor.py   # Distributor startup script
│   ├── start_analyzer_stub.py # Analyzer stub startup script
│   ├── test_weight_distribution.py # Weight distribution testing
│   ├── load_test.py           # Performance testing script
│   ├── monitor_service.py     # Service monitoring script
│   └── README.md              # Scripts documentation
├── requirements.txt           # Python dependencies
└── README.md
```

### Running in Development Mode
```bash
# Terminal 1 - Ingestor with auto-reload
export INGESTOR_RELOAD=true
source venv/bin/activate && PYTHONPATH=. python scripts/start_ingestor.py

# Terminal 2 - Distributor with auto-reload
export DISTRIBUTOR_RELOAD=true
source venv/bin/activate && PYTHONPATH=. python scripts/start_distributor.py

# Terminal 3 - Analyzer stub
source venv/bin/activate && PYTHONPATH=. python scripts/start_analyzer_stub.py --id analyzer1 --name analyzer1 --port 9001
```

## Monitoring

The service includes built-in logging and health checks:

- Application logs are written to stdout
- Health endpoint at `/health` for all services
- Redis connection status monitoring
- HTTP distribution success/failure tracking
- Analyzer health monitoring with automatic status updates
- Weight-based distribution statistics

## Scaling

The service is designed to be horizontally scalable:

- Stateless design allows multiple instances
- Redis provides shared storage
- Async processing handles high throughput
- Configurable timeouts and retries
- Weight-based load distribution across analyzers
- Automatic health monitoring and failover

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license here]