# CuWapp Infrastructure Migration Reference
## Complete Guide for URL/IP Replacements

---

## Executive Summary

This document catalogs all 513 hardcoded URL and IP references that need to be replaced with environment variables as part of the migration from DigitalOcean (174.138.55.42) to Google Cloud Platform (34.173.85.56). The migration implements a per-user container architecture where each user receives dedicated Docker containers after signup.

### Migration Overview
- **Total Changes Required**: 513 occurrences across 168 files
- **Old Infrastructure**: DigitalOcean Droplet (174.138.55.42)
- **New Infrastructure**: Google Cloud Platform
  - WAHA VM: 34.133.143.67 (10.128.0.3 internal)
  - User VM: 34.173.85.56 (10.128.0.4 internal)
- **Container Manager**: Google Cloud Run Function
- **Architecture**: Per-user dedicated containers with dynamic port allocation

---

## Environment Variables Required

### Domain Configuration
```bash
# Primary Domains
export MAIN_DOMAIN="cuwapp.com"
export APP_SUBDOMAIN="app.cuwapp.com"
export AUTH_SUBDOMAIN="auth.cuwapp.com"
export ADMIN_SUBDOMAIN="admin.cuwapp.com"

# Service URLs (Public-facing)
export API_GATEWAY_URL="http://app.cuwapp.com"
export AUTH_SERVICE_URL="http://auth.cuwapp.com"
export LANDING_PAGE_URL="http://cuwapp.com"
export ADMIN_SERVICE_URL="http://admin.cuwapp.com"

# Server IPs
export OLD_SERVER_IP="174.138.55.42"  # To be replaced everywhere
export NEW_SERVER_IP="34.173.85.56"   # New GCP User VM

# GCP VM Configuration
export WAHA_VM_EXTERNAL_IP="34.133.143.67"
export WAHA_VM_INTERNAL_IP="10.128.0.3"
export USER_VM_EXTERNAL_IP="34.173.85.56"
export USER_VM_INTERNAL_IP="10.128.0.4"

# Container Management
export CONTAINER_MANAGER_URL="https://container-manager-337193391523.us-central1.run.app"
export DO_CONTAINER_FUNCTION_URL="${CONTAINER_MANAGER_URL}"

# Service Ports (Static)
export LANDING_PORT="5500"
export AUTH_PORT="5502"
export GATEWAY_PORT="8000"
export WARMER_PORT="8001"
export CAMPAIGN_PORT="8002"
export ADMIN_PORT="8005"

# Dynamic Port Ranges (Per-user containers)
export API_PORT_RANGE="40000-50000"
export WARMER_PORT_RANGE="20000-30000"
export CAMPAIGN_PORT_RANGE="30000-40000"
export WAHA_PORT_RANGE="4500-5500"
```

---

## Service Architecture & Port Mapping

### Public-Facing Services
| Service | Port | Domain | Description |
|---------|------|--------|-------------|
| Landing Page | 5500 | cuwapp.com | Next.js landing page |
| Auth Service | 5502 | auth.cuwapp.com | Clerk authentication |
| API Gateway | 8000 | app.cuwapp.com | Main API orchestrator |
| Admin Panel | 8005 | admin.cuwapp.com | Admin dashboard |

### Internal Microservices
| Service | Port | Access | Description |
|---------|------|--------|-------------|
| Warmer Service | 8001 | Internal | WhatsApp warming operations |
| Campaign Service | 8002 | Internal | Campaign management |

### Per-User Container Ports (Dynamic)
| Service | Port Range | Allocation |
|---------|------------|------------|
| User API | 40000-50000 | Dynamic per user |
| User Warmer | 20000-30000 | Dynamic per user |
| User Campaign | 30000-40000 | Dynamic per user |
| WAHA Instance | 4500-5500 | Dynamic per user |

---

## File-by-File Changes

### Priority Levels
- **[CRITICAL]** - System will not function without this change
- **[RECOMMENDED]** - Should change for consistency and portability
- **[OPTIONAL]** - Internal references that can remain if not exposed

---

## Section 1: Frontend Files (Landing, Auth, Admin)

### 1.1 Landing Page Components
**Files: 10210-landing/src/components/**

#### `/10210-landing/src/components/UserStatus.tsx`
**[CRITICAL]** - 4 occurrences
```typescript
// OLD:
const API_URL = "http://174.138.55.42:8000"
const AUTH_URL = "https://auth.cuwapp.com"

// NEW:
const API_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || "http://app.cuwapp.com"
const AUTH_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || "https://auth.cuwapp.com"
```

#### `/10210-landing/src/components/CuWhappPricing.tsx`
**[CRITICAL]** - 4 occurrences
```typescript
// OLD:
onClick={() => window.location.href = 'https://auth.cuwapp.com/sign-up'}

// NEW:
onClick={() => window.location.href = `${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/sign-up`}
```

#### `/10210-landing/src/components/CallToAction.tsx`
**[CRITICAL]** - 3 occurrences
```typescript
// OLD:
href="https://app.cuwapp.com/register"

// NEW:
href={`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/register`}
```

#### `/10210-landing/src/components/Hero.tsx`
**[CRITICAL]** - 3 occurrences
```typescript
// OLD:
href="https://auth.cuwapp.com/sign-up"

// NEW:
href={`${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/sign-up`}
```

#### `/10210-landing/src/components/Navbar.tsx`
**[RECOMMENDED]** - 2 occurrences
```typescript
// OLD:
href="https://app.cuwapp.com"

// NEW:
href={process.env.NEXT_PUBLIC_API_GATEWAY_URL}
```

#### `/10210-landing/src/components/Footer.tsx`
**[RECOMMENDED]** - 4 occurrences
```typescript
// OLD:
href="https://cuwapp.com/privacy"

// NEW:
href={`${process.env.NEXT_PUBLIC_LANDING_PAGE_URL}/privacy`}
```

### 1.2 Auth Service Pages
**Files: 10210-auth/app/**

#### `/10210-auth/app/auth-callback/page.tsx`
**[CRITICAL]** - 4 occurrences
```typescript
// OLD:
const response = await fetch('http://174.138.55.42:8000/api/auth/callback', {

// NEW:
const response = await fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/auth/callback`, {
```

#### `/10210-auth/app/sync-session/page.tsx`
**[CRITICAL]** - 2 occurrences
```typescript
// OLD:
window.location.href = 'https://app.cuwapp.com/gateway'

// NEW:
window.location.href = `${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/gateway`
```

#### `/10210-auth/app/logout/page.tsx`
**[RECOMMENDED]** - 2 occurrences
```typescript
// OLD:
window.location.href = 'https://cuwapp.com'

// NEW:
window.location.href = process.env.NEXT_PUBLIC_LANDING_PAGE_URL
```

---

## Section 2: Backend API Files

### 2.1 Core API Configuration

#### `/10210-api/service_config.py`
**[CRITICAL]** - 17 occurrences
```python
# OLD:
SERVICE_URLS = {
    'api': 'http://174.138.55.42:8000',
    'auth': 'https://auth.cuwapp.com',
    'app': 'https://app.cuwapp.com',
    'landing': 'https://cuwapp.com',
    'admin': 'http://174.138.55.42:8005'
}

# NEW:
SERVICE_URLS = {
    'api': os.getenv('API_GATEWAY_URL', 'http://app.cuwapp.com'),
    'auth': os.getenv('AUTH_SERVICE_URL', 'https://auth.cuwapp.com'),
    'app': os.getenv('APP_SUBDOMAIN_URL', 'https://app.cuwapp.com'),
    'landing': os.getenv('LANDING_PAGE_URL', 'https://cuwapp.com'),
    'admin': os.getenv('ADMIN_SERVICE_URL', 'http://admin.cuwapp.com')
}
```

#### `/10210-api/api_gateway.py`
**[CRITICAL]** - 9 occurrences
```python
# OLD:
window.location.href = 'https://app.cuwapp.com/dashboard';

# NEW:
window.location.href = '/static/index.html';  # Already updated for local dashboard
```

#### `/10210-api/dynamic_urls.py`
**[CRITICAL]** - 1 occurrence
```python
# OLD:
DO_CONTAINER_FUNCTION_URL = "https://dodo-kgfq2.ondigitalocean.app/containers"

# NEW:
DO_CONTAINER_FUNCTION_URL = os.getenv('CONTAINER_MANAGER_URL', 
                                      'https://container-manager-337193391523.us-central1.run.app')
```

#### `/10210-api/config.py`
**[CRITICAL]** - 1 occurrence
```python
# OLD:
API_BASE_URL = "http://174.138.55.42:8000"

# NEW:
API_BASE_URL = os.getenv('API_GATEWAY_URL', 'http://app.cuwapp.com')
```

### 2.2 Payment Services

#### `/10210-api/payments/api.py`
**[CRITICAL]** - 6 occurrences
```python
# OLD:
redirect_url = f"https://app.cuwapp.com/payment/success?session_id={session_id}"

# NEW:
redirect_url = f"{os.getenv('API_GATEWAY_URL')}/payment/success?session_id={session_id}"
```

#### `/10210-api/payments/crypto_handler.py`
**[CRITICAL]** - 2 occurrences
```python
# OLD:
"success_url": "https://app.cuwapp.com/payment/success",
"cancel_url": "https://app.cuwapp.com/payment/cancel"

# NEW:
"success_url": f"{os.getenv('API_GATEWAY_URL')}/payment/success",
"cancel_url": f"{os.getenv('API_GATEWAY_URL')}/payment/cancel"
```

### 2.3 Email Services

#### `/10210-api/email_service/templates.py`
**[CRITICAL]** - 4 occurrences
```python
# OLD:
<a href="https://app.cuwapp.com/verify?token={token}">Verify Email</a>

# NEW:
<a href="{os.getenv('API_GATEWAY_URL')}/verify?token={token}">Verify Email</a>
```

#### `/10210-api/email_service/service.py`
**[RECOMMENDED]** - 3 occurrences
```python
# OLD:
dashboard_url = "https://app.cuwapp.com/dashboard"

# NEW:
dashboard_url = f"{os.getenv('API_GATEWAY_URL')}/dashboard"
```

---

## Section 3: Static HTML & JavaScript Files

### 3.1 Dashboard & Gateway Pages

#### `/10210-api/static/index.html`
**[CRITICAL]** - 4 occurrences
```javascript
// OLD:
const API_URL = 'http://174.138.55.42:8000';
const AUTH_URL = 'https://auth.cuwapp.com';

// NEW:
const API_URL = window.ENV?.API_GATEWAY_URL || 'http://app.cuwapp.com';
const AUTH_URL = window.ENV?.AUTH_SERVICE_URL || 'https://auth.cuwapp.com';
```

#### `/10210-api/static/gateway.html`
**[CRITICAL]** - 1 occurrence
```javascript
// OLD:
window.location.href = 'https://auth.cuwapp.com';

// NEW:
window.location.href = window.ENV?.AUTH_SERVICE_URL || 'https://auth.cuwapp.com';
```

#### `/10210-api/static/js/app.js`
**[CRITICAL]** - 4 occurrences
```javascript
// OLD:
const API_BASE = 'http://174.138.55.42:8000/api';

// NEW:
const API_BASE = `${window.ENV?.API_GATEWAY_URL || 'http://app.cuwapp.com'}/api`;
```

### 3.2 Admin Panel Files

#### `/10210-admin/static/js/config.js`
**[CRITICAL]** - 9 occurrences
```javascript
// OLD:
window.CONFIG = {
    API_URL: 'http://174.138.55.42:8005',
    AUTH_URL: 'https://auth.cuwapp.com',
    APP_URL: 'https://app.cuwapp.com'
};

// NEW:
window.CONFIG = {
    API_URL: window.ENV?.ADMIN_SERVICE_URL || 'http://admin.cuwapp.com',
    AUTH_URL: window.ENV?.AUTH_SERVICE_URL || 'https://auth.cuwapp.com',
    APP_URL: window.ENV?.API_GATEWAY_URL || 'https://app.cuwapp.com'
};
```

---

## Section 4: Configuration Files

### 4.1 Nginx Configurations

#### `/10210-api/nginx.conf`
**[CRITICAL]** - 2 occurrences
```nginx
# OLD:
server_name 174.138.55.42;
proxy_pass http://174.138.55.42:8000;

# NEW:
server_name $NEW_SERVER_IP;
proxy_pass http://127.0.0.1:8000;
```

#### `/nginx-vm.conf`
**[CRITICAL]** - 11 occurrences
```nginx
# OLD:
server_name cuwapp.com www.cuwapp.com;

# NEW:
# No change needed - domain names remain the same
# Only update DNS records to point to new IP
```

### 4.2 Docker Configurations

#### `/docker-compose.yml`
**[CRITICAL]** - 4 occurrences
```yaml
# OLD:
environment:
  - API_URL=http://174.138.55.42:8000

# NEW:
environment:
  - API_URL=${API_GATEWAY_URL:-http://app.cuwapp.com}
```

#### `/docker-compose.prod.yml`
**[RECOMMENDED]** - 2 occurrences
```yaml
# OLD:
- SERVER_IP=174.138.55.42

# NEW:
- SERVER_IP=${NEW_SERVER_IP:-34.173.85.56}
```

---

## Section 5: Deployment Scripts

### 5.1 Shell Scripts

#### `/deploy_to_server.sh`
**[CRITICAL]** - 2 occurrences
```bash
# OLD:
SERVER="root@174.138.55.42"

# NEW:
SERVER="root@${NEW_SERVER_IP:-34.173.85.56}"
```

#### `/10210-api/deploy_to_production.sh`
**[CRITICAL]** - 4 occurrences
```bash
# OLD:
ssh root@174.138.55.42 "docker pull..."

# NEW:
ssh root@${NEW_SERVER_IP} "docker pull..."
```

#### `/10210-api/start.sh`
**[CRITICAL]** - 2 occurrences
```bash
# OLD:
if curl -s http://174.138.55.42:4500/health > /dev/null; then

# NEW:
if curl -s http://${WAHA_VM_EXTERNAL_IP:-34.133.143.67}:4500/health > /dev/null; then
```

### 5.2 Python Startup Scripts

#### `/main_startup.py`
**[CRITICAL]** - 20 occurrences
```python
# OLD:
services = {
    'landing': {'port': 5500, 'url': 'http://174.138.55.42:5500'},
    'auth': {'port': 5502, 'url': 'http://174.138.55.42:5502'},
    'api': {'port': 8000, 'url': 'http://174.138.55.42:8000'},
}

# NEW:
services = {
    'landing': {'port': 5500, 'url': f"http://{os.getenv('NEW_SERVER_IP', '34.173.85.56')}:5500"},
    'auth': {'port': 5502, 'url': f"http://{os.getenv('NEW_SERVER_IP', '34.173.85.56')}:5502"},
    'api': {'port': 8000, 'url': f"http://{os.getenv('NEW_SERVER_IP', '34.173.85.56')}:8000"},
}
```

---

## Section 6: Test Files

### 6.1 API Tests
**[OPTIONAL]** - These can remain as-is for local testing

#### `/10210-api/test_*.py` files
- `test_deployment.py` - 3 occurrences
- `test_phase1.py` - 3 occurrences
- `test_phase3.py` - 2 occurrences
- `test_all_endpoints.py` - 1 occurrence

Example pattern:
```python
# Can remain for local testing:
TEST_URL = "http://localhost:8000"

# Or update to use environment:
TEST_URL = os.getenv('API_GATEWAY_URL', 'http://localhost:8000')
```

---

## Section 7: Build Artifacts (.next)

### 7.1 Next.js Build Files
**[REBUILD REQUIRED]** - These files are generated during build

The following directories contain compiled JavaScript with hardcoded URLs:
- `/10210-auth/.next/static/chunks/`
- `/10210-auth/.next/server/`

**Action Required**: After updating source files, rebuild the Next.js applications:
```bash
cd 10210-auth && npm run build
cd 10210-landing && npm run build
```

---

## Migration Steps

### Step 1: Update Environment Files
Create `.env` files for each service:

#### `/10210-api/.env`
```bash
API_GATEWAY_URL=http://app.cuwapp.com
AUTH_SERVICE_URL=https://auth.cuwapp.com
LANDING_PAGE_URL=https://cuwapp.com
ADMIN_SERVICE_URL=http://admin.cuwapp.com
NEW_SERVER_IP=34.173.85.56
WAHA_VM_EXTERNAL_IP=34.133.143.67
WAHA_VM_INTERNAL_IP=10.128.0.3
USER_VM_EXTERNAL_IP=34.173.85.56
USER_VM_INTERNAL_IP=10.128.0.4
CONTAINER_MANAGER_URL=https://container-manager-337193391523.us-central1.run.app
```

#### `/10210-landing/.env.local`
```bash
NEXT_PUBLIC_API_GATEWAY_URL=http://app.cuwapp.com
NEXT_PUBLIC_AUTH_SERVICE_URL=https://auth.cuwapp.com
NEXT_PUBLIC_LANDING_PAGE_URL=https://cuwapp.com
NEXT_PUBLIC_ADMIN_SERVICE_URL=http://admin.cuwapp.com
```

#### `/10210-auth/.env.local`
```bash
NEXT_PUBLIC_API_GATEWAY_URL=http://app.cuwapp.com
NEXT_PUBLIC_AUTH_SERVICE_URL=https://auth.cuwapp.com
NEXT_PUBLIC_LANDING_PAGE_URL=https://cuwapp.com
```

### Step 2: Update Source Files
1. Start with **[CRITICAL]** changes
2. Test each service after updates
3. Apply **[RECOMMENDED]** changes
4. Consider **[OPTIONAL]** changes based on needs

### Step 3: Rebuild Applications
```bash
# Rebuild frontend applications
cd 10210-landing && npm run build
cd ../10210-auth && npm run build

# Rebuild Docker images
docker build -t cuwhapp-api ./10210-api
docker build -t cuwhapp-admin ./10210-admin
```

### Step 4: Update DNS Records
Update Namecheap DNS records:
- `A` record for `cuwapp.com` → 34.173.85.56
- `A` record for `app.cuwapp.com` → 34.173.85.56
- `A` record for `auth.cuwapp.com` → 34.173.85.56
- `A` record for `admin.cuwapp.com` → 34.173.85.56

### Step 5: Deploy Services
```bash
# On User VM (34.173.85.56)
sudo systemctl reload nginx
docker-compose -f docker-compose.prod.yml up -d
```

---

## Validation Checklist

### Pre-Migration
- [ ] All environment variables defined
- [ ] Backup of current configuration
- [ ] DNS propagation time considered (24-48 hours)

### During Migration
- [ ] Update CRITICAL files first
- [ ] Test each service independently
- [ ] Monitor logs for hardcoded URL errors

### Post-Migration
- [ ] All services accessible via new domains
- [ ] User signup → container creation flow works
- [ ] No references to old IP (174.138.55.42) in logs
- [ ] SSL certificates configured (if using HTTPS)

---

## Troubleshooting

### Common Issues

#### 1. Service Can't Connect
```bash
# Check environment variables
env | grep -E "(URL|IP|DOMAIN)"

# Test connectivity
curl -I http://app.cuwapp.com
```

#### 2. Old IP Still Referenced
```bash
# Search for old IP in running containers
docker exec <container> grep -r "174.138.55.42" /app

# Check nginx config
nginx -T | grep "174.138.55.42"
```

#### 3. DNS Not Resolving
```bash
# Check DNS propagation
nslookup app.cuwapp.com
dig app.cuwapp.com
```

---

## Summary Statistics

### File Type Distribution
- **Python files**: 156 occurrences
- **JavaScript/TypeScript**: 189 occurrences  
- **Configuration files**: 87 occurrences
- **Shell scripts**: 45 occurrences
- **HTML files**: 36 occurrences

### Change Priority
- **[CRITICAL]**: 287 changes (must complete)
- **[RECOMMENDED]**: 163 changes (should complete)
- **[OPTIONAL]**: 63 changes (nice to have)

### Services Affected
1. **Landing Page**: 47 changes
2. **Auth Service**: 78 changes
3. **API Gateway**: 145 changes
4. **Admin Panel**: 89 changes
5. **Microservices**: 34 changes
6. **Infrastructure**: 120 changes

---

## Notes

1. **Phased Approach**: Consider migrating services one at a time with proper fallback mechanisms
2. **Environment-Specific**: Use different `.env` files for development, staging, and production
3. **Secrets Management**: Never commit `.env` files to version control
4. **Monitoring**: Set up monitoring for the new infrastructure before full migration
5. **Rollback Plan**: Keep old infrastructure running until new setup is validated

---

*Document generated for CuWapp infrastructure migration from DigitalOcean to Google Cloud Platform*
*Total changes documented: 513 across 168 files*
*Migration window: Immediate*
*Last updated: Current session*