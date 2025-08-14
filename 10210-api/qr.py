#!/usr/bin/env python3
"""
WAHA QR Code Module - Production Version
Clean module to get WhatsApp QR code bytes with smart session handling
"""

import requests
import time
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class QRCodeError(Exception):
    """Custom exception for QR code related errors"""
    pass

def get_qr_code(base_url: str, 
                session_name: str,
                api_key: Optional[str] = None,
                max_wait_seconds: int = 60) -> bytes:
    """
    Get WhatsApp QR code with intelligent session state handling
    
    Args:
        base_url: WAHA server base URL
        session_name: WhatsApp session name
        api_key: Optional API key for authentication
        max_wait_seconds: Maximum time to wait for session to be ready
        
    Returns:
        bytes: PNG image data of QR code
        
    Raises:
        QRCodeError: If unable to get QR code
    """
    
    # Setup headers
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-KEY"] = api_key
    
    base_url = base_url.rstrip('/')
    
    def make_request(method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling"""
        url = f"{base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {method} {endpoint} - {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"Error details: {error_data}")
                except:
                    logger.error(f"Error response: {e.response.text}")
            raise QRCodeError(f"API request failed: {e}")
    
    def get_session_status() -> Tuple[str, dict]:
        """Get current session status"""
        try:
            response = make_request("GET", f"/api/sessions/{session_name}")
            session_info = response.json()
            status = session_info.get('status', 'UNKNOWN')
            logger.info(f"Session {session_name} status: {status}")
            return status, session_info
        except QRCodeError as e:
            if "404" in str(e):
                logger.info(f"Session {session_name} doesn't exist")
                return "NOT_EXISTS", {}
            raise
    
    def create_and_start_session() -> None:
        """Create and start session"""
        logger.info(f"Creating session {session_name}...")
        payload = {
            "name": session_name,
            "start": True,
            "config": {
                "proxy": None,
                "webhooks": [],
                "debug": False
            }
        }
        make_request("POST", "/api/sessions", json=payload)
        logger.info(f"Session {session_name} created and starting...")
    
    def start_existing_session() -> None:
        """Start existing session"""
        logger.info(f"Starting session {session_name}...")
        make_request("POST", f"/api/sessions/{session_name}/start")
        logger.info(f"Session {session_name} start command sent")
    
    def wait_for_qr_ready_state() -> None:
        """Wait for session to reach QR-ready state"""
        logger.info(f"Waiting for session {session_name} to be ready for QR code...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_seconds:
            status, _ = get_session_status()
            
            if status == "SCAN_QR_CODE":
                logger.info(f"Session {session_name} is ready for QR code!")
                return
            elif status in ["STARTING", "WORKING"]:
                logger.info(f"Session {session_name} is {status}, waiting...")
                time.sleep(2)
            else:
                logger.warning(f"Session {session_name} in unexpected state: {status}")
                time.sleep(2)
        
        raise QRCodeError(f"Session did not reach QR-ready state within {max_wait_seconds} seconds")
    
    def fetch_qr_code() -> bytes:
        """Fetch QR code binary data"""
        logger.info("Fetching QR code...")
        response = make_request("GET", f"/api/{session_name}/auth/qr?format=image")
        
        if response.headers.get('content-type') != 'image/png':
            logger.warning(f"Unexpected content type: {response.headers.get('content-type')}")
        
        qr_data = response.content
        logger.info(f"QR code fetched successfully ({len(qr_data)} bytes)")
        return qr_data
    
    # =============================================================================
    # MAIN LOGIC
    # =============================================================================
    
    try:
        logger.info(f"Getting QR code for session '{session_name}'...")
        
        # Step 1: Check current session status
        status, session_info = get_session_status()
        
        # Step 2: Handle session state intelligently
        if status == "SCAN_QR_CODE":
            logger.info("Session already in QR scan mode!")
        
        elif status == "STARTING":
            logger.info("Session is starting, waiting for QR scan mode...")
            wait_for_qr_ready_state()
        
        elif status == "NOT_EXISTS":
            logger.info("Session doesn't exist, creating new session...")
            create_and_start_session()
            wait_for_qr_ready_state()
        
        elif status in ["STOPPED", "FAILED", "WORKING"]:
            logger.info(f"Session is {status}, starting session...")
            start_existing_session()
            wait_for_qr_ready_state()
        
        else:
            logger.warning(f"Unknown session status: {status}, attempting to start...")
            start_existing_session()
            wait_for_qr_ready_state()
        
        # Step 3: Fetch QR code
        qr_data = fetch_qr_code()
        
        logger.info("QR code retrieved successfully!")
        return qr_data
        
    except Exception as e:
        logger.error(f"Failed to get QR code: {e}")
        raise QRCodeError(f"Failed to get QR code: {e}")