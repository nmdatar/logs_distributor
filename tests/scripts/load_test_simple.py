#!/usr/bin/env python3
"""
Simple load testing script for the log ingestor
"""
import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import List

async def send_log_packet(client: httpx.AsyncClient, source: str, message_count: int = 1):
    """Send a log packet to the ingestor"""
    messages = []
    for i in range(message_count):
        messages.append({
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": f"Load test message {i+1} from {source}"
        })
    
    packet = {
        "source": source,
        "messages": messages
    }
    
    try:
        response = await client.post(
            "http://localhost:8000/logs",
            json=packet,
            timeout=10.0
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending packet: {e}")
        return False

async def load_test(concurrent_users: int = 10, requests_per_user: int = 100, delay: float = 0.1):
    """Run a load test"""
    print(f"🚀 Starting load test: {concurrent_users} users, {requests_per_user} requests each")
    print(f"📊 Total requests: {concurrent_users * requests_per_user}")
    
    start_time = time.time()
    success_count = 0
    error_count = 0
    
    async def user_worker(user_id: int):
        nonlocal success_count, error_count
        async with httpx.AsyncClient() as client:
            for i in range(requests_per_user):
                success = await send_log_packet(client, f"user_{user_id}", 1)
                if success:
                    success_count += 1
                else:
                    error_count += 1
                
                if delay > 0:
                    await asyncio.sleep(delay)
    
    # Create tasks for all users
    tasks = [user_worker(i) for i in range(concurrent_users)]
    
    # Run all tasks concurrently
    await asyncio.gather(*tasks)
    
    end_time = time.time()
    duration = end_time - start_time
    total_requests = concurrent_users * requests_per_user
    
    print(f"\n📈 Load Test Results:")
    print(f"⏱️  Duration: {duration:.2f} seconds")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {error_count}")
    print(f"📊 Success Rate: {(success_count/total_requests)*100:.1f}%")
    print(f"🚀 Requests/sec: {total_requests/duration:.1f}")

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple load test for log ingestor")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--requests", type=int, default=100, help="Requests per user")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests (seconds)")
    
    args = parser.parse_args()
    
    await load_test(args.users, args.requests, args.delay)

if __name__ == "__main__":
    asyncio.run(main()) 