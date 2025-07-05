#!/usr/bin/env python3
"""
Script to simulate analyzer failures for testing fault tolerance
"""
import subprocess
import time
import asyncio
import httpx
import signal
import sys

def simulate_analyzer_down(port: int, duration: int = 30):
    """Simulate analyzer going down by blocking its port"""
    print(f"🔴 Simulating analyzer on port {port} going down for {duration} seconds...")
    
    # Method 1: Use iptables to block port (Linux/macOS)
    try:
        # Block incoming connections to the port
        subprocess.run([
            "sudo", "iptables", "-A", "INPUT", "-p", "tcp", 
            "--dport", str(port), "-j", "DROP"
        ], check=True)
        
        print(f"✅ Port {port} blocked. Analyzer should appear offline.")
        print(f"⏰ Will unblock in {duration} seconds...")
        
        time.sleep(duration)
        
        # Unblock the port
        subprocess.run([
            "sudo", "iptables", "-D", "INPUT", "-p", "tcp", 
            "--dport", str(port), "-j", "DROP"
        ], check=True)
        
        print(f"✅ Port {port} unblocked. Analyzer should come back online.")
        
    except subprocess.CalledProcessError:
        print("❌ Failed to block port (may need sudo privileges)")
        print("🔄 Falling back to process termination method...")
        simulate_analyzer_process_kill(port, duration)

def simulate_analyzer_process_kill(port: int, duration: int = 30):
    """Simulate analyzer failure by killing the process"""
    print(f"🔴 Simulating analyzer on port {port} failure by killing process...")
    
    # Find and kill the analyzer process
    try:
        result = subprocess.run([
            "lsof", "-ti", f":{port}"
        ], capture_output=True, text=True)
        
        if result.stdout.strip():
            pid = result.stdout.strip()
            print(f"🔄 Killing process {pid} on port {port}")
            subprocess.run(["kill", pid])
            print(f"✅ Process killed. Analyzer should appear offline.")
            print(f"⏰ Will restart in {duration} seconds...")
            
            time.sleep(duration)
            
            # Restart the analyzer (you'll need to do this manually)
            print(f"🔄 Please restart analyzer on port {port} manually:")
            print(f"   python scripts/start_analyzer_stub.py --id analyzer{port-9000} --name analyzer{port-9000} --port {port}")
            
        else:
            print(f"❌ No process found on port {port}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_fault_tolerance():
    """Test the system's fault tolerance"""
    print("🧪 Testing Fault Tolerance")
    print("=" * 40)
    
    async with httpx.AsyncClient() as client:
        # Check initial state
        print("\n1. Checking initial analyzer status...")
        response = await client.get("http://localhost:8001/analyzers")
        if response.status_code == 200:
            config = response.json()
            print(f"Online analyzers: {config['online_count']}/{config['total_count']}")
            for analyzer in config['analyzers']:
                status = "🟢" if analyzer['status'] == 'online' else "🔴"
                print(f"  {status} {analyzer['name']}: {analyzer['status']}")
        
        # Send some messages before failure
        print("\n2. Sending messages before failure...")
        for i in range(5):
            packet = {
                "source": "pre_failure_test",
                "messages": [{
                    "timestamp": "2025-07-01T12:00:00Z",
                    "level": "info",
                    "message": f"Pre-failure message {i+1}"
                }]
            }
            await client.post("http://localhost:8000/logs", json=packet)
            print(f"✅ Sent pre-failure packet {i+1}")
            await asyncio.sleep(0.5)
        
        # Simulate analyzer failure
        print("\n3. Simulating analyzer failure...")
        simulate_analyzer_down(9002, 10)  # Take down analyzer 2 for 10 seconds
        
        # Check status during failure
        print("\n4. Checking status during failure...")
        await asyncio.sleep(5)  # Wait for health check to detect failure
        
        response = await client.get("http://localhost:8001/analyzers")
        if response.status_code == 200:
            config = response.json()
            print(f"Online analyzers: {config['online_count']}/{config['total_count']}")
            for analyzer in config['analyzers']:
                status = "🟢" if analyzer['status'] == 'online' else "🔴"
                print(f"  {status} {analyzer['name']}: {analyzer['status']}")
        
        # Send messages during failure
        print("\n5. Sending messages during failure...")
        for i in range(5):
            packet = {
                "source": "during_failure_test",
                "messages": [{
                    "timestamp": "2025-07-01T12:00:00Z",
                    "level": "info",
                    "message": f"During-failure message {i+1}"
                }]
            }
            await client.post("http://localhost:8000/logs", json=packet)
            print(f"✅ Sent during-failure packet {i+1}")
            await asyncio.sleep(0.5)
        
        # Wait for recovery
        print("\n6. Waiting for analyzer recovery...")
        await asyncio.sleep(10)
        
        # Check final status
        print("\n7. Checking final status...")
        response = await client.get("http://localhost:8001/analyzers")
        if response.status_code == 200:
            config = response.json()
            print(f"Online analyzers: {config['online_count']}/{config['total_count']}")
            for analyzer in config['analyzers']:
                status = "🟢" if analyzer['status'] == 'online' else "🔴"
                print(f"  {status} {analyzer['name']}: {analyzer['status']}")
        
        # Check final distribution
        print("\n8. Checking final message distribution...")
        for port in [9001, 9002, 9003]:
            try:
                response = await client.get(f"http://localhost:{port}/stats")
                if response.status_code == 200:
                    stats = response.json()
                    print(f"  Analyzer {port}: {stats['processed_messages']} messages")
            except:
                print(f"  Analyzer {port}: unreachable")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            asyncio.run(test_fault_tolerance())
        else:
            port = int(sys.argv[1])
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            simulate_analyzer_down(port, duration)
    else:
        print("Usage:")
        print("  python tests/scripts/simulate_analyzer_failure.py <port> [duration]")
        print("  python tests/scripts/simulate_analyzer_failure.py test")
        print("\nExamples:")
        print("  python tests/scripts/simulate_analyzer_failure.py 9002 30  # Take down analyzer 2 for 30s")
        print("  python tests/scripts/simulate_analyzer_failure.py test    # Run full fault tolerance test") 