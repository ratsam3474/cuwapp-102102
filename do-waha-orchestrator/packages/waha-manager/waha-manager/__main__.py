import os
import json
import requests
from typing import Dict, Any

def main(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    DigitalOcean Function to manage WAHA instances via Docker API
    """
    try:
        # Get action from request
        action = args.get('action', 'create')
        docker_host = args.get('docker_host') or os.environ.get('DOCKER_HOST', 'localhost')
        docker_port = args.get('docker_port', 2375)
        
        # Docker API base URL
        docker_api = f"http://{docker_host}:{docker_port}"
        
        if action == 'create':
            return create_instance(args, docker_api)
        elif action == 'list':
            return list_instances(docker_api)
        elif action == 'destroy':
            return destroy_instance(args, docker_api)
        else:
            return {
                "statusCode": 400,
                "body": {"error": f"Unknown action: {action}"}
            }
            
    except Exception as e:
        return {
            "statusCode": 500,
            "body": {"error": str(e), "type": str(type(e))}
        }

def create_instance(args: Dict[str, Any], docker_api: str) -> Dict[str, Any]:
    """Create a new WAHA instance via Docker API"""
    
    try:
        # Get parameters
        user_id = args.get('user_id', 'anonymous')
        plan_type = args.get('plan_type', 'starter')
        max_sessions = args.get('max_sessions', 1)
        image_name = args.get('image', 'devlikeapro/waha-plus:latest')
        
        # Find next available port (simplified - just use a timestamp-based port)
        import time
        port = 4501 + (int(time.time()) % 100)  # Ports 4501-4600
        
        # Container configuration
        container_name = f"waha-{user_id[:8]}-{port}"
        
        # Create container via Docker API
        container_config = {
            "Image": image_name,
            "name": container_name,
            "ExposedPorts": {"3000/tcp": {}},
            "HostConfig": {
                "PortBindings": {
                    "3000/tcp": [{"HostPort": str(port)}]
                },
                "RestartPolicy": {"Name": "unless-stopped"}
            },
            "Env": [
                "WAHA_PRINT_QR=false",
                "WAHA_LOG_LEVEL=info",
                f"WAHA_MAX_SESSIONS={max_sessions}",
                "WAHA_SESSION_STORE_ENABLED=true",
                "WAHA_SESSION_STORE_PATH=/app/sessions"
            ],
            "Labels": {
                "user_id": user_id,
                "plan_type": plan_type,
                "managed_by": "do-function",
                "port": str(port)
            }
        }
        
        # Create the container
        response = requests.post(
            f"{docker_api}/containers/create",
            params={"name": container_name},
            json=container_config
        )
        
        if response.status_code == 201:
            container_id = response.json()["Id"]
            
            # Start the container
            start_response = requests.post(
                f"{docker_api}/containers/{container_id}/start"
            )
            
            if start_response.status_code == 204:
                docker_host = docker_api.replace("http://", "").split(":")[0]
                
                return {
                    "statusCode": 200,
                    "body": {
                        "success": True,
                        "instance": {
                            "port": port,
                            "endpoint": f"http://{docker_host}:{port}",
                            "container_id": container_id[:12],
                            "container_name": container_name,
                            "image": image_name
                        }
                    }
                }
            else:
                return {
                    "statusCode": 500,
                    "body": {"error": f"Failed to start container: {start_response.text}"}
                }
        else:
            return {
                "statusCode": 500,
                "body": {"error": f"Failed to create container: {response.text}"}
            }
            
    except Exception as e:
        return {
            "statusCode": 500,
            "body": {"error": f"Failed to create instance: {str(e)}"}
        }

def list_instances(docker_api: str) -> Dict[str, Any]:
    """List all WAHA instances via Docker API"""
    
    try:
        # Get all containers with our label
        response = requests.get(
            f"{docker_api}/containers/json",
            params={"all": True, "filters": json.dumps({"label": ["managed_by=do-function"]})}
        )
        
        if response.status_code == 200:
            containers = response.json()
            instances = []
            
            for container in containers:
                instances.append({
                    "id": container["Id"][:12],
                    "name": container["Names"][0].lstrip("/") if container["Names"] else "",
                    "status": container["State"],
                    "ports": container["Ports"],
                    "labels": container["Labels"]
                })
            
            return {
                "statusCode": 200,
                "body": {
                    "success": True,
                    "instances": instances,
                    "count": len(instances)
                }
            }
        else:
            return {
                "statusCode": 500,
                "body": {"error": f"Failed to list containers: {response.text}"}
            }
            
    except Exception as e:
        return {
            "statusCode": 500,
            "body": {"error": f"Failed to list instances: {str(e)}"}
        }

def destroy_instance(args: Dict[str, Any], docker_api: str) -> Dict[str, Any]:
    """Destroy a WAHA instance via Docker API"""
    
    try:
        container_name = args.get('container_name')
        container_id = args.get('container_id')
        port = args.get('port')
        
        # Find container by port if provided
        if port and not container_id and not container_name:
            response = requests.get(
                f"{docker_api}/containers/json",
                params={"all": True, "filters": json.dumps({"label": [f"port={port}"]})}
            )
            
            if response.status_code == 200:
                containers = response.json()
                if containers:
                    container_id = containers[0]["Id"]
                else:
                    return {
                        "statusCode": 404,
                        "body": {"error": f"No container found on port {port}"}
                    }
        
        # Use container name or ID
        container_ref = container_id or container_name
        
        if not container_ref:
            return {
                "statusCode": 400,
                "body": {"error": "container_name, container_id, or port required"}
            }
        
        # Stop the container
        stop_response = requests.post(
            f"{docker_api}/containers/{container_ref}/stop"
        )
        
        # Remove the container
        remove_response = requests.delete(
            f"{docker_api}/containers/{container_ref}"
        )
        
        if remove_response.status_code in [204, 404]:
            return {
                "statusCode": 200,
                "body": {
                    "success": True,
                    "message": f"Container {container_ref} destroyed"
                }
            }
        else:
            return {
                "statusCode": 500,
                "body": {"error": f"Failed to remove container: {remove_response.text}"}
            }
            
    except Exception as e:
        return {
            "statusCode": 500,
            "body": {"error": f"Failed to destroy instance: {str(e)}"}
        }