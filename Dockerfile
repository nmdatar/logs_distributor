FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Install the package in development mode
RUN pip install -e .

# Expose default ports
EXPOSE 8000 8001 9001 9002 9003

# Default command (can be overridden in docker-compose.yml)
CMD ["python", "run.py"] 