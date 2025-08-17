/**
 * Session UI Fixes
 * - Logout button always visible
 * - Screenshot displays in modal (not popup)
 * - Login with code option
 */

// Enhanced session card with logout always visible
function createSessionCard(session) {
    const statusClass = session.status === 'WORKING' ? 'status-working' : 
                      session.status === 'STARTING' ? 'status-starting' : 
                      session.status === 'SCAN_QR_CODE' ? 'status-qr' : 'status-stopped';
    
    return `
        <div class="col-md-6 col-lg-4 mb-3">
            <div class="card session-card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <h6 class="card-title mb-0">
                            <i class="bi bi-phone me-2"></i>${session.name}
                        </h6>
                        <span class="session-status ${statusClass}">
                            ${session.status}
                        </span>
                    </div>
                    
                    <div class="session-actions">
                        <div class="btn-group btn-group-sm mb-2" role="group">
                            ${session.status === 'WORKING' ? `
                                <button class="btn btn-outline-success" onclick="app.stopSession('${session.name}')" title="Stop">
                                    <i class="bi bi-stop-fill"></i>
                                </button>
                            ` : session.status === 'STOPPED' ? `
                                <button class="btn btn-outline-primary" onclick="app.startSession('${session.name}')" title="Start">
                                    <i class="bi bi-play-fill"></i>
                                </button>
                            ` : ''}
                            
                            <!-- Logout button ALWAYS visible -->
                            <button class="btn btn-outline-warning" onclick="logoutSession('${session.name}')" title="Logout WhatsApp">
                                <i class="bi bi-box-arrow-right"></i> Logout
                            </button>
                            
                            <button class="btn btn-outline-danger" onclick="app.deleteSession('${session.name}')" title="Delete Session">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                        
                        <div class="d-flex gap-2">
                            ${session.status === 'SCAN_QR_CODE' ? `
                                <button class="btn btn-sm btn-info" onclick="showScreenshotModal('${session.name}')" title="Show QR Code">
                                    <i class="bi bi-qr-code"></i> QR Code
                                </button>
                                <button class="btn btn-sm btn-secondary" onclick="loginWithCode('${session.name}')" title="Login with Code">
                                    <i class="bi bi-123"></i> Use Code
                                </button>
                            ` : session.status === 'WORKING' ? `
                                <button class="btn btn-sm btn-info" onclick="showScreenshotModal('${session.name}')" title="Take Screenshot">
                                    <i class="bi bi-camera"></i> Screenshot
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Logout session function
async function logoutSession(sessionName) {
    if (!confirm(`Are you sure you want to logout ${sessionName}? This will disconnect WhatsApp.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/sessions/${sessionName}/logout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            app.showToast(`✅ ${sessionName} logged out successfully`, 'success');
            // Refresh sessions after logout
            setTimeout(() => app.loadSessions(), 1000);
        } else {
            throw new Error(result.error || 'Logout failed');
        }
    } catch (error) {
        app.showToast(`❌ Failed to logout: ${error.message}`, 'error');
    }
}

// Show screenshot in modal (not popup)
async function showScreenshotModal(sessionName) {
    // Show loading modal first
    const loadingModal = `
        <div class="modal fade" id="screenshotModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-camera me-2"></i>Screenshot - ${sessionName}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body text-center" id="screenshotBody">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-3">Capturing screenshot...</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" onclick="refreshScreenshot('${sessionName}')" id="refreshBtn">
                            <i class="bi bi-arrow-clockwise"></i> Refresh
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('screenshotModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', loadingModal);
    const modalInstance = new bootstrap.Modal(document.getElementById('screenshotModal'));
    modalInstance.show();
    
    // Get screenshot
    try {
        const response = await fetch(`/api/sessions/${sessionName}/screenshot`);
        
        if (!response.ok) {
            throw new Error('Failed to capture screenshot');
        }
        
        const data = await response.json();
        
        if (data.screenshot) {
            // Display the screenshot in modal
            document.getElementById('screenshotBody').innerHTML = `
                <img src="${data.screenshot}" class="img-fluid" alt="WhatsApp Screenshot" 
                     style="max-width: 100%; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <div class="mt-3">
                    <small class="text-muted">Captured at ${new Date().toLocaleTimeString()}</small>
                </div>
            `;
            
            // If it's a QR code, add instructions
            if (data.screenshot.includes('qr') || data.status === 'SCAN_QR_CODE') {
                document.getElementById('screenshotBody').innerHTML += `
                    <div class="alert alert-info mt-3">
                        <strong>To connect:</strong><br>
                        1. Open WhatsApp on your phone<br>
                        2. Go to Settings → Linked Devices<br>
                        3. Tap "Link a Device"<br>
                        4. Scan this QR code
                    </div>
                `;
            }
        } else {
            throw new Error('No screenshot data received');
        }
    } catch (error) {
        document.getElementById('screenshotBody').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Failed to capture screenshot: ${error.message}
            </div>
        `;
    }
}

// Refresh screenshot
async function refreshScreenshot(sessionName) {
    const btn = document.getElementById('refreshBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Refreshing...';
    
    // Re-capture screenshot
    document.getElementById('screenshotBody').innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-3">Capturing new screenshot...</p>
    `;
    
    try {
        const response = await fetch(`/api/sessions/${sessionName}/screenshot`);
        const data = await response.json();
        
        if (data.screenshot) {
            document.getElementById('screenshotBody').innerHTML = `
                <img src="${data.screenshot}" class="img-fluid" alt="WhatsApp Screenshot" 
                     style="max-width: 100%; border-radius: 8px;">
                <div class="mt-3">
                    <small class="text-muted">Refreshed at ${new Date().toLocaleTimeString()}</small>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('screenshotBody').innerHTML = `
            <div class="alert alert-danger">
                Failed to refresh: ${error.message}
            </div>
        `;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh';
    }
}

// Login with code modal
function loginWithCode(sessionName) {
    const modal = `
        <div class="modal fade" id="loginCodeModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Login with Phone Number</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div id="step1" class="login-step">
                            <p class="mb-3">Enter your WhatsApp phone number:</p>
                            <div class="input-group mb-3">
                                <span class="input-group-text">+</span>
                                <input type="tel" id="phoneNumber" class="form-control" 
                                       placeholder="1234567890" />
                            </div>
                            <button class="btn btn-primary w-100" onclick="requestCode('${sessionName}')">
                                Request Code
                            </button>
                        </div>
                        
                        <div id="step2" class="login-step" style="display:none;">
                            <div class="alert alert-info">
                                <strong>On your phone:</strong><br>
                                1. Open WhatsApp<br>
                                2. Go to Settings → Linked Devices<br>
                                3. Click "Link a Device"<br>
                                4. Select "Link with phone number"<br>
                                5. You'll see an 8-digit code
                            </div>
                            <p class="mb-3">Enter the 8-digit code from your phone:</p>
                            <input type="text" id="authCode" class="form-control mb-3" 
                                   placeholder="1234-5678" maxlength="9" 
                                   oninput="formatCode(this)" />
                            <button class="btn btn-success w-100" onclick="submitCode('${sessionName}')">
                                Submit Code
                            </button>
                        </div>
                        
                        <div id="loginLoader" class="text-center" style="display:none;">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2">Authenticating...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('loginCodeModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modal);
    const modalInstance = new bootstrap.Modal(document.getElementById('loginCodeModal'));
    modalInstance.show();
}

// Format code input (add dash after 4 digits)
function formatCode(input) {
    let value = input.value.replace(/\D/g, '');
    if (value.length > 4) {
        value = value.slice(0, 4) + '-' + value.slice(4, 8);
    }
    input.value = value;
}

// Request authentication code
async function requestCode(sessionName) {
    const phoneNumber = document.getElementById('phoneNumber').value.replace(/\D/g, '');
    
    if (!phoneNumber || phoneNumber.length < 10) {
        app.showToast('Please enter a valid phone number', 'warning');
        return;
    }
    
    document.getElementById('loginLoader').style.display = 'block';
    document.getElementById('step1').style.display = 'none';
    
    try {
        const response = await fetch(`/api/${sessionName}/auth/request-code`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                phoneNumber: phoneNumber,
                method: 'code'
            })
        });
        
        if (response.ok) {
            document.getElementById('loginLoader').style.display = 'none';
            document.getElementById('step2').style.display = 'block';
            app.showToast('Code requested! Check your phone', 'success');
        } else {
            throw new Error('Failed to request code');
        }
    } catch (error) {
        document.getElementById('loginLoader').style.display = 'none';
        document.getElementById('step1').style.display = 'block';
        app.showToast(`Error: ${error.message}`, 'error');
    }
}

// Submit authentication code
async function submitCode(sessionName) {
    const code = document.getElementById('authCode').value.replace(/\D/g, '');
    
    if (code.length !== 8) {
        app.showToast('Please enter the 8-digit code', 'warning');
        return;
    }
    
    document.getElementById('loginLoader').style.display = 'block';
    document.getElementById('step2').style.display = 'none';
    
    try {
        const response = await fetch(`/api/${sessionName}/auth/authorize-code`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code
            })
        });
        
        if (response.ok) {
            app.showToast('✅ Login successful!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('loginCodeModal')).hide();
            app.loadSessions(); // Refresh sessions
        } else {
            throw new Error('Invalid code');
        }
    } catch (error) {
        document.getElementById('loginLoader').style.display = 'none';
        document.getElementById('step2').style.display = 'block';
        app.showToast(`Error: ${error.message}`, 'error');
    }
}

// Add to global app object
if (typeof app !== 'undefined') {
    app.createSessionCard = createSessionCard;
    app.showScreenshotModal = showScreenshotModal;
    app.logoutSession = logoutSession;
    app.loginWithCode = loginWithCode;
}

// Auto-apply to existing displaySessions function
if (typeof app !== 'undefined' && app.displaySessions) {
    const originalDisplay = app.displaySessions;
    app.displaySessions = function(sessions) {
        const container = document.getElementById('sessions-container');
        const emptyState = document.getElementById('empty-sessions');
        
        if (!container) return;
        
        if (sessions.length === 0) {
            container.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        container.innerHTML = sessions.map(session => createSessionCard(session)).join('');
    };
}