# Scripts Directory

This directory contains various utility scripts for the Logs Distributor service.

## Available Scripts

### 🚀 `start_ingestor.py`
**Purpose**: Start the Logs Ingestor FastAPI service

**Usage**:
```bash
python scripts/start_ingestor.py
```

**Environment Variables**:
- `INGESTOR_HOST`: Server host (default: `0.0.0.0`)
- `INGESTOR_PORT`: Server port (default: `8000`)
- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379`)
- `LOG_QUEUE_NAME`: Redis queue name (default: `log_queue`)
- `INGESTOR_RELOAD`: Enable auto-reload for development (default: `false`)

**Example**:
```bash
export INGESTOR_PORT=8080
export INGESTOR_RELOAD=true
python scripts/start_ingestor.py
```

### 🚀 `start_distributor.py`
**Purpose**: Start the Logs Distributor FastAPI service

**Usage**:
```bash
python scripts/start_distributor.py
```

**Environment Variables**:
- `DISTRIBUTOR_HOST`: Server host (default: `0.0.0.0`)
- `DISTRIBUTOR_PORT`: Server port (default: `8001`)
- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379`)
- `LOG_QUEUE_NAME`: Redis queue name (default: `log_queue`)
- `HTTP_TIMEOUT`: HTTP request timeout (default: `30`)
- `DISTRIBUTOR_RELOAD`: Enable auto-reload for development (default: `false`)

**Example**:
```bash
export DISTRIBUTOR_PORT=8081
export DISTRIBUTOR_RELOAD=true
python scripts/start_distributor.py
```

### 🧪 `test_service.py`
**Purpose**: Test both Logs Ingestor and Distributor services with sample data

**Usage**:
```bash
python scripts/test_service.py
```

**What it does**:
- Tests health of both services
- Adds test endpoints to Distributor
- Submits sample log packets to Ingestor
- Checks queue status on both services
- Retrieves stored logs from Ingestor
- Monitors distribution processing

**Prerequisites**: Both services must be running:
- Ingestor on `http://localhost:8000`
- Distributor on `http://localhost:8001`

### 🔧 `setup_environment.py`
**Purpose**: Automated setup of the Logs Distributor environment

**Usage**:
```bash
python scripts/setup_environment.py
```

**What it does**:
- Checks Python version compatibility
- Creates virtual environment
- Installs dependencies from `requirements.txt`
- Creates `.env` file with default configuration
- Checks Redis availability
- Provides next steps

**Example output**:
```
🚀 Setting up Logs Distributor environment...
==================================================
✅ Python 3.9.7 detected
✅ Creating virtual environment...
✅ Installing dependencies...
✅ Created .env file with default configuration
✅ Redis is running
==================================================
🎉 Setup completed!

Next steps:
1. Activate virtual environment:
   source logs_distributor/bin/activate
2. Start the service:
   python scripts/start_server.py
3. Test the service:
   python scripts/test_service.py
```

### 📊 `load_test.py`
**Purpose**: Performance testing of the Logs Distributor service

**Usage**:
```bash
python scripts/load_test.py
```

**Features**:
- Sends multiple concurrent log packets
- Measures response times
- Calculates success rates
- Provides detailed performance statistics

**Configuration** (modify in script):
- `num_requests`: Number of requests to send (default: 100)
- `concurrency`: Number of concurrent requests (default: 10)

**Example output**:
```
🔧 Logs Distributor Load Tester
============================================================
✅ Service is running
✅ Test endpoints configured
🚀 Starting load test: 100 requests with concurrency 10
============================================================

📊 Load Test Results
============================================================
Total Requests: 100
Successful: 98
Failed: 2
Success Rate: 98.00%
Total Time: 12.34 seconds
Requests per Second: 8.10

Response Time Statistics:
  Average: 0.045 seconds
  Median: 0.042 seconds
  Min: 0.023 seconds
  Max: 0.156 seconds
  Standard Deviation: 0.023 seconds
```

### 🔍 `monitor_service.py`
**Purpose**: Continuous monitoring of the Logs Distributor service

**Usage**:
```bash
# Basic monitoring (30-second intervals)
python scripts/monitor_service.py

# Custom interval and duration
python scripts/monitor_service.py --interval 60 --duration 3600

# Monitor different service URL
python scripts/monitor_service.py --url http://localhost:8080
```

**Features**:
- Continuous health checks
- Response time monitoring
- Endpoint configuration tracking
- Log count monitoring
- Metrics persistence to JSON file
- Real-time status display

**Command Line Options**:
- `--url`: Service URL (default: `http://localhost:8000`)
- `--interval`: Check interval in seconds (default: `30`)
- `--duration`: Monitoring duration in seconds (optional)

**Example output**:
```
🔍 Starting Logs Distributor Monitoring
Monitoring URL: http://localhost:8000
Check Interval: 30 seconds
Press Ctrl+C to stop
============================================================

🟢 Service Status - 2024-01-15 14:30:00
============================================================
Status: HEALTHY
Response Time: 0.023s
Configured Endpoints: 3
  INFO: 1 endpoint(s)
  ERROR: 1 endpoint(s)
  WARNING: 1 endpoint(s)
Stored Logs: 45
Uptime (last 10 checks): 100.0%
Avg Response Time (last 10): 0.025s
```

## Script Dependencies

All scripts require the following packages (installed via `requirements.txt`):
- `fastapi`
- `uvicorn`
- `redis`
- `httpx`
- `pydantic`

## Running Scripts

### Prerequisites
1. **Activate virtual environment**:
   ```bash
   source logs_distributor/bin/activate
   ```

2. **Ensure Redis is running**:
   ```bash
   # macOS
   brew services start redis
   
   # Linux
   sudo systemctl start redis
   
   # Docker
   docker run -d -p 6379:6379 redis:alpine
   ```

### Typical Workflow

1. **Setup environment** (first time only):
   ```bash
   python scripts/setup_environment.py
   ```

2. **Start both services**:
   ```bash
   # Terminal 1 - Start Ingestor
   python scripts/start_ingestor.py
   
   # Terminal 2 - Start Distributor
   python scripts/start_distributor.py
   ```

3. **Test both services**:
   ```bash
   python scripts/test_service.py
   ```

4. **Monitor performance** (optional):
   ```bash
   python scripts/monitor_service.py
   ```

5. **Load test** (optional):
   ```bash
   python scripts/load_test.py
   ```

## Troubleshooting

### Common Issues

1. **Service not starting**:
   - Check if Redis is running
   - Verify port availability
   - Check virtual environment activation

2. **Connection errors**:
   - Ensure service is running on correct host/port
   - Check firewall settings
   - Verify Redis connection

3. **Import errors**:
   - Activate virtual environment
   - Install dependencies: `pip install -r requirements.txt`

### Getting Help

- Check the main `README.md` for detailed documentation
- Review service logs for error messages
- Use the health endpoint: `GET /health`
- Monitor service with `monitor_service.py`

## Contributing

When adding new scripts:
1. Follow the existing naming convention
2. Add proper documentation
3. Include error handling
4. Update this README
5. Test thoroughly before committing 