#!/usr/bin/env python3
"""
Register analyzers with multiple distributors
"""
import asyncio
import httpx
import os
from app.models import Analyzer

async def register_with_all_distributors():
    analyzers = [
        Analyzer(
            id="analyzer1",
            name="Analyzer 1",
            endpoint="http://analyzer1:9001/analyze",
            weight=3,
            health_check_url="http://analyzer1:9001/health"
        ),
        Analyzer(
            id="analyzer2", 
            name="Analyzer 2",
            endpoint="http://analyzer2:9002/analyze",
            weight=2,
            health_check_url="http://analyzer2:9002/health"
        ),
        Analyzer(
            id="analyzer3",
            name="Analyzer 3", 
            endpoint="http://analyzer3:9003/analyze",
            weight=1,
            health_check_url="http://analyzer3:9003/health"
        )
    ]
    
    # Register with each distributor
    distributor_urls = [
        "http://distributor-1:8001",
        "http://distributor-2:8001", 
        "http://distributor-3:8001"
    ]
    
    async with httpx.AsyncClient() as client:
        for distributor_url in distributor_urls:
            print(f"Registering analyzers with {distributor_url}")
            for analyzer in analyzers:
                try:
                    response = await client.post(
                        f"{distributor_url}/analyzers",
                        json=analyzer.model_dump()
                    )
                    if response.status_code == 200:
                        print(f"✅ Registered {analyzer.name} with {distributor_url}")
                    else:
                        print(f"❌ Failed to register {analyzer.name} with {distributor_url}: {response.status_code}")
                except Exception as e:
                    print(f"❌ Error registering {analyzer.name} with {distributor_url}: {e}")

if __name__ == "__main__":
    asyncio.run(register_with_all_distributors()) 