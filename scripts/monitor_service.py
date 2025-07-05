#!/usr/bin/env python3
"""
Monitoring script for Logs Distributor service
"""
import asyncio
import time
import httpx
import json
from datetime import datetime
from typing import Dict, List
import statistics

class ServiceMonitor:
    def __init__(self, base_url: str = "http://localhost:8000", interval: int = 30):
        self.base_url = base_url
        self.interval = interval
        self.metrics = {
            "health_checks": [],
            "response_times": [],
            "errors": []
        }
    
    async def check_health(self) -> Dict:
        """Check service health"""
        start_time = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                end_time = time.time()
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "error": None
                }
        except Exception as e:
            end_time = time.time()
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "status_code": None,
                "response_time": end_time - start_time,
                "error": str(e)
            }
    
    async def get_endpoints_status(self) -> Dict:
        """Get current endpoints configuration"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/endpoints")
                return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_logs_count(self) -> int:
        """Get count of stored logs"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/logs")
                logs = response.json()
                return len(logs)
        except Exception:
            return 0
    
    def print_status(self, health_check: Dict, endpoints: Dict, logs_count: int):
        """Print current service status"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Status indicator
        if health_check["status"] == "healthy":
            status_icon = "🟢"
        elif health_check["status"] == "unhealthy":
            status_icon = "🟡"
        else:
            status_icon = "🔴"
        
        print(f"\n{status_icon} Service Status - {timestamp}")
        print("=" * 60)
        print(f"Status: {health_check['status'].upper()}")
        print(f"Response Time: {health_check['response_time']:.3f}s")
        
        if health_check["error"]:
            print(f"Error: {health_check['error']}")
        
        # Endpoints summary
        if "error" not in endpoints:
            total_endpoints = sum(len(endpoints.get(level, [])) for level in endpoints)
            print(f"Configured Endpoints: {total_endpoints}")
            
            for level, urls in endpoints.items():
                if urls:
                    print(f"  {level}: {len(urls)} endpoint(s)")
        else:
            print(f"Endpoints Error: {endpoints['error']}")
        
        print(f"Stored Logs: {logs_count}")
        
        # Metrics summary
        if self.metrics["health_checks"]:
            recent_checks = self.metrics["health_checks"][-10:]  # Last 10 checks
            healthy_count = sum(1 for check in recent_checks if check["status"] == "healthy")
            uptime_percentage = (healthy_count / len(recent_checks)) * 100
            print(f"Uptime (last 10 checks): {uptime_percentage:.1f}%")
        
        if self.metrics["response_times"]:
            recent_times = self.metrics["response_times"][-10:]
            avg_time = statistics.mean(recent_times)
            print(f"Avg Response Time (last 10): {avg_time:.3f}s")
    
    def save_metrics(self):
        """Save metrics to file"""
        try:
            with open("monitoring_metrics.json", "w") as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save metrics: {e}")
    
    async def run_monitoring(self, duration: int = None):
        """Run continuous monitoring"""
        print("🔍 Starting Logs Distributor Monitoring")
        print(f"Monitoring URL: {self.base_url}")
        print(f"Check Interval: {self.interval} seconds")
        if duration:
            print(f"Duration: {duration} seconds")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        start_time = time.time()
        check_count = 0
        
        try:
            while True:
                # Check if duration exceeded
                if duration and (time.time() - start_time) > duration:
                    print(f"\n⏰ Monitoring completed after {duration} seconds")
                    break
                
                # Perform health check
                health_check = await self.check_health()
                self.metrics["health_checks"].append(health_check)
                
                # Get additional metrics
                endpoints = await self.get_endpoints_status()
                logs_count = await self.get_logs_count()
                
                # Store response time
                if health_check["response_time"]:
                    self.metrics["response_times"].append(health_check["response_time"])
                
                # Store errors
                if health_check["error"]:
                    self.metrics["errors"].append({
                        "timestamp": health_check["timestamp"],
                        "error": health_check["error"]
                    })
                
                # Print status
                self.print_status(health_check, endpoints, logs_count)
                
                check_count += 1
                
                # Save metrics periodically
                if check_count % 10 == 0:
                    self.save_metrics()
                
                # Wait for next check
                await asyncio.sleep(self.interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        
        # Final summary
        print("\n📊 Monitoring Summary")
        print("=" * 60)
        print(f"Total Checks: {check_count}")
        print(f"Duration: {time.time() - start_time:.1f} seconds")
        
        if self.metrics["health_checks"]:
            total_checks = len(self.metrics["health_checks"])
            healthy_checks = sum(1 for check in self.metrics["health_checks"] if check["status"] == "healthy")
            print(f"Overall Uptime: {(healthy_checks / total_checks) * 100:.1f}%")
        
        if self.metrics["response_times"]:
            avg_response_time = statistics.mean(self.metrics["response_times"])
            print(f"Average Response Time: {avg_response_time:.3f}s")
        
        if self.metrics["errors"]:
            print(f"Total Errors: {len(self.metrics['errors'])}")
        
        # Save final metrics
        self.save_metrics()
        print("✅ Metrics saved to monitoring_metrics.json")

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor Logs Distributor service")
    parser.add_argument("--url", default="http://localhost:8000", help="Service URL")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--duration", type=int, help="Monitoring duration in seconds")
    
    args = parser.parse_args()
    
    monitor = ServiceMonitor(args.url, args.interval)
    await monitor.run_monitoring(args.duration)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")
    except Exception as e:
        print(f"❌ Monitoring failed: {e}") 