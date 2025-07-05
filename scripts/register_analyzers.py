#!/usr/bin/env python3
"""
Script to register analyzers with the distributor
"""
import asyncio
import httpx
import json
import time
from typing import List, Dict

# Analyzer configurations for Docker Compose
ANALYZERS = [
    {
        "id": "analyzer1",
        "name": "analyzer1", 
        "endpoint": "http://analyzer1:9001/logs",
        "health_check_url": "http://analyzer1:9001/health",
        "weight": 1.0,
        "status": "online"
    },
    {
        "id": "analyzer2",
        "name": "analyzer2",
        "endpoint": "http://analyzer2:9002/logs", 
        "health_check_url": "http://analyzer2:9002/health",
        "weight": 2.0,
        "status": "online"
    },
    {
        "id": "analyzer3", 
        "name": "analyzer3",
        "endpoint": "http://analyzer3:9003/logs",
        "health_check_url": "http://analyzer3:9003/health", 
        "weight": 1.0,
        "status": "online"
    }
]

async def register_analyzers(distributor_url: str = "http://distributor:8001"):
    """Register all analyzers with the distributor"""
    async with httpx.AsyncClient() as client:
        for analyzer in ANALYZERS:
            try:
                response = await client.post(
                    f"{distributor_url}/analyzers",
                    json=analyzer,
                    timeout=10.0
                )
                if response.status_code == 200:
                    print(f"✅ Successfully registered {analyzer['name']}")
                else:
                    print(f"❌ Failed to register {analyzer['name']}: {response.status_code}")
            except Exception as e:
                print(f"❌ Error registering {analyzer['name']}: {e}")

async def wait_for_distributor(distributor_url: str = "http://distributor:8001", max_retries: int = 30):
    """Wait for distributor to be ready"""
    async with httpx.AsyncClient() as client:
        for i in range(max_retries):
            try:
                response = await client.get(f"{distributor_url}/health", timeout=5.0)
                if response.status_code == 200:
                    print("✅ Distributor is ready!")
                    return True
            except Exception:
                pass
            
            print(f"⏳ Waiting for distributor... (attempt {i+1}/{max_retries})")
            await asyncio.sleep(2)
        
        print("❌ Distributor not ready after maximum retries")
        return False

async def main():
    """Main function"""
    print("🚀 Starting analyzer registration...")
    
    # Wait for distributor to be ready
    if not await wait_for_distributor():
        return
    
    # Register analyzers
    await register_analyzers()
    
    # Show current analyzers
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://distributor:8001/analyzers", timeout=10.0)
            if response.status_code == 200:
                analyzers = response.json()
                print("\n📊 Current analyzer configuration:")
                print(json.dumps(analyzers, indent=2))
        except Exception as e:
            print(f"❌ Error getting analyzer status: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 