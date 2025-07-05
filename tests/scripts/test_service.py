#!/usr/bin/env python3
"""
Test script for the Logs Ingestor and Distributor services
"""
import asyncio
import httpx
from datetime import datetime
from app.models import LogPacket, LogMessage

async def test_services():
    """Test both ingestor and distributor services"""
    
    # Sample log messages
    messages = [
        LogMessage(
            timestamp=datetime.now().isoformat(),
            level="INFO",
            message="Application started successfully"
        ),
        LogMessage(
            timestamp=datetime.now().isoformat(),
            level="WARNING",
            message="High memory usage detected"
        ),
        LogMessage(
            timestamp=datetime.now().isoformat(),
            level="ERROR",
            message="Database connection failed"
        )
    ]
    
    # Create a log packet
    packet = LogPacket(
        source="test-application",
        messages=messages
    )
    
    # Test the services
    async with httpx.AsyncClient() as client:
        ingestor_url = "http://localhost:8000"
        distributor_url = "http://localhost:8001"
        
        print("Testing Logs Ingestor and Distributor Services...")
        
        # 1. Test Ingestor Health
        print("\n1. Testing Ingestor Health...")
        try:
            response = await client.get(f"{ingestor_url}/health")
            print(f"✅ Ingestor Health: {response.json()}")
        except Exception as e:
            print(f"❌ Ingestor Health Check Failed: {e}")
            return
        
        # 2. Test Distributor Health
        print("\n2. Testing Distributor Health...")
        try:
            response = await client.get(f"{distributor_url}/health")
            print(f"✅ Distributor Health: {response.json()}")
        except Exception as e:
            print(f"❌ Distributor Health Check Failed: {e}")
            return
        
        # 3. Add analyzers to Distributor with weights
        print("\n3. Adding analyzers to Distributor with weights...")
        try:
            analyzers = [
                {
                    "id": "analyzer-1",
                    "name": "Fast Analyzer",
                    "endpoint": "http://localhost:8081/logs",
                    "weight": 0.4,
                    "health_check_url": "http://localhost:8081/health"
                },
                {
                    "id": "analyzer-2", 
                    "name": "Medium Analyzer",
                    "endpoint": "http://localhost:8082/logs",
                    "weight": 0.3,
                    "health_check_url": "http://localhost:8082/health"
                },
                {
                    "id": "analyzer-3",
                    "name": "Slow Analyzer", 
                    "endpoint": "http://localhost:8083/logs",
                    "weight": 0.2,
                    "health_check_url": "http://localhost:8083/health"
                },
                {
                    "id": "analyzer-4",
                    "name": "Backup Analyzer",
                    "endpoint": "http://localhost:8084/logs", 
                    "weight": 0.1,
                    "health_check_url": "http://localhost:8084/health"
                }
            ]
            
            for analyzer in analyzers:
                await client.post(f"{distributor_url}/analyzers", json=analyzer)
            
            print("✅ Analyzers added successfully")
        except Exception as e:
            print(f"❌ Failed to add analyzers: {e}")
        
        # 4. Get current analyzers
        print("\n4. Current Distributor analyzers:")
        try:
            response = await client.get(f"{distributor_url}/analyzers")
            print(response.json())
        except Exception as e:
            print(f"❌ Failed to get analyzers: {e}")
        
        # 5. Submit log packet to Ingestor
        print("\n5. Submitting log packet to Ingestor...")
        try:
            response = await client.post(f"{ingestor_url}/logs", json=packet.model_dump())
            result = response.json()
            print(f"✅ Ingestor Response: {result}")
        except Exception as e:
            print(f"❌ Failed to submit to Ingestor: {e}")
            return
        
        # 6. Check queue status
        print("\n6. Checking queue status...")
        try:
            ingestor_queue = await client.get(f"{ingestor_url}/queue/status")
            distributor_queue = await client.get(f"{distributor_url}/queue/status")
            print(f"✅ Ingestor Queue: {ingestor_queue.json()}")
            print(f"✅ Distributor Queue: {distributor_queue.json()}")
        except Exception as e:
            print(f"❌ Failed to get queue status: {e}")
        
        # 7. Retrieve stored logs from Ingestor
        print("\n7. Retrieving stored logs from Ingestor...")
        try:
            response = await client.get(f"{ingestor_url}/logs")
            logs = response.json()
            print(f"✅ Retrieved {len(logs)} log packets from Ingestor")
        except Exception as e:
            print(f"❌ Failed to retrieve logs: {e}")
        
        # 8. Wait a bit for distribution to process
        print("\n8. Waiting for distribution to process...")
        await asyncio.sleep(2)
        
        # 9. Check distribution statistics
        print("\n9. Checking distribution statistics...")
        try:
            stats = await client.get(f"{distributor_url}/analyzers/stats")
            print(f"✅ Distribution Stats: {stats.json()}")
        except Exception as e:
            print(f"❌ Failed to get distribution stats: {e}")
        
        # 10. Check queue status again
        print("\n10. Checking queue status after processing...")
        try:
            ingestor_queue = await client.get(f"{ingestor_url}/queue/status")
            distributor_queue = await client.get(f"{distributor_url}/queue/status")
            print(f"✅ Ingestor Queue: {ingestor_queue.json()}")
            print(f"✅ Distributor Queue: {distributor_queue.json()}")
        except Exception as e:
            print(f"❌ Failed to get queue status: {e}")

if __name__ == "__main__":
    print("Logs Ingestor and Distributor Test")
    print("Make sure all services are running:")
    print("  - Ingestor: python scripts/start_ingestor.py (port 8000)")
    print("  - Distributor: python scripts/start_distributor.py (port 8001)")
    print("  - Analyzer stubs (optional):")
    print("    python scripts/start_analyzer_stub.py --id analyzer-1 --name 'Fast Analyzer' --port 8081")
    print("    python scripts/start_analyzer_stub.py --id analyzer-2 --name 'Medium Analyzer' --port 8082")
    print("    python scripts/start_analyzer_stub.py --id analyzer-3 --name 'Slow Analyzer' --port 8083")
    print("    python scripts/start_analyzer_stub.py --id analyzer-4 --name 'Backup Analyzer' --port 8084")
    print()
    
    try:
        asyncio.run(test_services())
    except Exception as e:
        print(f"Test failed: {e}")
        print("Make sure all services are running and Redis is available") 