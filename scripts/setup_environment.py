#!/usr/bin/env python3
"""
Setup script for Logs Distributor environment
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def create_virtual_environment():
    """Create virtual environment"""
    venv_name = "logs_distributor"
    if os.path.exists(venv_name):
        print(f"ℹ️  Virtual environment '{venv_name}' already exists")
        return True
    
    return run_command(f"python3 -m venv {venv_name}", "Creating virtual environment")

def install_dependencies():
    """Install Python dependencies"""
    venv_pip = "logs_distributor/bin/pip" if platform.system() != "Windows" else "logs_distributor\\Scripts\\pip"
    return run_command(f"{venv_pip} install -r requirements.txt", "Installing dependencies")

def check_redis():
    """Check if Redis is running"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running")
        return True
    except Exception as e:
        print("❌ Redis is not running or not accessible")
        print("💡 To start Redis:")
        if platform.system() == "Darwin":  # macOS
            print("   brew services start redis")
        elif platform.system() == "Linux":
            print("   sudo systemctl start redis")
        else:
            print("   Start Redis manually or use Docker: docker run -d -p 6379:6379 redis:alpine")
        return False

def create_env_file():
    """Create .env file with default configuration"""
    env_file = Path(".env")
    if env_file.exists():
        print("ℹ️  .env file already exists")
        return True
    
    env_content = """# Logs Distributor Configuration
HOST=0.0.0.0
PORT=8000
REDIS_URL=redis://localhost:6379
HTTP_TIMEOUT=30
RELOAD=false
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("✅ Created .env file with default configuration")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Logs Distributor environment...")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create .env file
    create_env_file()
    
    # Check Redis
    check_redis()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed!")
    print("\nNext steps:")
    print("1. Activate virtual environment:")
    if platform.system() != "Windows":
        print("   source logs_distributor/bin/activate")
    else:
        print("   logs_distributor\\Scripts\\activate")
    print("2. Start the service:")
    print("   python scripts/start_server.py")
    print("3. Test the service:")
    print("   python scripts/test_service.py")
    print("\nFor more information, see README.md")

if __name__ == "__main__":
    main() 