#!/usr/bin/env python3
"""
Script to dynamically manage analyzers
"""
import asyncio
import httpx
import json
import argparse
import sys
from typing import Dict

DISTRIBUTOR_URL = "http://localhost:8001"

async def add_analyzer(analyzer_config: Dict):
    """Add a new analyzer"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{DISTRIBUTOR_URL}/analyzers",
                json=analyzer_config,
                timeout=10.0
            )
            if response.status_code == 200:
                print(f"✅ Successfully added analyzer: {analyzer_config['name']}")
                return True
            else:
                print(f"❌ Failed to add analyzer: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error adding analyzer: {e}")
            return False

async def remove_analyzer(analyzer_id: str):
    """Remove an analyzer"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                f"{DISTRIBUTOR_URL}/analyzers/{analyzer_id}",
                timeout=10.0
            )
            if response.status_code == 200:
                print(f"✅ Successfully removed analyzer: {analyzer_id}")
                return True
            else:
                print(f"❌ Failed to remove analyzer: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error removing analyzer: {e}")
            return False

async def list_analyzers():
    """List all current analyzers"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{DISTRIBUTOR_URL}/analyzers", timeout=10.0)
            if response.status_code == 200:
                analyzers = response.json()
                print("\n📊 Current Analyzers:")
                print(json.dumps(analyzers, indent=2))
            else:
                print(f"❌ Failed to get analyzers: {response.status_code}")
        except Exception as e:
            print(f"❌ Error getting analyzers: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Manage analyzers dynamically")
    parser.add_argument("action", choices=["add", "remove", "list"], help="Action to perform")
    parser.add_argument("--id", help="Analyzer ID (for remove)")
    parser.add_argument("--name", help="Analyzer name (for add)")
    parser.add_argument("--endpoint", help="Analyzer endpoint (for add)")
    parser.add_argument("--port", type=int, help="Analyzer port (for add)")
    parser.add_argument("--weight", type=float, default=1.0, help="Analyzer weight (for add)")
    
    args = parser.parse_args()
    
    if args.action == "list":
        await list_analyzers()
    
    elif args.action == "remove":
        if not args.id:
            print("❌ --id is required for remove action")
            sys.exit(1)
        await remove_analyzer(args.id)
    
    elif args.action == "add":
        if not all([args.id, args.name, args.port]):
            print("❌ --id, --name, and --port are required for add action")
            sys.exit(1)
        
        analyzer_config = {
            "id": args.id,
            "name": args.name,
            "endpoint": args.endpoint or f"http://{args.name}:{args.port}/logs",
            "health_check_url": f"http://{args.name}:{args.port}/health",
            "weight": args.weight,
            "status": "online"
        }
        
        await add_analyzer(analyzer_config)
        print("\n📝 To add this analyzer to Docker Compose, add this service:")
        print(f"""
  {args.name}:
    build: .
    command: python scripts/start_analyzer_stub.py --id {args.id} --name {args.name} --port {args.port}
    depends_on:
      - distributor
    ports:
      - "{args.port}:{args.port}"
        """)

if __name__ == "__main__":
    asyncio.run(main()) 