# Google Social Login 500 Error - Fix Summary

## Problem
The endpoint `http://localhost:3000/api/v1/auth/social/google/` was returning a 500 Internal Server Error when accessed through Docker Compose.

## Root Cause
The Vite development server's proxy configuration was hardcoded to `http://localhost:8000`, which doesn't work inside Docker containers. In Docker Compose, services communicate using service names (e.g., `backend`) instead of `localhost`.

## Solution

### 1. Fixed Vite Proxy Configuration
**File: `frontend/vite.config.ts`**
- Made the proxy target configurable via environment variable
- Added fallback to `localhost:8000` for local development
- Changed from: `target: 'http://localhost:8000'`
- Changed to: `target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'`

### 2. Updated Docker Compose Configuration
**File: `docker-compose.yml`**
- Added `VITE_API_PROXY_TARGET=http://backend:8000` to frontend service environment
- Removed deprecated `version: '3'` field
- Frontend now correctly proxies requests to the backend service

### 3. Created Social Auth Setup Management Command
**File: `frontend_server/translator/management/commands/setup_social_auth.py`**
- Created Django management command to automatically configure OAuth providers
- Reads `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from environment
- Creates SocialApp entries in the database

### 4. Updated Backend Dockerfile
**File: `frontend_server/Dockerfile.py`**
- Added automatic execution of `setup_social_auth` on container startup
- Command sequence: migrate → setup_social_auth → runserver

### 5. Updated Documentation
**File: `skills/cloud_agents_starter_skill.md`**
- Added troubleshooting entry for social login 500 errors
- Documented the docker-compose proxy configuration requirement
- Added OAuth setup instructions

## Testing
After the fix:
- ✅ `curl http://localhost:3000/api/v1/auth/social/google/` returns HTTP 302 (correct redirect)
- ✅ No proxy errors in frontend logs
- ✅ Google OAuth provider configured in database
- ✅ Frontend successfully proxies API requests to backend

## Benefits
1. **Works in Docker Compose**: Services can communicate properly using service names
2. **Backward Compatible**: Still works for local development using localhost
3. **Automatic Setup**: OAuth providers are configured on container startup
4. **Environment-Driven**: Configuration is pulled from environment variables
5. **Production Ready**: Fix applies to both development and production deployments
