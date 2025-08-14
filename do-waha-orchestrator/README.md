# WAHA Orchestrator - DigitalOcean Function

This function manages WAHA (WhatsApp Business API) instances on a Docker droplet.

## Setup

### 1. Install DigitalOcean CLI (doctl)

```bash
# macOS
brew install doctl

# Linux
cd ~
wget https://github.com/digitalocean/doctl/releases/download/v1.104.0/doctl-1.104.0-linux-amd64.tar.gz
tar xf doctl-1.104.0-linux-amd64.tar.gz
sudo mv doctl /usr/local/bin
```

### 2. Authenticate with DigitalOcean

```bash
doctl auth init
# Enter your DigitalOcean API token
```

### 3. Configure Environment Variables

Edit `.env` file with your actual values:

```env
DOCKER_USERNAME=devlikeapro
DOCKER_TOKEN=your_docker_token
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
DOCKER_HOST=your-droplet-ip
```

### 4. Deploy the Function

```bash
./deploy.sh
```

## Usage

### Create a WAHA Instance

```bash
curl -X POST https://your-function-url.digitaloceanfunctions.com/api/v1/web/fn-xxx/waha-manager/waha-manager \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "create",
    "docker_host": "167.99.123.45",
    "image": "devlikeapro/waha-plus:latest",
    "user_id": "user123",
    "plan_type": "pro",
    "max_sessions": 10
  }'
```

Response:
```json
{
  "success": true,
  "instance": {
    "port": 4501,
    "endpoint": "http://167.99.123.45:4501",
    "api_key": "waha_key_4501",
    "container_id": "abc123def456",
    "container_name": "waha-user123-4501"
  }
}
```

### List All Instances

```bash
curl -X POST https://your-function-url.digitaloceanfunctions.com/api/v1/web/fn-xxx/waha-manager/waha-manager \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "list",
    "docker_host": "167.99.123.45"
  }'
```

### Destroy an Instance

```bash
curl -X POST https://your-function-url.digitaloceanfunctions.com/api/v1/web/fn-xxx/waha-manager/waha-manager \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "destroy",
    "docker_host": "167.99.123.45",
    "port": 4501
  }'
```

### Check Instance Health

```bash
curl -X POST https://your-function-url.digitaloceanfunctions.com/api/v1/web/fn-xxx/waha-manager/waha-manager \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "check_health",
    "docker_host": "167.99.123.45",
    "port": 4501
  }'
```

## Docker Droplet Setup

Your Docker droplet needs to:

1. **Have Docker installed**
2. **Expose Docker API** (for TCP connection) OR
3. **Have SSH access** (recommended)

### Option 1: SSH Access (Recommended)

Just ensure your function can SSH to the droplet:
- Add the function's SSH key to the droplet's authorized_keys
- Or use password authentication

### Option 2: TCP Access (Less Secure)

Edit `/etc/docker/daemon.json` on your droplet:

```json
{
  "hosts": ["tcp://0.0.0.0:2375", "unix:///var/run/docker.sock"]
}
```

Then restart Docker:
```bash
sudo systemctl restart docker
```

⚠️ **Warning**: This exposes Docker API without authentication. Use firewall rules to restrict access.

### Option 3: TCP with TLS (Secure)

For production, use TLS certificates. See Docker documentation for setup.

## Integration with Your App

In your main application, replace the local orchestrator calls with HTTP requests to this function:

```python
import requests

def create_waha_instance(user_id, plan_type):
    response = requests.post(
        "https://your-function-url.digitaloceanfunctions.com/api/v1/web/fn-xxx/waha-manager/waha-manager",
        json={
            "action": "create",
            "docker_host": "167.99.123.45",
            "image": "devlikeapro/waha-plus:latest",
            "user_id": user_id,
            "plan_type": plan_type
        }
    )
    return response.json()
```

## Monitoring

View function logs:
```bash
doctl serverless activations logs --follow
```

List recent activations:
```bash
doctl serverless activations list
```