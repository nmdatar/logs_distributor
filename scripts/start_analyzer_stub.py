#!/usr/bin/env python3
"""
Start analyzer stub for testing weight-based distribution
"""
import uvicorn
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Start analyzer stub")
    parser.add_argument("--id", required=True, help="Analyzer ID")
    parser.add_argument("--name", required=True, help="Analyzer name")
    parser.add_argument("--port", type=int, required=True, help="Port to run on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    
    args = parser.parse_args()
    
    # Import here to avoid circular imports
    from app.analyzer_stub import create_analyzer_stub
    
    # Create analyzer stub app
    app = create_analyzer_stub(args.id, args.name, args.port)
    
    print(f"Starting Analyzer Stub: {args.name} (ID: {args.id}) on {args.host}:{args.port}")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )

if __name__ == "__main__":
    main() 