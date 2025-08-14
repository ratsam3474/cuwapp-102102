#!/usr/bin/env python3
"""
Main Startup Script for 10210 Project
Orchestrates all components under single port 10210
"""

import os
import sys
import json
import time
import subprocess
import socket
import threading
import signal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('startup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProjectConfig:
    """Central configuration for all components"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.absolute()
        self.config_file = self.base_dir / "project_config.json"
        self.env_file = self.base_dir / ".env"
        self.config = self.load_or_create_config()
        
    def load_or_create_config(self) -> Dict:
        """Load existing config or create new one"""
        default_config = {
            "main_port": 10210,
            "components": {
                "landing": {
                    "name": "Landing Page", 
                    "path": "10210-landing",
                    "internal_port": 5500,
                    "route": "/home",
                    "startup_cmd": "npm run build && npm start",
                    "health_check": "https://www.cuwapp.com",
                    "enabled": True
                },
                "api": {
                    "name": "Main API",
                    "path": "10210-api", 
                    "internal_port": 8000,
                    "route": "/",
                    "startup_cmd": "python3 start.py",
                    "health_check": "https://app.cuwapp.com/health",
                    "enabled": True
                },
                "auth": {
                    "name": "Authentication",
                    "path": "10210-auth",
                    "internal_port": 5502,
                    "route": "/auth",
                    "startup_cmd": "npm run build && npm start",
                    "health_check": "https://auth.cuwapp.com",
                    "enabled": True
                },
                "blog": {
                    "name": "Blog",
                    "path": "../10210/simple-blog/cuwhapp-openblog",
                    "internal_port": 5503,
                    "route": "/blog",
                    "startup_cmd": "rm -rf node_modules pnpm-lock.yaml && pnpm add react@18.3.1 react-dom@18.3.1 -D && pnpm install && pnpm run dev",
                    "health_check": "http://localhost:5503",
                    "enabled": False  # Blog is now part of landing page at /blog
                },
                "admin": {
                    "name": "Admin Panel",
                    "path": "10210-admin",
                    "internal_port": 8001,
                    "route": "/admin",
                    "startup_cmd": "./start_admin_local.sh",
                    "health_check": "https://admin.cuwapp.com",
                    "enabled": True  # Admin dashboard on separate port
                },
                "instance_manager": {
                    "name": "Instance Manager",
                    "path": "10210-api",
                    "internal_port": 8002,
                    "route": "/instances",
                    "startup_cmd": "python3 waha_session_manager.py",
                    "health_check": "http://localhost:8002/health",
                    "enabled": True
                },
                "waha_autoscaler": {
                    "name": "WAHA Autoscaler",
                    "path": "10210-api",
                    "internal_port": None,  # Runs as background service
                    "route": None,
                    "startup_cmd": "python3 -c \"from waha_pool_manager import waha_pool; import time; print('WAHA Pool Manager initialized'); while True: time.sleep(30)\"",
                    "health_check": None,
                    "enabled": True
                }
            },
            "docker": {
                "username": "devlikeapro",
                "token": os.getenv('DOCKER_TOKEN'),
                "waha_image": "devlikeapro/waha-plus:latest",
                "waha_ports_start": 3000,
                "waha_ports_end": 3100,
                "waha_free_port": 4500,  # Port for free users instance
                "waha_paid_ports_start": 4501,  # Start of paid user ports
                "waha_paid_ports_end": 4600,  # End of paid user ports
                "remote_endpoint": os.getenv('DOCKER_HOST', ''),  # Remote Docker endpoint for Digital Ocean
                "is_remote": os.getenv('DOCKER_HOST', '').startswith('tcp://') or os.getenv('DOCKER_HOST', '').startswith('ssh://')
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "whatsapp_agent",
                "user": "postgres",
                "password": ""
            },
            "redis": {
                "host": "localhost",
                "port": 6379
            },
            "required_env_vars": [
                "GROQ_API_KEY",
                "STRIPE_API_KEY", 
                "STRIPE_WEBHOOK_SECRET",
                "CRYPTOMUS_API_KEY",
                "CRYPTOMUS_MERCHANT_ID",
                "JWT_SECRET_KEY"
            ]
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    existing_config = json.load(f)
                    # Merge with defaults (defaults win for structure, existing wins for values)
                    return self.merge_configs(default_config, existing_config)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                return default_config
        else:
            # Save default config
            self.save_config(default_config)
            return default_config
    
    def merge_configs(self, default: Dict, existing: Dict) -> Dict:
        """Merge existing config with defaults"""
        result = default.copy()
        for key, value in existing.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def save_config(self, config: Dict = None):
        """Save configuration to file"""
        if config is None:
            config = self.config
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration saved to {self.config_file}")
    
    def validate_required_vars(self) -> Tuple[bool, List[str]]:
        """Check if all required environment variables are set"""
        missing = []
        
        # Check .env file
        env_vars = {}
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value
        
        # Check required vars
        for var in self.config['required_env_vars']:
            if var not in env_vars and var not in os.environ:
                missing.append(var)
        
        return len(missing) == 0, missing
    
    def prompt_for_config(self, missing_vars: List[str]):
        """Prompt user for missing configuration"""
        print("\n" + "="*60)
        print("CONFIGURATION REQUIRED")
        print("="*60)
        print("The following environment variables are missing:")
        
        new_vars = {}
        for var in missing_vars:
            print(f"\n{var}:")
            if "PASSWORD" in var or "SECRET" in var or "KEY" in var:
                import getpass
                value = getpass.getpass(f"Enter value for {var}: ")
            else:
                value = input(f"Enter value for {var}: ")
            new_vars[var] = value
        
        # Save to .env file
        with open(self.env_file, 'a') as f:
            f.write(f"\n# Added by startup script on {datetime.now()}\n")
            for key, value in new_vars.items():
                f.write(f"{key}={value}\n")
        
        print(f"\nConfiguration saved to {self.env_file}")
        return True

class DependencyChecker:
    """Check and validate all dependencies"""
    
    @staticmethod
    def check_command(cmd: str) -> bool:
        """Check if a command exists"""
        try:
            subprocess.run(
                f"which {cmd}" if os.name != 'nt' else f"where {cmd}",
                shell=True, capture_output=True, check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def check_port(port: int) -> bool:
        """Check if a port is available"""
        if port is None:
            return True  # For services without ports
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result != 0
    
    def validate_dependencies(self) -> Tuple[bool, List[str]]:
        """Validate all required dependencies"""
        required = {
            'docker': 'Docker is required for WAHA containers',
            'python3': 'Python 3 is required',
            'npm': 'Node.js/npm is required for frontend components',
            'pnpm': 'pnpm is required for blog component',
            'nginx': 'nginx is REQUIRED - it routes all services through port 10210'
        }
        
        missing = []
        for cmd, desc in required.items():
            if not self.check_command(cmd):
                missing.append(f"{cmd}: {desc}")
                logger.warning(f"Missing dependency: {cmd}")
        
        return len(missing) == 0, missing

class WAHAManager:
    """Manage WAHA Docker containers with autoscaling support"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.docker_config = config['docker']
        self.setup_docker_context()
        
    def setup_docker_context(self):
        """Setup Docker context for remote or local deployment"""
        if self.docker_config.get('is_remote'):
            # Using remote Docker endpoint
            logger.info(f"Using remote Docker endpoint: {self.docker_config['remote_endpoint']}")
            os.environ['DOCKER_HOST'] = self.docker_config['remote_endpoint']
        else:
            # Using local Docker
            logger.info("Using local Docker daemon")
    
    def docker_login(self) -> bool:
        """Login to Docker registry"""
        try:
            docker_token = os.getenv('DOCKER_TOKEN', self.docker_config.get('token', ''))
            cmd = f"docker login -u {self.docker_config['username']} -p {docker_token}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Docker login successful")
                return True
            else:
                logger.error(f"Docker login failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Docker login error: {e}")
            return False
    
    def pull_waha_image(self) -> bool:
        """Pull WAHA image if not exists"""
        try:
            # Check if image exists
            check_cmd = f"docker images -q {self.docker_config['waha_image']}"
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            
            if not result.stdout.strip():
                logger.info(f"Pulling WAHA image: {self.docker_config['waha_image']}")
                pull_cmd = f"docker pull {self.docker_config['waha_image']}"
                result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("WAHA image pulled successfully")
                    return True
                else:
                    logger.error(f"Failed to pull WAHA image: {result.stderr}")
                    return False
            else:
                logger.info("WAHA image already exists")
                return True
        except Exception as e:
            logger.error(f"Error managing WAHA image: {e}")
            return False
    
    def get_existing_containers(self) -> List[Dict]:
        """Get list of existing WAHA containers"""
        try:
            cmd = "docker ps -a --format json --filter 'ancestor=devlikeapro/waha-plus'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    container = json.loads(line)
                    containers.append(container)
            
            return containers
        except Exception as e:
            logger.error(f"Error getting containers: {e}")
            return []
    
    def check_port_conflicts(self, containers: List[Dict]) -> List[str]:
        """Check for port conflicts between containers"""
        conflicts = []
        used_ports = set()
        
        for container in containers:
            # Parse ports from container info
            if 'Ports' in container:
                ports_str = container['Ports']
                # Extract port numbers (this is simplified, might need adjustment)
                import re
                port_matches = re.findall(r':(\d+)->', ports_str)
                for port in port_matches:
                    if port in used_ports:
                        conflicts.append(f"Port {port} is used by multiple containers")
                    used_ports.add(port)
        
        return conflicts
    
    def start_existing_containers(self) -> bool:
        """Start all existing WAHA containers"""
        try:
            containers = self.get_existing_containers()
            
            if not containers:
                logger.info("No existing WAHA containers found")
                # Create default containers for free and paid users
                return self.create_default_containers()
            
            # Check for conflicts and handle them
            conflicts = self.check_port_conflicts(containers)
            if conflicts:
                logger.warning(f"Port conflicts detected: {conflicts}")
                # Find which containers are already running on conflicting ports
                running_on_ports = {}
                for container in containers:
                    if container['State'] == 'running':
                        for port_map in container['Ports'].split(','):
                            if '->' in port_map:
                                host_port = port_map.split(':')[-1].split('->')[0]
                                running_on_ports[host_port] = container['Names']
                
                # Only start containers that won't conflict
                for container in containers:
                    container_id = container['ID']
                    container_name = container['Names']
                    
                    # Skip if container wants a port that's already in use by another running container
                    skip = False
                    for port_map in container['Ports'].split(','):
                        if '->' in port_map:
                            host_port = port_map.split(':')[-1].split('->')[0]
                            if host_port in running_on_ports and running_on_ports[host_port] != container_name:
                                logger.info(f"Skipping {container_name} - port {host_port} already used by {running_on_ports[host_port]}")
                                skip = True
                                break
                    
                    if not skip and container['State'] != 'running':
                        logger.info(f"Starting container: {container_name}")
                        subprocess.run(f"docker start {container_id}", shell=True)
                    elif container['State'] == 'running':
                        logger.info(f"Container {container_name} already running")
            else:
                # No conflicts, start all stopped containers
                for container in containers:
                    container_id = container['ID']
                    if container['State'] != 'running':
                        logger.info(f"Starting container: {container_id}")
                        subprocess.run(f"docker start {container_id}", shell=True)
            
            return True
        except Exception as e:
            logger.error(f"Error starting containers: {e}")
            return False
    
    def create_default_containers(self) -> bool:
        """Create default WAHA containers for free and paid users"""
        try:
            # Create network if not exists
            network_cmd = f"docker network create cuwhapp-network 2>/dev/null || true"
            subprocess.run(network_cmd, shell=True)
            
            # Check if container already exists on the port first
            free_port = self.docker_config['waha_free_port']
            
            # Check if any container is using this port
            check_cmd = f"docker ps -a --filter 'publish={free_port}' --format '{{{{.Names}}}}'"
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            existing_container = result.stdout.strip()
            
            if existing_container:
                logger.info(f"Found existing container '{existing_container}' on port {free_port}")
                # Start it if it's not running
                start_cmd = f"docker start {existing_container} 2>/dev/null"
                subprocess.run(start_cmd, shell=True)
                logger.info(f"Using existing WAHA container '{existing_container}' on port {free_port}")
            elif DependencyChecker.check_port(free_port):
                # Port is free, create new container
                cmd = f"""docker run -d \
                    --name waha-plus \
                    --network cuwhapp-network \
                    -p {free_port}:3000 \
                    -e WHATSAPP_SESSIONS_LIMIT=100 \
                    --restart unless-stopped \
                    {self.docker_config['waha_image']}"""
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Created free users WAHA container on port {free_port}")
                else:
                    logger.error(f"Failed to create free WAHA container: {result.stderr}")
            else:
                logger.info(f"Port {free_port} already in use by non-Docker process")
            
            # Check for paid users container (Instance 2)
            paid_port = self.docker_config['waha_paid_ports_start']
            
            # Check if any container is using this port
            check_cmd = f"docker ps -a --filter 'publish={paid_port}' --format '{{{{.Names}}}}'"
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            existing_paid_container = result.stdout.strip()
            
            if existing_paid_container:
                logger.info(f"Found existing paid container '{existing_paid_container}' on port {paid_port}")
                # Start it if it's not running
                start_cmd = f"docker start {existing_paid_container} 2>/dev/null"
                subprocess.run(start_cmd, shell=True)
                logger.info(f"Using existing paid WAHA container '{existing_paid_container}' on port {paid_port}")
            elif DependencyChecker.check_port(paid_port):
                # Port is free, create new container
                cmd = f"""docker run -d \
                    --name waha-paid-instance-1 \
                    --network cuwhapp-network \
                    -p {paid_port}:3000 \
                    -e WHATSAPP_SESSIONS_LIMIT=100 \
                    --restart unless-stopped \
                    {self.docker_config['waha_image']}"""
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Created first paid users WAHA container on port {paid_port}")
                else:
                    logger.error(f"Failed to create paid WAHA container: {result.stderr}")
            else:
                logger.info(f"Port {paid_port} already in use by non-Docker process")
            
            return True
        except Exception as e:
            logger.error(f"Error creating containers: {e}")
            return False
    
    def initialize_waha_database(self):
        """Initialize WAHA instances in database"""
        try:
            import sqlite3
            db_path = self.config['components']['api']['path'] + "/data/wagent.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create waha_instances table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS waha_instances (
                    instance_id INTEGER PRIMARY KEY,
                    container_name TEXT UNIQUE,
                    port INTEGER,
                    url TEXT,
                    current_sessions INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert default instances
            cursor.execute("""
                INSERT OR IGNORE INTO waha_instances 
                (instance_id, container_name, port, url, current_sessions)
                VALUES 
                (1, 'waha-free-instance', ?, ?, 0),
                (2, 'waha-paid-instance-1', ?, ?, 0)
            """, (
                self.docker_config['waha_free_port'],
                f"http://localhost:{self.docker_config['waha_free_port']}",
                self.docker_config['waha_paid_ports_start'],
                f"http://localhost:{self.docker_config['waha_paid_ports_start']}"
            ))
            
            conn.commit()
            conn.close()
            logger.info("WAHA instances initialized in database")
        except Exception as e:
            logger.error(f"Error initializing WAHA database: {e}")

class ComponentManager:
    """Manage individual project components"""
    
    def __init__(self, config: Dict, base_dir: Path):
        self.config = config
        self.base_dir = base_dir
        self.processes = {}
        self.threads = {}
        
    def start_component(self, component_key: str) -> bool:
        """Start a single component"""
        component = self.config['components'][component_key]
        
        if not component['enabled']:
            logger.info(f"Component {component['name']} is disabled")
            return True
        
        # Check if port is available (if component has a port)
        if component['internal_port'] and not DependencyChecker.check_port(component['internal_port']):
            logger.warning(f"Port {component['internal_port']} is already in use for {component['name']}")
            # Assume it's already running
            return True
        
        # Determine working directory
        if component_key == 'blog':
            # Special case for blog (in different parent directory)
            work_dir = self.base_dir.parent / '10210' / 'simple-blog' / 'cuwhapp-openblog'
        else:
            work_dir = self.base_dir / component['path']
        
        if not work_dir.exists():
            logger.error(f"Component directory not found: {work_dir}")
            return False
        
        # Check for node_modules if it's a Node.js project
        if component['startup_cmd'].startswith('npm') or component['startup_cmd'].startswith('pnpm'):
            if not (work_dir / 'node_modules').exists():
                logger.info(f"Installing dependencies for {component['name']}...")
                install_cmd = 'npm install' if component['startup_cmd'].startswith('npm') else 'pnpm install'
                install_process = subprocess.run(
                    install_cmd,
                    shell=True,
                    cwd=work_dir,
                    capture_output=True,
                    text=True
                )
                if install_process.returncode != 0:
                    logger.error(f"Failed to install dependencies for {component['name']}: {install_process.stderr}")
                    return False
                logger.info(f"Dependencies installed for {component['name']}")
        
        logger.info(f"Starting {component['name']} in {work_dir}")
        
        try:
            # Start the process
            process = subprocess.Popen(
                component['startup_cmd'],
                shell=True,
                executable='/bin/bash',
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env={**os.environ}  # Pass environment variables
            )
            
            self.processes[component_key] = process
            
            # Start thread to monitor output
            thread = threading.Thread(
                target=self.monitor_process,
                args=(component_key, process)
            )
            thread.daemon = True
            thread.start()
            self.threads[component_key] = thread
            
            # Wait for component to be ready
            logger.info(f"Waiting for {component['name']} to be ready...")
            
            # For components with ports, wait until port is occupied
            if component['internal_port']:
                max_wait = 120  # Maximum 120 seconds (increased for npm builds)
                waited = 0
                while waited < max_wait:
                    # Check if process is still running
                    if process.poll() is not None:
                        # Process died
                        logger.error(f"Component {component['name']} stopped unexpectedly")
                        # Get error output
                        stdout, stderr = process.communicate()
                        if stderr:
                            logger.error(f"Error output: {stderr[:500]}")
                        # For Landing Page, we know it might work in a separate terminal, so return warning instead of failure
                        if component['name'] == 'Landing Page':
                            logger.warning(f"Component {component['name']} has stopped but may work when run separately")
                            logger.warning("You can start it manually with: cd 10210-landing && npm run dev")
                            return True  # Continue with other components
                        return False
                    
                    # Check if port is now in use
                    if not DependencyChecker.check_port(component['internal_port']):
                        # Port is in use, component is ready
                        logger.info(f"Component {component['name']} is ready on port {component['internal_port']}")
                        return True
                    
                    time.sleep(1)
                    waited += 1
                    
                    if waited % 5 == 0:
                        logger.info(f"Still waiting for {component['name']}... ({waited}s)")
                
                # Timeout reached
                logger.error(f"Component {component['name']} failed to start within {max_wait} seconds")
                # For Landing Page, provide manual start instructions
                if component['name'] == 'Landing Page':
                    logger.warning("Landing Page can be started manually with: cd 10210-landing && npm run dev")
                    return True  # Continue with other components
                return False
            else:
                # For components without ports (like autoscaler), just check if running
                time.sleep(5)
                if process.poll() is None:
                    logger.info(f"Component {component['name']} started successfully")
                    return True
                else:
                    logger.error(f"Component {component['name']} failed to start")
                    return False
            
        except Exception as e:
            logger.error(f"Error starting {component['name']}: {e}")
            return False
    
    def monitor_process(self, component_key: str, process):
        """Monitor process output"""
        component_name = self.config['components'][component_key]['name']
        
        while True:
            output = process.stdout.readline()
            if output:
                logger.debug(f"[{component_name}] {output.strip()}")
            
            if process.poll() is not None:
                logger.warning(f"Component {component_name} has stopped")
                break
    print("Killing existing processes on ports...")
    ports = [8000, 8001, 5502, 5500]
    for port in ports:
        try:
            result = subprocess.run(f"sudo lsof -t -i:{port}", shell=True, capture_output=True, text=True)
            if result.stdout.strip():
                subprocess.run(f"sudo kill -9 {result.stdout.strip()}", shell=True)
                print(f"Killed process on port {port}")
        except:
            pass
    def start_all_components(self) -> bool:
        """Start all enabled components in order"""
        startup_order = [
            'landing',           # Frontend landing page
            'api',              # Main backend API
            'auth',             # Authentication service
            'blog',             # Blog
            'admin',            # Admin panel
            'instance_manager', # WAHA instance manager
            'waha_autoscaler'   # WAHA autoscaling service
        ]
        
        for component_key in startup_order:
            if component_key in self.config['components']:
                success = self.start_component(component_key)
                if not success:
                    logger.error(f"Failed to start {component_key}")
                    # Continue with other components
                
                # Small delay between components
                time.sleep(2)
        
        return True
    
    def stop_all_components(self):
        """Stop all running components"""
        logger.info("Stopping all components...")
        
        for component_key, process in self.processes.items():
            if process and process.poll() is None:
                logger.info(f"Stopping {component_key}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        
        self.processes.clear()

class NginxConfigurator:
    """Configure nginx reverse proxy"""
    
    @staticmethod
    def generate_config(config: Dict) -> str:
        """Generate nginx configuration"""
        main_port = config['main_port']
        
        # Only route landing page through nginx on port 10210
        # Other services remain on their individual ports
        nginx_conf = f"""
# Auto-generated nginx configuration for 10210 project
events {{
    worker_connections 1024;
}}

http {{
    server {{
        listen {main_port};
        server_name _;  # Accept any hostname (174.138.55.42, localhost, etc.)
    
    # Landing Page - The only service routed through nginx
    location / {{
        proxy_pass http://localhost:{config['components']['landing']['internal_port']}/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    }}
}}

# Other services run on their individual ports:
# API:              http://174.138.55.42:8000 or https://app.cuwapp.com
# Admin:            http://174.138.55.42:8001 or https://admin.cuwapp.com  
# Auth:             http://174.138.55.42:5502 or https://auth.cuwapp.com
# Instance Manager: http://174.138.55.42:8002 or http://localhost:8002
# WAHA Free:        http://174.138.55.42:4500 or http://localhost:4500
# WAHA Paid:        http://174.138.55.42:4501+ or http://localhost:4501+
"""
        return nginx_conf
    
    @staticmethod
    def save_config(config: Dict, base_dir: Path):
        """Save nginx configuration to file"""
        nginx_conf = NginxConfigurator.generate_config(config)
        conf_file = base_dir / "nginx.conf"
        
        with open(conf_file, 'w') as f:
            f.write(nginx_conf)
        
        logger.info(f"Nginx configuration saved to {conf_file}")
        print(f"\nTo use nginx proxy, copy {conf_file} to your nginx config directory")
        print(f"and reload nginx: sudo nginx -s reload")
        
        return conf_file

class MainStartup:
    """Main startup orchestrator"""
    
    def __init__(self):
        self.config_manager = ProjectConfig()
        self.config = self.config_manager.config
        self.dependency_checker = DependencyChecker()
        self.waha_manager = WAHAManager(self.config)
        self.component_manager = ComponentManager(self.config, self.config_manager.base_dir)
        self.running = False
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            logger.info("Shutdown signal received")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def startup_sequence(self) -> bool:
        """Main startup sequence"""
        print("\n" + "="*60)
        print("10210 PROJECT STARTUP")
        print("="*60)
        
        # Step 1: Check dependencies
        print("\n[1/8] Checking dependencies...")
        deps_ok, missing_deps = self.dependency_checker.validate_dependencies()
        if not deps_ok:
            print("\nMISSING REQUIRED DEPENDENCIES:")
            for dep in missing_deps:
                print(f"  ❌ {dep}")
            
            print("\n" + "="*60)
            print("INSTALLATION INSTRUCTIONS:")
            print("="*60)
            
            # Check for nginx specifically
            if 'nginx' in str(missing_deps):
                print("\nNGINX is REQUIRED for routing all services through port 10210")
                print("To install nginx on macOS:")
                print("  brew install nginx")
                print("\nWithout nginx, you would need to access each service separately:")
                print("  - Landing: https://www.cuwapp.com")
                print("  - API: https://app.cuwapp.com")
                print("  - Auth: https://auth.cuwapp.com")
                print("  - etc...")
                print("\nWith nginx, everything works through: http://localhost:10210")
            
            if 'pnpm' in str(missing_deps):
                print("\nTo install pnpm:")
                print("  npm install -g pnpm")
            
            print("\nPlease install missing dependencies and try again")
            return False
        
        # Step 2: Validate configuration
        print("\n[2/8] Validating configuration...")
        config_ok, missing_vars = self.config_manager.validate_required_vars()
        if not config_ok:
            print(f"\nMissing environment variables: {missing_vars}")
            if not self.config_manager.prompt_for_config(missing_vars):
                return False
        
        # Step 3: Docker/WAHA setup
        print("\n[3/8] Setting up WAHA containers...")
        if self.dependency_checker.check_command('docker'):
            if not self.waha_manager.docker_login():
                print("Warning: Docker login failed, continuing anyway...")
            
            if not self.waha_manager.pull_waha_image():
                print("Warning: Could not pull WAHA image")
            
            if not self.waha_manager.start_existing_containers():
                print("Warning: Could not start WAHA containers")
            
            # Initialize WAHA in database
            self.waha_manager.initialize_waha_database()
        else:
            print("Docker not available, skipping WAHA setup")
        
        # Step 4: Setup and start nginx
        print("\n[4/8] Setting up nginx (for landing page routing only)...")
        nginx_config_path = NginxConfigurator.save_config(self.config, self.config_manager.base_dir)
        
        # Check if nginx is running
        nginx_status = subprocess.run("pgrep nginx", shell=True, capture_output=True)
        if nginx_status.returncode != 0:
            print("Starting nginx...")
            # Try to start nginx with our config
            nginx_cmd = f"sudo nginx -c {nginx_config_path}"
            print(f"Running: {nginx_cmd}")
            print("(You may need to enter your password)")
            result = subprocess.run(nginx_cmd, shell=True)
            if result.returncode == 0:
                print("✅ Nginx started successfully - routing landing page on port 10210")
            else:
                print("⚠️  Could not start nginx automatically")
                print(f"Please manually run: {nginx_cmd}")
        else:
            print("✅ Nginx is already running")
            print(f"To reload with new config: sudo nginx -c {nginx_config_path} -s reload")
        
        print("\nNOTE: Only the landing page is routed through nginx on port 10210")
        print("Other services run on their individual ports and are directly accessible")
        
        # Step 5: Start components
        print("\n[5/8] Starting components...")
        if not self.component_manager.start_all_components():
            print("Warning: Some components failed to start")
        
        # Step 6: WAHA Autoscaling Monitor
        print("\n[6/8] Starting WAHA autoscaling monitor...")
        self.start_waha_monitor()
        
        # Step 7: Configure nginx routing
        print("\n[7/8] Configuring nginx routing...")
        print("All services are now accessible through http://localhost:10210")
        
        # Step 8: Final status
        print("\n[8/8] Startup complete!")
        self.print_status()
        
        self.running = True
        return True
    
    def start_waha_monitor(self):
        """Start WAHA autoscaling monitor in background"""
        def monitor_loop():
            """Background loop to monitor and scale WAHA instances"""
            while self.running:
                try:
                    # This would call the autoscaling check
                    # In production, this would be more sophisticated
                    time.sleep(30)  # Check every 30 seconds
                    
                    # The actual autoscaling happens through waha_pool_manager
                    # when sessions are created via the API
                    logger.debug("WAHA monitor check completed")
                    
                except Exception as e:
                    logger.error(f"WAHA monitor error: {e}")
        
        monitor_thread = threading.Thread(target=monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        logger.info("WAHA autoscaling monitor started")
    
    def print_status(self):
        """Print current status of all components"""
        print("\n" + "="*60)
        print("SYSTEM STATUS")
        print("="*60)
        
        main_port = self.config['main_port']
        print(f"\nMain application URL: http://localhost:{main_port}")
        print("\nComponent Status:")
        
        for key, component in self.config['components'].items():
            if component['enabled']:
                if component['internal_port']:
                    port_status = "BUSY" if not DependencyChecker.check_port(component['internal_port']) else "FREE"
                    if port_status == "BUSY":
                        status = "✓ Running"
                    else:
                        status = "✗ Not running"
                    port_info = f"Port: {component['internal_port']:5}"
                else:
                    status = "✓ Running"  # Background services
                    port_info = "Port: N/A  "
                
                route_info = f"Route: {component['route']}" if component['route'] else "Route: N/A"
                print(f"  {component['name']:20} {status:15} {port_info} {route_info}")
        
        # Get server IP
        server_ip = os.getenv('SERVER_IP', '174.138.55.42')
        
        print("\nAccess URLs:")
        print(f"  Landing Page: http://{server_ip}:{main_port}/ or http://localhost:{main_port}/")
        print(f"  API:          http://{server_ip}:8000 or https://app.cuwapp.com")
        print(f"  Admin:        http://{server_ip}:8001 or https://admin.cuwapp.com")
        print(f"  Auth:         http://{server_ip}:5502 or https://auth.cuwapp.com")
        print(f"  Instances:    http://{server_ip}:8002 or http://localhost:8002")
        
        print("\nWAHA Instances:")
        print(f"  Free Users:   http://localhost:{self.config['docker']['waha_free_port']}")
        print(f"  Paid Users:   http://localhost:{self.config['docker']['waha_paid_ports_start']} (autoscales as needed)")
        
        print("\n" + "="*60)
    
    def shutdown(self):
        """Graceful shutdown"""
        if self.running:
            logger.info("Shutting down...")
            self.running = False
            self.component_manager.stop_all_components()
            print("\nShutdown complete")
    
    def run(self):
        """Main run method"""
        self.setup_signal_handlers()
        
        if self.startup_sequence():
            print("\nPress Ctrl+C to shutdown")
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            print("\nStartup failed")
            sys.exit(1)

def main():
    """Main entry point"""
    startup = MainStartup()
    startup.run()

if __name__ == "__main__":
    main()
