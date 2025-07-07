# Logs Distributor

A high-performance log distribution system built with FastAPI, Redis, and async HTTP clients. The system distributes log packets to multiple analyzers based on configurable weights.

## Architecture

### Basic Architecture
```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   JMeter    │───▶│   Logs       │───▶│   Redis     │───▶│   Logs       │
│   Load      │    │  Ingestor    │    │   Queue     │    │ Distributor  │
│  Generator  │    │  (Port 8000) │    │             │    │ (Port 8001)  │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                                                                    │
                                                                    ▼
                                                           ┌──────────────┐
                                                           │   Analyzers  │
                                                           │ (Port 9001+) │
                                                           └──────────────┘
```

### Load Balanced Architecture
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   JMeter    │───▶│   Nginx     │───▶│  Ingestors  │───▶│   Redis     │
│   Load      │    │   Load      │    │ (3x Port    │    │   Queue     │
│  Generator  │    │  Balancer   │    │  8001-8003) │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                    │
                                                                    ▼
                                                           ┌─────────────┐
                                                           │Distributors │
                                                           │(3x Port     │
                                                           │ 8001-8003)  │
                                                                    │
                                                                    ▼
                                                           ┌─────────────┐
                                                           │   Analyzers │
                                                           │ (Port 9001+)│
                                                           └─────────────┘
```

## Project Structure

```
logs_distributor/
├── app/                          # Main application code
│   ├── __init__.py
│   ├── models.py                 # Data models (LogPacket, Analyzer, etc.)
│   ├── ingestor.py               # Log ingestion logic
│   ├── distributor.py            # Log distribution logic
│   ├── analyzer_stub.py          # Analyzer stub implementation
│   ├── ingestor_app.py           # Ingestor FastAPI application
│   ├── distributor_app.py        # Distributor FastAPI application
│   └── main.py                   # Main entry point
├── scripts/                      # Utility scripts
│   ├── start_ingestor.py         # Start ingestor service
│   ├── start_distributor.py      # Start distributor service
│   ├── start_analyzer_stub.py    # Start analyzer stub
│   ├── register_analyzers.py     # Register analyzers with distributor
│   ├── monitor_service.py        # Monitor service health
│   └── manage_analyzers.py       # Manage analyzer registration
├── tests/                        # Test files and data
│   ├── jmeter/                   # JMeter test plans
│   │   ├── load_test.jmx         # Basic load test
│   │   └── load_test_scalable.jmx # Scalable load test
│   └── scripts/                  # Test scripts
│       ├── load_test_simple.py   # Simple Python load test
│       └── test_weight_accuracy.py # Test weight distribution accuracy
├── results/                      # JMeter test results
├── docker-compose.yml            # Docker Compose configuration
├── docker-compose.final.yml      # Scaled Docker compose configuration
├── nginx.conf                    # Load balancing config
├── Dockerfile                    # Docker image definition
├── requirements.txt              # Python dependencies
├── run.py                        # Alternative entry point
└── README.md                     # This file
```

## Quick Start with Docker Compose

The system provides two Docker Compose configurations for different scaling needs:

### Basic Setup (Single Instance)
```bash
docker-compose up -d
```

This starts:
- **Redis** (port 6379)
- **Ingestor** (port 8000)
- **Distributor** (port 8001)
- **3 Analyzers** (ports 9001, 9002, 9003)
- **JMeter** (load generator)

### Load Balanced Setup (Horizontal Scaling)
```bash
docker-compose -f docker-compose.final.yml up -d
```

This starts:
- **Nginx Load Balancer** (port 80)
- **3 Ingestors** (ports 8001, 8002, 8003)
- **3 Distributors** (reading from same Redis queue)
- **Redis** (port 6379)
- **3 Analyzers** (ports 9001, 9002, 9003)
- **JMeter** (load generator)

**Load Balancing Features:**
- Round-robin distribution across ingestor instances
- Health checks and automatic failover
- Rate limiting and connection pooling
- Multiple distributors for parallel processing

### 2. Register Analyzers
```bash
# For basic setup
docker-compose exec distributor python scripts/register_analyzers.py

# For load balanced setup
docker-compose -f docker-compose.final.yml exec distributor-1 python scripts/register_analyzers_multi.py
```

### 3. Run Load Test
```bash
# Basic setup - Run JMeter test directly
docker-compose exec jmeter jmeter -n -t /tests/jmeter/load_test_scalable.jmx -l /results/results.jtl

# Load balanced setup - Run JMeter test
docker-compose -f docker-compose.final.yml exec jmeter jmeter -n -t /tests/jmeter/load_test_scalable.jmx -l /results/results.jtl

# Or use the shell script for different load scenarios
./scripts/run_load_test.sh light    # Light load
./scripts/run_load_test.sh medium   # Medium load
./scripts/run_load_test.sh heavy    # Heavy load
./scripts/run_load_test.sh stress   # Stress test
```

### 4. Check Results
```bash
# Basic setup - Check distributor stats
curl http://localhost:8001/analyzers/stats

# Load balanced setup - Check load balancer status
curl http://localhost/nginx_status

# Check individual analyzer stats
curl http://localhost:9001/stats
curl http://localhost:9002/stats
curl http://localhost:9003/stats

# View JMeter results
open results/index.html  # macOS
# or manually open results/index.html in your browser
```

### 5. Stop Services
```bash
# Basic setup
docker-compose down

# Load balanced setup
docker-compose -f docker-compose.final.yml down
```

## Manual Setup (Without Docker)

### Prerequisites
- Python 3.8+
- Redis server

### 1. Setup Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Redis (if not already running)
# macOS: brew services start redis
# Ubuntu: sudo systemctl start redis
# Or: docker run -d -p 6379:6379 redis:alpine
```

### 2. Start Services
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

### 3. Register Analyzers
```bash
source venv/bin/activate && PYTHONPATH=. python scripts/register_analyzers.py
```

### 4. Run Tests
```bash
# Simple Python load test
source venv/bin/activate && PYTHONPATH=. python tests/scripts/load_test_simple.py

# Test weight distribution accuracy
source venv/bin/activate && PYTHONPATH=. python tests/scripts/test_weight_accuracy.py
```

## Load Testing

### JMeter Tests
The project includes JMeter test plans for performance testing:

- **`tests/jmeter/load_test.jmx`** - Basic load test
- **`tests/jmeter/load_test_scalable.jmx`** - Scalable test with configurable parameters

#### Running JMeter Tests
```bash
# Using Docker Compose (recommended)
docker-compose exec jmeter jmeter -n -t /tests/jmeter/load_test_scalable.jmx -l /results/results.jtl

# Using shell script for different scenarios
./scripts/run_load_test.sh light    # 10 users, 10 seconds
./scripts/run_load_test.sh medium   # 50 users, 30 seconds
./scripts/run_load_test.sh heavy    # 100 users, 60 seconds
./scripts/run_load_test.sh stress   # 200 users, 120 seconds
```

### Python Load Tests
For simpler testing, use the Python load test script:
```bash
source venv/bin/activate && PYTHONPATH=. python tests/scripts/load_test_simple.py
```

## API Endpoints

### Ingestor (Port 8000)
- `POST /logs` - Submit log packets
- `GET /logs` - Retrieve stored logs
- `GET /queue/status` - Queue status
- `GET /health` - Health check

### Distributor (Port 8001)
- `POST /analyzers` - Add analyzer
- `DELETE /analyzers/{id}` - Remove analyzer
- `GET /analyzers` - List analyzers
- `GET /analyzers/stats` - Distribution statistics
- `GET /queue/status` - Queue status
- `GET /health` - Health check

### Analyzers (Port 9001+)
- `POST /analyze` - Receive log packets
- `GET /stats` - Processing statistics
- `GET /health` - Health check

## Example Usage

### Submit Logs
```bash
curl -X POST http://localhost:8000/logs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "my-app",
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
  }'
```

### Add Analyzer
```bash
curl -X POST http://localhost:8001/analyzers \
  -H "Content-Type: application/json" \
  -d '{
    "id": "analyzer1",
    "name": "Primary Analyzer",
    "endpoint": "http://localhost:9001/analyze",
    "weight": 3,
    "health_check_url": "http://localhost:9001/health"
  }'
```

### Check Statistics
```bash
# Distributor stats
curl http://localhost:8001/analyzers/stats

# Individual analyzer stats
curl http://localhost:9001/stats
```

## Configuration

### Environment Variables
- `REDIS_URL` - Redis connection URL (default: `redis://localhost:6379`)
- `LOG_QUEUE_NAME` - Redis queue name (default: `log_queue`)
- `HTTP_TIMEOUT` - HTTP request timeout (default: `30`)

### Docker Compose Configuration

**`docker-compose.yml`** - Basic single-instance setup:
- Service ports and networking
- Volume mounts for test data and results
- Environment variables
- Service dependencies and restart policies

**`docker-compose.final.yml`** - Load balanced horizontal scaling:
- Nginx load balancer with health checks
- Multiple ingestor and distributor instances
- Round-robin distribution and failover
- Rate limiting and connection pooling

## Troubleshooting

### Common Issues

1. **JMeter container fails to start**
   - Check if the results directory is empty
   - Reduce load parameters in the test plan

2. **Analyzers not receiving logs**
   - Ensure analyzers are registered with the distributor
   - Check analyzer health status
   - Verify network connectivity between services

3. **Redis connection errors**
   - Ensure Redis is running and accessible
   - Check Redis URL configuration

4. **Port conflicts**
   - Verify no other services are using the required ports
   - Modify port mappings in docker-compose.yml if needed

### Debugging
```bash
# View service logs
docker-compose logs ingestor
docker-compose logs distributor
docker-compose logs analyzer1

# Check service status
docker-compose ps

# Restart specific service
docker-compose restart distributor
```

## Development

### Adding New Features
1. Modify the appropriate service in `app/`
2. Update tests in `tests/`
3. Test with load tests
4. Update documentation

## License

This project is open source and available under the MIT License.