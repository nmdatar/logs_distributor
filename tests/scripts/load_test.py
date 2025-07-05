#!/usr/bin/env python3
"""
Load testing script for Logs Distributor
"""
import asyncio
import time
import random
import httpx
from datetime import datetime
from typing import List
import statistics

class LoadTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    def generate_log_messages(self, count: int) -> List[dict]:
        """Generate random log messages for testing"""
        levels = ["INFO", "WARNING", "ERROR", "DEBUG"]
        messages = [
            "Application started",
            "User login successful",
            "Database query executed",
            "API request processed",
            "Cache miss occurred",
            "Memory usage high",
            "Network timeout",
            "File upload completed",
            "Background job finished",
            "System health check passed"
        ]
        
        log_messages = []
        for i in range(count):
            log_messages.append({
                "timestamp": datetime.now().isoformat(),
                "level": random.choice(levels),
                "message": f"{random.choice(messages)} - {i}"
            })
        
        return log_messages
    
    async def send_log_packet(self, client: httpx.AsyncClient, packet_id: int) -> dict:
        """Send a single log packet and measure response time"""
        messages = self.generate_log_messages(random.randint(1, 5))
        packet = {
            "source": f"load-test-{packet_id}",
            "messages": messages
        }
        
        start_time = time.time()
        try:
            response = await client.post(f"{self.base_url}/logs", json=packet)
            end_time = time.time()
            
            return {
                "packet_id": packet_id,
                "response_time": end_time - start_time,
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "error": None
            }
        except Exception as e:
            end_time = time.time()
            return {
                "packet_id": packet_id,
                "response_time": end_time - start_time,
                "status_code": None,
                "success": False,
                "error": str(e)
            }
    
    async def run_load_test(self, num_requests: int, concurrency: int = 10):
        """Run load test with specified number of requests and concurrency"""
        print(f"🚀 Starting load test: {num_requests} requests with concurrency {concurrency}")
        print("=" * 60)
        
        # Setup test endpoints first
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"{self.base_url}/endpoints/INFO", 
                                params={"endpoint": "http://localhost:8081/logs"})
                await client.post(f"{self.base_url}/endpoints/ERROR", 
                                params={"endpoint": "http://localhost:8082/logs"})
                print("✅ Test endpoints configured")
            except Exception as e:
                print(f"⚠️  Could not configure test endpoints: {e}")
        
        # Run the load test
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            semaphore = asyncio.Semaphore(concurrency)
            
            async def send_with_semaphore(packet_id):
                async with semaphore:
                    return await self.send_log_packet(client, packet_id)
            
            tasks = [send_with_semaphore(i) for i in range(num_requests)]
            results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        self.analyze_results(results, total_time, num_requests)
    
    def analyze_results(self, results: List[dict], total_time: float, num_requests: int):
        """Analyze and display test results"""
        print("\n📊 Load Test Results")
        print("=" * 60)
        
        # Basic statistics
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        response_times = [r["response_time"] for r in successful_requests]
        
        print(f"Total Requests: {num_requests}")
        print(f"Successful: {len(successful_requests)}")
        print(f"Failed: {len(failed_requests)}")
        print(f"Success Rate: {(len(successful_requests) / num_requests) * 100:.2f}%")
        print(f"Total Time: {total_time:.2f} seconds")
        print(f"Requests per Second: {num_requests / total_time:.2f}")
        
        if response_times:
            print(f"\nResponse Time Statistics:")
            print(f"  Average: {statistics.mean(response_times):.3f} seconds")
            print(f"  Median: {statistics.median(response_times):.3f} seconds")
            print(f"  Min: {min(response_times):.3f} seconds")
            print(f"  Max: {max(response_times):.3f} seconds")
            print(f"  Standard Deviation: {statistics.stdev(response_times):.3f} seconds")
        
        if failed_requests:
            print(f"\nFailed Requests ({len(failed_requests)}):")
            for req in failed_requests[:5]:  # Show first 5 failures
                print(f"  Packet {req['packet_id']}: {req['error']}")
            if len(failed_requests) > 5:
                print(f"  ... and {len(failed_requests) - 5} more")

async def main():
    """Main function to run load tests"""
    print("🔧 Logs Distributor Load Tester")
    print("=" * 60)
    
    # Configuration
    base_url = "http://localhost:8000"
    num_requests = 100
    concurrency = 10
    
    # Check if service is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ Service is running")
            else:
                print("❌ Service health check failed")
                return
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        print("💡 Make sure the service is running: python scripts/start_server.py")
        return
    
    # Run load test
    tester = LoadTester(base_url)
    await tester.run_load_test(num_requests, concurrency)

if __name__ == "__main__":
    print("Load testing Logs Distributor...")
    print("Make sure the service is running on localhost:8000")
    print("You can start it with: python scripts/start_server.py")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Load test interrupted by user")
    except Exception as e:
        print(f"❌ Load test failed: {e}") 