// Helper function to get dynamic URL for API calls
function getDynamicUrl(endpoint) {
    const infrastructure = JSON.parse(localStorage.getItem('user_infrastructure') || '{}');
    let baseUrl = '';
    
    // Determine which service URL to use based on endpoint
    if (endpoint.includes('/api/warmer')) {
        baseUrl = sessionStorage.getItem('WARMER_URL') || infrastructure.warmerUrl || '';
    } else if (endpoint.includes('/api/campaign')) {
        baseUrl = sessionStorage.getItem('CAMPAIGN_URL') || infrastructure.campaignUrl || '';
    } else {
        baseUrl = sessionStorage.getItem('API_URL') || infrastructure.apiUrl || '';
    }
    
    // Return full URL if we have baseUrl, otherwise return relative URL
    return baseUrl ? `${baseUrl}${endpoint}` : endpoint;
}

// WhatsApp Agent Frontend Application
class WhatsAppAgent {
    constructor() {
        this.currentSession = null;
        this.currentChat = null;
        this.pollingInterval = null;
        this.sessions = [];
        this.userSubscription = null;
        this.userId = this.getUserId();  // Get user ID from URL or storage
        this.init();
        this.loadUserSubscription();
    }
    
    getUserId() {
        // Get user ID from UserCache first (most reliable source)
        const cachedUser = UserCache.getUser();
        if (cachedUser && cachedUser.id) {
            // Save to localStorage for analytics page
            localStorage.setItem('userId', cachedUser.id);
            return cachedUser.id;
        }
        
        // Fallback: Check URL parameters (for testing)
        const urlParams = new URLSearchParams(window.location.search);
        const userIdFromUrl = urlParams.get('user_id');
        if (userIdFromUrl) {
            // Save to localStorage for analytics page
            localStorage.setItem('userId', userIdFromUrl);
            return userIdFromUrl;
        }
        
        // Check localStorage as last resort
        const storedUserId = localStorage.getItem('userId');
        if (storedUserId) {
            return storedUserId;
        }
        
        // Return null if no user ID found (admin mode)
        return null;
    }
    
    // ==================== CAMPAIGN ACTIONS ====================
    
    async startCampaign(campaignId) {
        try {
            await this.apiCall(`/api/campaigns/${campaignId}/start`, { method: 'POST' });
            this.showToast('Campaign started successfully', 'success');
            this.loadCampaigns();
            this.loadProcessingStatus();
        } catch (error) {
            console.error('Error starting campaign:', error);
            this.showToast('Failed to start campaign', 'error');
        }
    }
    
    async pauseCampaign(campaignId) {
        try {
            await this.apiCall(`/api/campaigns/${campaignId}/pause`, { method: 'POST' });
            this.showToast('Campaign paused successfully', 'success');
            this.loadCampaigns();
            this.loadProcessingStatus();
        } catch (error) {
            console.error('Error pausing campaign:', error);
            this.showToast('Failed to pause campaign', 'error');
        }
    }
    
    async resumeCampaign(campaignId) {
        try {
            await this.apiCall(`/api/campaigns/${campaignId}/start`, { method: 'POST' });
            this.showToast('Campaign resumed successfully', 'success');
            this.loadCampaigns();
            this.loadProcessingStatus();
        } catch (error) {
            console.error('Error resuming campaign:', error);
            this.showToast('Failed to resume campaign', 'error');
        }
    }
    
    async stopCampaign(campaignId) {
        if (!confirm('Are you sure you want to stop this campaign? This action cannot be undone.')) {
            return;
        }
        
        try {
            await this.apiCall(`/api/campaigns/${campaignId}/stop`, { method: 'POST' });
            this.showToast('Campaign stopped successfully', 'success');
            this.loadCampaigns();
            this.loadProcessingStatus();
        } catch (error) {
            console.error('Error stopping campaign:', error);
            this.showToast('Failed to stop campaign', 'error');
        }
    }
    
    async cancelSchedule(campaignId) {
        if (!confirm('Are you sure you want to cancel the schedule for this campaign?')) {
            return;
        }
        
        try {
            // Update campaign to remove schedule
            const response = await fetch(`/api/campaigns/${campaignId}/cancel-schedule`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.getUserId()
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to cancel schedule');
            }
            
            this.showToast('Schedule cancelled successfully', 'success');
            this.loadCampaigns();
            
            // Reload campaign details
            this.selectCampaign(campaignId);
        } catch (error) {
            console.error('Error cancelling schedule:', error);
            this.showToast('Failed to cancel schedule', 'error');
        }
    }
    
    async deleteCampaign(campaignId) {
        if (!confirm('Are you sure you want to delete this campaign? All data will be lost.')) {
            return;
        }
        
        try {
            await this.apiCall(`/api/campaigns/${campaignId}`, { method: 'DELETE' });
            this.showToast('Campaign deleted successfully', 'success');
            this.loadCampaigns();
            
            // Clear campaign controls
            document.getElementById('campaign-controls').innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-hand-index display-4"></i>
                    <p class="mt-3">Select a campaign to view controls</p>
                </div>
            `;
        } catch (error) {
            console.error('Error deleting campaign:', error);
            this.showToast('Failed to delete campaign', 'error');
        }
    }
    
    async showRestartCampaignModal(campaignId) {
        try {
            // Fetch campaign details
            const response = await this.apiCall(`/api/campaigns/${campaignId}`);
            const campaign = response.data || response;
            
            // Store campaign ID for restart
            this.restartCampaignId = campaignId;
            
            // Update modal with campaign info
            const infoDiv = document.getElementById('restart-campaign-info');
            infoDiv.innerHTML = `
                <div><strong>Name:</strong> ${campaign.name}</div>
                <div><strong>Total Rows:</strong> ${campaign.total_rows}</div>
                <div><strong>Processed:</strong> ${campaign.processed_rows}</div>
                <div><strong>Success:</strong> ${campaign.success_count}</div>
                <div><strong>Failed:</strong> ${(campaign.processed_rows || 0) - (campaign.success_count || 0)}</div>
            `;
            
            // Set default starting row (next unprocessed row)
            const nextRow = (campaign.processed_rows || 0) + 1;
            document.getElementById('restart-start-row').value = nextRow;
            document.getElementById('restart-start-row').max = campaign.total_rows;
            
            // Set stop row max value
            document.getElementById('restart-stop-row').max = campaign.total_rows;
            document.getElementById('restart-stop-row').placeholder = `Leave empty for all rows (max: ${campaign.total_rows})`;
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('restartCampaignModal'));
            modal.show();
            
        } catch (error) {
            console.error('Error loading campaign for restart:', error);
            this.showToast('Failed to load campaign details', 'error');
        }
    }
    
    async restartCampaign() {
        const campaignId = this.restartCampaignId;
        if (!campaignId) return;
        
        const startRow = parseInt(document.getElementById('restart-start-row').value);
        const stopRow = document.getElementById('restart-stop-row').value ? 
                       parseInt(document.getElementById('restart-stop-row').value) : null;
        const skipProcessed = document.getElementById('restart-skip-processed').checked;
        const saveContact = document.getElementById('restart-save-contact').checked;
        
        if (!startRow || startRow < 1) {
            this.showToast('Please enter a valid starting row number', 'warning');
            return;
        }
        
        if (stopRow && stopRow < startRow) {
            this.showToast('Stop row must be greater than or equal to start row', 'warning');
            return;
        }
        
        try {
            // Call restart endpoint
            const response = await this.apiCall(`/api/campaigns/${campaignId}/restart`, {
                method: 'POST',
                body: JSON.stringify({
                    start_row: startRow,
                    stop_row: stopRow,
                    skip_processed: skipProcessed,
                    save_contact_before_message: saveContact
                })
            });
            
            if (response.success) {
                this.showToast('Campaign restarted successfully', 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('restartCampaignModal'));
                modal.hide();
                
                // Reload campaigns
                this.loadCampaigns();
                
                // Select the new campaign
                if (response.new_campaign_id) {
                    setTimeout(() => {
                        this.selectCampaign(response.new_campaign_id);
                    }, 500);
                }
            }
        } catch (error) {
            console.error('Error restarting campaign:', error);
            this.showToast('Failed to restart campaign: ' + (error.message || 'Unknown error'), 'error');
        }
    }
    
    async viewCampaignReport(campaignId) {
        try {
            // Fetch detailed campaign report
            const response = await this.apiCall(`/api/campaigns/${campaignId}/report`);
            
            if (!response.success || !response.data) {
                throw new Error('Failed to load campaign report');
            }
            
            const report = response.data;
            
            // Create modal HTML
            const modalHtml = `
                <div class="modal fade" id="campaignReportModal" tabindex="-1">
                    <div class="modal-dialog modal-xl">
                        <div class="modal-content">
                            <div class="modal-header bg-info text-white">
                                <h5 class="modal-title">
                                    <i class="bi bi-file-text me-2"></i>Campaign Report: ${report.name}
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <h6 class="text-primary mb-3">Campaign Information</h6>
                                        <table class="table table-sm">
                                            <tr>
                                                <td class="text-muted">Status:</td>
                                                <td><span class="badge bg-${this.getStatusColor(report.status)}">${report.status.toUpperCase()}</span></td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Session:</td>
                                                <td>${report.session_name}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Session Phone:</td>
                                                <td>
                                                    ${report.session_phone ? '+' + report.session_phone : 'Not available'}
                                                    ${report.session_phone_name ? ' (' + report.session_phone_name + ')' : ''}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Message Mode:</td>
                                                <td>${report.message_mode === 'multiple' ? '🎲 Multiple Samples' : '📝 Single Template'}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Delay:</td>
                                                <td>${report.delay_seconds} seconds</td>
                                            </tr>
                                            ${report.source_info ? `
                                            <tr>
                                                <td class="text-muted">Source Type:</td>
                                                <td>
                                                    <span class="badge bg-${this.getSourceTypeColor(report.source_info.source_type)}">
                                                        ${this.getSourceTypeLabel(report.source_info.source_type)}
                                                    </span>
                                                    ${report.source_info.delivery_method ? ` - ${report.source_info.delivery_method}` : ''}
                                                </td>
                                            </tr>
                                            ` : ''}
                                        </table>
                                    </div>
                                    <div class="col-md-6">
                                        <h6 class="text-primary mb-3">File Information</h6>
                                        <table class="table table-sm">
                                            <tr>
                                                <td class="text-muted">File Name:</td>
                                                <td class="fw-bold">${report.file_name}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">File Total Rows:</td>
                                                <td class="fw-bold">${report.file_total_rows || report.total_rows}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Start Row:</td>
                                                <td class="fw-bold">${report.start_row}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">End Row:</td>
                                                <td class="fw-bold">${report.end_row || 'All rows'}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Campaign Rows:</td>
                                                <td>${report.total_rows} (rows ${report.start_row} to ${report.end_row || report.file_total_rows || report.total_rows})</td>
                                            </tr>
                                        </table>
                                    </div>
                                </div>
                                
                                <hr>
                                
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <h6 class="text-primary mb-3">Progress Statistics</h6>
                                        <table class="table table-sm">
                                            <tr>
                                                <td class="text-muted">Processed:</td>
                                                <td>${report.processed_rows} / ${report.total_rows} messages</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Progress:</td>
                                                <td>
                                                    <div class="progress" style="height: 20px;">
                                                        <div class="progress-bar bg-primary" role="progressbar" style="width: ${report.progress_percentage}%">
                                                            ${report.progress_percentage}%
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Success Count:</td>
                                                <td class="text-success fw-bold">${report.success_count}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Failed Count:</td>
                                                <td class="text-danger fw-bold">${report.failed_count}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Success Rate:</td>
                                                <td>
                                                    <div class="progress" style="height: 20px;">
                                                        <div class="progress-bar bg-success" role="progressbar" style="width: ${report.success_rate}%">
                                                            ${report.success_rate}%
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </div>
                                    <div class="col-md-6">
                                        <h6 class="text-primary mb-3">Timestamps</h6>
                                        <table class="table table-sm">
                                            <tr>
                                                <td class="text-muted">Created:</td>
                                                <td>${new Date(report.created_at).toLocaleString()}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Last Updated:</td>
                                                <td>${new Date(report.updated_at).toLocaleString()}</td>
                                            </tr>
                                        </table>
                                        
                                        <div class="alert alert-info mt-3">
                                            <i class="bi bi-info-circle me-2"></i>
                                            <strong>Quick Restart Info:</strong><br>
                                            To continue processing, start from row <strong>${(report.end_row || report.total_rows || 0) + 1}</strong>
                                        </div>
                                    </div>
                                </div>
                                
                                ${report.contacts_preview && report.contacts_preview.length > 0 ? `
                                <hr>
                                <h6 class="text-primary mb-3">
                                    <i class="bi bi-people me-2"></i>Contacts Preview (First 10)
                                </h6>
                                <div class="table-responsive">
                                    <table class="table table-sm table-hover">
                                        <thead>
                                            <tr>
                                                <th>Phone Number</th>
                                                <th>Name</th>
                                                <th>Source</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${report.contacts_preview.map(contact => `
                                                <tr>
                                                    <td>${contact.phone_number}</td>
                                                    <td>${contact.name || '-'}</td>
                                                    <td>
                                                        <span class="badge bg-${this.getSourceTypeColor(contact.source_type)}">
                                                            ${this.getSourceTypeLabel(contact.source_type)}
                                                        </span>
                                                    </td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                                ` : ''}
                                
                                ${report.deliveries && report.deliveries.length > 0 ? `
                                <hr>
                                <h6 class="text-primary mb-3">
                                    <i class="bi bi-send me-2"></i>Delivery Details (${report.total_deliveries} Recipients)
                                </h6>
                                <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                                    <table class="table table-sm table-hover">
                                        <thead class="sticky-top bg-light">
                                            <tr>
                                                <th>Phone Number</th>
                                                <th>Contact Name</th>
                                                <th>Status</th>
                                                <th>Message Preview</th>
                                                <th>Delivered At</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${report.deliveries.map(delivery => `
                                                <tr>
                                                    <td>${delivery.phone_number}</td>
                                                    <td>${delivery.contact_name || '-'}</td>
                                                    <td>
                                                        ${delivery.status === 'sent' ? 
                                                            '<span class="badge bg-success">Sent</span>' : 
                                                            '<span class="badge bg-danger">Failed</span>'}
                                                        ${delivery.error_message ? `<br><small class="text-danger">${delivery.error_message}</small>` : ''}
                                                    </td>
                                                    <td>
                                                        <small class="text-muted">${delivery.message_sent || '-'}</small>
                                                    </td>
                                                    <td>
                                                        ${delivery.delivered_at ? new Date(delivery.delivered_at).toLocaleString() : '-'}
                                                    </td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                                ` : ''}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                ${report.status !== 'running' && report.status !== 'processing' ? `
                                    <button type="button" class="btn btn-warning" onclick="closeReportAndShowRestart('${campaignId}')">
                                        <i class="bi bi-arrow-clockwise"></i> Restart Campaign
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove existing modal if present
            const existingModal = document.getElementById('campaignReportModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Add modal to body
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('campaignReportModal'));
            modal.show();
            
        } catch (error) {
            console.error('Error viewing campaign report:', error);
            this.showToast('Failed to load campaign report', 'error');
        }
    }
    
    getStatusColor(status) {
        const colors = {
            'created': 'secondary',
            'queued': 'info',
            'running': 'primary',
            'processing': 'primary',
            'paused': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'dark'
        };
        return colors[status.toLowerCase()] || 'secondary';
    }
    
    getSourceTypeColor(sourceType) {
        const colors = {
            'csv': 'primary',
            'csv_upload': 'primary',
            'whatsapp_group': 'success',
            'user_contacts': 'info',
            'group_participant': 'warning',
            'contact': 'info'
        };
        return colors[sourceType?.toLowerCase()] || 'secondary';
    }
    
    getSourceTypeLabel(sourceType) {
        const labels = {
            'csv': '📁 CSV Upload',
            'csv_upload': '📁 CSV Upload',
            'whatsapp_group': '👥 WhatsApp Group',
            'user_contacts': '📱 User Contacts',
            'group_participant': '👤 Group Member',
            'contact': '📱 Contact'
        };
        return labels[sourceType?.toLowerCase()] || sourceType || 'Unknown';
    }
    
    // ==================== CAMPAIGN WIZARD ====================
    
    currentWizardStep = 1;
    uploadedFileData = null;
    
    modalNextStep() {
        if (!this.validateCurrentStep()) {
            console.log('Validation failed for step', this.currentWizardStep);
            // Show what's missing
            if (this.currentWizardStep === 1) {
                const name = document.getElementById('modal-campaign-name').value;
                const session = document.getElementById('modal-campaign-session').value;
                const sourceType = document.getElementById('modal-contact-source')?.value;
                
                if (!name) {
                    this.showToast('Please enter a campaign name', 'warning');
                } else if (!session) {
                    this.showToast('Please select a WhatsApp session', 'warning');
                } else if (!sourceType) {
                    this.showToast('Please select a contact source', 'warning');
                } else if (sourceType === 'whatsapp_groups') {
                    const selectedGroups = document.querySelectorAll('.group-select-checkbox:checked');
                    if (selectedGroups.length === 0) {
                        this.showToast('Please select at least one group', 'warning');
                    }
                } else if (sourceType === 'my_contacts') {
                    const contactSelection = document.querySelector('input[name="contact-selection"]:checked')?.value;
                    if (contactSelection === 'specific') {
                        const selectedContacts = document.querySelectorAll('.contact-select-checkbox:checked');
                        if (selectedContacts.length === 0) {
                            this.showToast('Please select at least one contact', 'warning');
                        }
                    }
                } else if (sourceType === 'csv') {
                    const file = document.getElementById('modal-campaign-file').files[0];
                    if (!file) {
                        this.showToast('Please upload a CSV file', 'warning');
                    } else if (!this.uploadedFileData) {
                        // File selected but not uploaded yet, trigger upload
                        this.handleModalFileUpload();
                    }
                }
            }
            return;
        }
        
        if (this.currentWizardStep >= 4) return;
        
        const sourceType = document.getElementById('modal-contact-source')?.value;
        
        // Move to next step
        this.currentWizardStep++;
        
        this.updateWizardStepIndicators();
        this.showWizardStep(this.currentWizardStep);
    }
    
    modalPrevStep() {
        if (this.currentWizardStep > 1) {
            this.currentWizardStep--;
            this.updateWizardStepIndicators();
            this.showWizardStep(this.currentWizardStep);
        }
    }
    
    validateCurrentStep() {
        switch (this.currentWizardStep) {
            case 1:
                const name = document.getElementById('modal-campaign-name').value;
                const session = document.getElementById('modal-campaign-session').value;
                const sourceType = document.getElementById('modal-contact-source')?.value;
                
                if (!name || !session || !sourceType) {
                    return false;
                }
                
                // Validate based on source type
                if (sourceType === 'csv') {
                    const file = document.getElementById('modal-campaign-file').files[0];
                    return !!file;
                } else if (sourceType === 'whatsapp_groups') {
                    const selectedGroups = document.querySelectorAll('.group-select-checkbox:checked');
                    return selectedGroups.length > 0;
                } else if (sourceType === 'my_contacts') {
                    const contactSelection = document.querySelector('input[name="contact-selection"]:checked')?.value;
                    if (contactSelection === 'specific') {
                        const selectedContacts = document.querySelectorAll('.contact-select-checkbox:checked');
                        return selectedContacts.length > 0;
                    }
                    return true;
                }
                return false;
                
            case 2:
                // Column mapping is only required for CSV source
                const currentSourceType = document.getElementById('modal-contact-source')?.value;
                if (currentSourceType === 'csv') {
                    // Check if phone number column is mapped
                    const phoneMapping = document.getElementById('mapping-phone')?.value;
                    return this.uploadedFileData && this.uploadedFileData.valid && phoneMapping;
                }
                // For other sources, step 2 is always valid (just shows data preview)
                return true;
                
            case 3:
                // Check if at least one message template/sample exists
                const mode = document.querySelector('input[name="modalMessageMode"]:checked')?.value;
                if (mode === 'single') {
                    const template = document.getElementById('modal-single-template')?.value;
                    return template && template.trim().length > 0;
                } else {
                    const samples = document.querySelectorAll('.modal-sample-text');
                    return samples.length > 0 && Array.from(samples).some(s => s.value.trim().length > 0);
                }
            case 4:
                // For step 4, validate all previous steps
                // Temporarily set step to validate each previous step
                let allValid = true;
                for (let i = 1; i <= 3; i++) {
                    const prevStep = this.currentWizardStep;
                    this.currentWizardStep = i;
                    if (!this.validateCurrentStep()) {
                        allValid = false;
                    }
                    this.currentWizardStep = prevStep;
                }
                return allValid;
            default:
                return false;
        }
    }
    
    updateWizardStepIndicators() {
        for (let i = 1; i <= 4; i++) {
            const indicator = document.getElementById(`step-indicator-${i}`);
            if (!indicator) continue;
            
            const badge = indicator.querySelector('.badge');
            
            indicator.classList.remove('active', 'completed');
            badge.classList.remove('bg-primary', 'bg-success', 'bg-secondary');
            
            if (i < this.currentWizardStep) {
                indicator.classList.add('completed');
                badge.classList.add('bg-success');
            } else if (i === this.currentWizardStep) {
                indicator.classList.add('active');
                badge.classList.add('bg-primary');
            } else {
                badge.classList.add('bg-secondary');
            }
        }
    }
    
    showWizardStep(stepNumber) {
        // Hide all steps
        document.querySelectorAll('.wizard-step').forEach(step => {
            step.style.display = 'none';
        });
        
        // Show current step
        const currentStep = document.getElementById(`step-${stepNumber}`);
        if (currentStep) {
            currentStep.style.display = 'block';
        }
        
        // If showing step 4, generate summary
        if (stepNumber === 4) {
            this.generateCampaignSummary();
        }
        
        // Update buttons
        this.updateWizardButtons();
        
        // Add input listeners based on step
        if (stepNumber === 1) {
            // Add listeners to step 1 inputs to update button state
            const nameInput = document.getElementById('modal-campaign-name');
            const sessionSelect = document.getElementById('modal-campaign-session');
            const sourceSelect = document.getElementById('modal-contact-source');
            
            if (nameInput) {
                nameInput.oninput = () => this.updateWizardButtons();
            }
            if (sessionSelect) {
                sessionSelect.onchange = () => {
                    this.loadSourceOptions();
                    this.updateWizardButtons();
                };
            }
            if (sourceSelect) {
                sourceSelect.onchange = () => {
                    this.toggleSourceOptions();
                    this.updateWizardButtons();
                };
            }
        } else if (stepNumber === 2) {
            // Show appropriate data mapping for the selected source
            this.populateDataMapping();
        } else if (stepNumber === 3) {
            // Add listeners to message inputs to update button state
            const singleTemplate = document.getElementById('modal-single-template');
            const sampleTexts = document.querySelectorAll('.modal-sample-text');
            
            if (singleTemplate) {
                singleTemplate.oninput = () => this.updateWizardButtons();
            }
            
            sampleTexts.forEach(sample => {
                sample.oninput = () => this.updateWizardButtons();
            });
        }
    }
    
    generateCampaignSummary() {
        const summaryContainer = document.getElementById('modal-campaign-summary');
        if (!summaryContainer) return;
        
        const sourceType = document.getElementById('modal-contact-source')?.value;
        const name = document.getElementById('modal-campaign-name')?.value || 'Unnamed';
        const session = document.getElementById('modal-campaign-session')?.value || 'None';
        const delay = document.getElementById('modal-delay-seconds')?.value || '5';
        const retries = document.getElementById('modal-retry-attempts')?.value || '3';
        const maxDaily = document.getElementById('modal-max-daily')?.value || '1000';
        const mode = document.querySelector('input[name="modalMessageMode"]:checked')?.value || 'single';
        
        let messageInfo = '';
        if (mode === 'single') {
            const template = document.getElementById('modal-single-template')?.value || '';
            messageInfo = `<strong>Template:</strong><br><pre class="bg-light p-2 rounded">${template}</pre>`;
        } else {
            const samples = Array.from(document.querySelectorAll('.modal-sample-text'));
            messageInfo = `<strong>${samples.length} Message Samples</strong> (randomly selected per recipient)`;
        }
        
        // Build source info based on type
        let sourceInfo = '';
        let totalRecipients = 0;
        
        if (sourceType === 'csv') {
            const startRow = document.getElementById('modal-start-row')?.value || '1';
            const endRow = document.getElementById('modal-end-row')?.value || 'All';
            const phoneCol = document.getElementById('mapping-phone')?.value || 'Not mapped';
            const nameCol = document.getElementById('mapping-name')?.value || 'Not mapped';
            
            if (this.uploadedFileData) {
                totalRecipients = endRow === 'All' ? this.uploadedFileData.rows : Math.min(parseInt(endRow), this.uploadedFileData.rows) - parseInt(startRow) + 1;
                sourceInfo = `
                    <p><strong>Source:</strong> CSV File Upload</p>
                    <p><strong>File:</strong> ${this.uploadedFileData.filename}</p>
                    <p><strong>Row Range:</strong> ${startRow} to ${endRow}</p>
                    <p><strong>Phone Column:</strong> ${phoneCol}</p>
                    <p><strong>Name Column:</strong> ${nameCol}</p>
                `;
            }
        } else if (sourceType === 'whatsapp_groups') {
            const selectedGroups = document.querySelectorAll('.group-select-checkbox:checked');
            const deliveryMethod = document.querySelector('input[name="group-delivery-method"]:checked')?.value || 'individual_dms';
            
            sourceInfo = `
                <p><strong>Source:</strong> WhatsApp Groups</p>
                <p><strong>Selected Groups:</strong> ${selectedGroups.length}</p>
                <p><strong>Delivery Method:</strong> ${deliveryMethod === 'individual_dms' ? 'Individual DMs to members' : 'Group message'}</p>
            `;
            totalRecipients = selectedGroups.length; // Will be actual member count after processing
        } else if (sourceType === 'my_contacts') {
            const contactSelection = document.querySelector('input[name="contact-selection"]:checked')?.value || 'all';
            
            if (contactSelection === 'specific') {
                const selectedContacts = document.querySelectorAll('.contact-select-checkbox:checked');
                totalRecipients = selectedContacts.length;
                sourceInfo = `
                    <p><strong>Source:</strong> My Contacts</p>
                    <p><strong>Selection:</strong> ${selectedContacts.length} specific contacts selected</p>
                `;
            } else {
                const allCount = document.getElementById('all-contacts-count')?.textContent || '0';
                const myCount = document.getElementById('my-contacts-count')?.textContent || '0';
                totalRecipients = contactSelection === 'saved_only' ? parseInt(myCount) : parseInt(allCount);
                sourceInfo = `
                    <p><strong>Source:</strong> My Contacts</p>
                    <p><strong>Selection:</strong> ${contactSelection === 'saved_only' ? 'Only saved contacts' : 'All contacts'}</p>
                    <p><strong>Count:</strong> ${totalRecipients} contacts</p>
                `;
            }
        }
        
        const estimatedTime = (totalRecipients * parseInt(delay)) / 60; // in minutes
        
        summaryContainer.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-primary mb-3">Campaign Details</h6>
                    <p><strong>Name:</strong> ${name}</p>
                    <p><strong>Session:</strong> ${session}</p>
                    ${sourceInfo}
                    <p><strong>Total Recipients:</strong> ~${totalRecipients} messages</p>
                </div>
                <div class="col-md-6">
                    <h6 class="text-primary mb-3">Settings</h6>
                    <p><strong>Delay:</strong> ${delay} seconds between messages</p>
                    <p><strong>Retry Attempts:</strong> ${retries}</p>
                    <p><strong>Daily Limit:</strong> ${maxDaily} messages</p>
                    <p><strong>Est. Time:</strong> ~${estimatedTime.toFixed(1)} minutes</p>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-12">
                    <h6 class="text-primary mb-3">Message Configuration</h6>
                    <p><strong>Mode:</strong> ${mode === 'single' ? 'Single Template' : 'Multiple Samples'}</p>
                    ${messageInfo}
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-12">
                    <h6 class="text-primary mb-3">Exclusion Filters</h6>
                    ${this.getExclusionFiltersDisplay()}
                </div>
            </div>
        `;
    }
    
    getExclusionFiltersDisplay() {
        const excludeMyContacts = document.getElementById('modal-exclude-my-contacts')?.checked;
        const excludePrevConversations = document.getElementById('modal-exclude-previous-conversations')?.checked;
        
        const filters = [];
        if (excludeMyContacts) {
            filters.push('<li><i class="bi bi-person-x me-1"></i> Exclude contacts saved in phone</li>');
        }
        if (excludePrevConversations) {
            filters.push('<li><i class="bi bi-chat-x me-1"></i> Exclude contacts with previous conversations</li>');
        }
        
        if (filters.length === 0) {
            return '<p class="text-muted">No exclusion filters applied - messages will be sent to all contacts in the file</p>';
        }
        
        return `<ul class="mb-0">${filters.join('')}</ul>`;
    }
    
    updateWizardButtons() {
        const prevBtn = document.getElementById('modal-prev-btn');
        const nextBtn = document.getElementById('modal-next-btn');
        const saveBtn = document.getElementById('modal-save-btn');
        const launchBtn = document.getElementById('modal-launch-btn');
        
        if (!prevBtn || !nextBtn || !saveBtn || !launchBtn) return;
        
        // Show/hide back button
        prevBtn.style.display = this.currentWizardStep > 1 ? 'block' : 'none';
        
        // Update next button
        if (this.currentWizardStep < 4) {
            nextBtn.style.display = 'block';
            saveBtn.style.display = 'none';
            launchBtn.style.display = 'none';
            
            const stepNames = ['', 'Data Mapping', 'Message Config', 'Review & Launch'];
            nextBtn.innerHTML = `Next: ${stepNames[this.currentWizardStep]} <i class="bi bi-arrow-right"></i>`;
            
            // Enable/disable based on step validation
            nextBtn.disabled = !this.validateCurrentStep();
        } else {
            // Step 4: Review & Launch
            nextBtn.style.display = 'none';
            saveBtn.style.display = 'block';
            launchBtn.style.display = 'block';
            
            // Enable Launch button if all previous steps are valid
            const allStepsValid = this.validateCurrentStep();
            launchBtn.disabled = !allStepsValid;
            saveBtn.disabled = !allStepsValid;
        }
    }
    
    async handleModalFileUpload() {
        const fileInput = document.getElementById('modal-campaign-file');
        const file = fileInput.files[0];
        
        if (!file) return;
        
        const fileInfo = document.getElementById('modal-file-info');
        
        // Show file info
        fileInfo.style.display = 'block';
        fileInfo.innerHTML = `
            <div class="file-info-card">
                <div class="d-flex align-items-center">
                    <div class="file-icon">
                        <i class="bi bi-file-earmark-spreadsheet"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-bold">${file.name}</div>
                        <small class="text-muted">${(file.size / 1024 / 1024).toFixed(2)} MB • ${file.type || 'Unknown type'}</small>
                        <div class="mt-1">
                            <div class="spinner-border spinner-border-sm me-2"></div>
                            <span class="text-muted">Uploading and processing file...</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Create FormData and upload file
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            // Get dynamic URL
            const infrastructure = JSON.parse(localStorage.getItem('user_infrastructure') || '{}');
            const baseUrl = sessionStorage.getItem('API_URL') || infrastructure.apiUrl || '';
            const uploadUrl = baseUrl ? `${baseUrl}/api/files/upload` : '/api/files/upload';
            
            const response = await fetch(uploadUrl, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'File upload failed');
            }
            
            const result = await response.json();
            
            if (result.success && result.data) {
                this.uploadedFileData = {
                    valid: true,
                    file_path: result.data.file_path,
                    filename: result.data.filename,
                    rows: result.data.total_rows,
                    columns: result.data.headers.length,
                    headers: result.data.headers,
                    sample_data: result.data.sample_data,
                    suggested_mapping: result.data.suggested_mapping
                };
                
                fileInfo.innerHTML = `
                    <div class="file-info-card">
                        <div class="d-flex align-items-center">
                            <div class="file-icon">
                                <i class="bi bi-check-circle-fill text-success"></i>
                            </div>
                            <div class="flex-grow-1">
                                <div class="fw-bold">${this.uploadedFileData.filename}</div>
                                <small class="text-success">✅ ${this.uploadedFileData.rows} rows, ${this.uploadedFileData.columns} columns</small>
                                <div class="mt-1">
                                    <small class="text-muted">Headers: ${this.uploadedFileData.headers.join(', ')}</small>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                this.showToast('File uploaded and validated successfully', 'success');
                this.updateWizardButtons();
                
                // Populate column mapping in step 2
                this.populateColumnMapping();
                
                // Update row range inputs with file data
                const endRowInput = document.getElementById('modal-end-row');
                if (endRowInput) {
                    endRowInput.placeholder = `Leave empty for all rows (${this.uploadedFileData.rows} total)`;
                }
                
            } else {
                throw new Error('Invalid response from server');
            }
            
        } catch (error) {
            console.error('File upload error:', error);
            
            fileInfo.innerHTML = `
                <div class="file-info-card">
                    <div class="d-flex align-items-center">
                        <div class="file-icon">
                            <i class="bi bi-x-circle-fill text-danger"></i>
                        </div>
                        <div class="flex-grow-1">
                            <div class="fw-bold">${file.name}</div>
                            <small class="text-danger">❌ Upload failed: ${error.message}</small>
                        </div>
                    </div>
                </div>
            `;
            
            this.uploadedFileData = null;
            this.showToast('File upload failed: ' + error.message, 'error');
            this.updateWizardButtons();
        }
    }
    
    toggleModalMessageMode() {
        const mode = document.querySelector('input[name="modalMessageMode"]:checked')?.value;
        const singleSection = document.getElementById('modalSingleTemplateSection');
        const multipleSection = document.getElementById('modalMultipleSamplesSection');
        
        if (!singleSection || !multipleSection) return;
        
        if (mode === 'single') {
            singleSection.style.display = 'block';
            multipleSection.style.display = 'none';
        } else {
            singleSection.style.display = 'none';
            multipleSection.style.display = 'block';
        }
        
        // Update wizard buttons when mode changes
        this.updateWizardButtons();
    }
    
    addModalSample() {
        const container = document.getElementById('modalSamplesContainer');
        if (!container) return;
        
        const sampleCount = container.children.length + 1;
        
        const sampleDiv = document.createElement('div');
        sampleDiv.className = 'sample-input mb-2';
        sampleDiv.innerHTML = `
            <div class="input-group">
                <span class="input-group-text">Sample ${sampleCount}</span>
                <textarea class="form-control modal-sample-text" rows="2" 
                          placeholder="Enter sample message with {name} variables"></textarea>
                <button class="btn btn-outline-danger" type="button" onclick="removeModalSample(this)">
                    🗑️
                </button>
            </div>
        `;
        
        container.appendChild(sampleDiv);
        this.updateModalSampleNumbers();
        
        // Add input listener to new textarea for button state updates
        const newTextarea = sampleDiv.querySelector('.modal-sample-text');
        if (newTextarea) {
            newTextarea.oninput = () => this.updateWizardButtons();
        }
    }
    
    removeModalSample(button) {
        const container = document.getElementById('modalSamplesContainer');
        if (!container || container.children.length <= 1) return;
        
        button.closest('.sample-input').remove();
        this.updateModalSampleNumbers();
        this.updateWizardButtons(); // Update button state after removal
    }
    
    async generateSimilarTemplates() {
        const container = document.getElementById('modalSamplesContainer');
        if (!container) return;
        
        // Get the first template
        const firstTemplate = container.querySelector('.modal-sample-text');
        if (!firstTemplate || !firstTemplate.value.trim()) {
            this.showToast('Please enter at least one template first', 'warning');
            return;
        }
        
        // Show loading state
        const generateBtn = document.querySelector('[onclick="generateSimilarTemplates()"]');
        const originalHtml = generateBtn.innerHTML;
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Generating...';
        
        try {
            // Call the backend API
            const response = await this.apiCall('/api/generate-templates', {
                method: 'POST',
                body: JSON.stringify({
                    template: firstTemplate.value.trim(),
                    count: 3  // Generate 3 variations
                })
            });
            
            if (response.success && response.variations) {
                // Add the generated variations
                response.variations.forEach(variation => {
                    this.addModalSample();
                    // Get the last added textarea
                    const textareas = container.querySelectorAll('.modal-sample-text');
                    const lastTextarea = textareas[textareas.length - 1];
                    lastTextarea.value = variation;
                });
                
                this.showToast(`Generated ${response.variations.length} template variations`, 'success');
            } else {
                this.showToast('Failed to generate templates', 'error');
            }
        } catch (error) {
            console.error('Error generating templates:', error);
            this.showToast('Error generating templates: ' + error.message, 'error');
        } finally {
            // Restore button state
            if (generateBtn) {
                generateBtn.disabled = false;
                generateBtn.innerHTML = originalHtml;
            }
        }
    }
    
    updateModalSampleNumbers() {
        const container = document.getElementById('modalSamplesContainer');
        if (!container) return;
        
        Array.from(container.children).forEach((child, index) => {
            const span = child.querySelector('.input-group-text');
            if (span) span.textContent = `Sample ${index + 1}`;
            
            const button = child.querySelector('.btn-outline-danger');
            if (button) button.disabled = container.children.length === 1;
        });
    }
    
    populateDataMapping() {
        const sourceType = document.getElementById('modal-contact-source')?.value;
        
        if (sourceType === 'csv') {
            this.populateColumnMapping();
        } else if (sourceType === 'whatsapp_groups') {
            this.populateGroupDataMapping();
        } else if (sourceType === 'my_contacts') {
            this.populateContactDataMapping();
        }
    }
    
    populateGroupDataMapping() {
        const mappingContainer = document.getElementById('modal-column-mapping');
        const previewContainer = document.getElementById('modal-data-preview');
        
        if (!mappingContainer || !previewContainer) return;
        
        // Get selected groups
        const selectedGroups = Array.from(document.querySelectorAll('.group-select-checkbox:checked'));
        const deliveryMethod = document.querySelector('input[name="group-delivery-method"]:checked')?.value || 'individual_dms';
        
        mappingContainer.innerHTML = `
            <div class="alert alert-info mb-3">
                <i class="bi bi-info-circle me-2"></i>
                <strong>WhatsApp Groups Source</strong><br>
                ${selectedGroups.length} group(s) selected
            </div>
            <div class="mb-3">
                <p><strong>Delivery Method:</strong> ${deliveryMethod === 'individual_dms' ? 
                    '💬 Individual DMs to group members' : 
                    '📢 Direct message to group'}</p>
                <p><strong>Selected Groups:</strong></p>
                <ul class="list-group">
                    ${selectedGroups.map(cb => {
                        const label = cb.parentElement.querySelector('label');
                        return `<li class="list-group-item">${label ? label.textContent : cb.value}</li>`;
                    }).join('')}
                </ul>
            </div>
            <div class="alert alert-warning">
                <i class="bi bi-lightbulb me-2"></i>
                <strong>Available Variables:</strong><br>
                • <code>{name}</code> - Contact/Group name<br>
                • <code>{phone}</code> - Phone number (for individual DMs)<br>
                • <code>{group_name}</code> - Group name
            </div>
        `;
        
        previewContainer.innerHTML = `
            <h6 class="text-primary mb-3">Data Preview</h6>
            <p class="text-muted">Contact data will be extracted when the campaign starts.</p>
            ${deliveryMethod === 'individual_dms' ? 
                '<p>Group members will be extracted and messaged individually.</p>' :
                '<p>Messages will be sent directly to the selected groups.</p>'
            }
        `;
    }
    
    populateContactDataMapping() {
        const mappingContainer = document.getElementById('modal-column-mapping');
        const previewContainer = document.getElementById('modal-data-preview');
        
        if (!mappingContainer || !previewContainer) return;
        
        const contactSelection = document.querySelector('input[name="contact-selection"]:checked')?.value || 'all';
        let selectionInfo = '';
        
        if (contactSelection === 'specific') {
            const selectedContacts = document.querySelectorAll('.contact-select-checkbox:checked');
            selectionInfo = `${selectedContacts.length} specific contacts selected`;
        } else if (contactSelection === 'saved_only') {
            const myCount = document.getElementById('my-contacts-count')?.textContent || '0';
            selectionInfo = `${myCount} saved contacts`;
        } else {
            const allCount = document.getElementById('all-contacts-count')?.textContent || '0';
            selectionInfo = `All ${allCount} contacts`;
        }
        
        mappingContainer.innerHTML = `
            <div class="alert alert-info mb-3">
                <i class="bi bi-info-circle me-2"></i>
                <strong>My Contacts Source</strong><br>
                ${selectionInfo}
            </div>
            <div class="mb-3">
                <p><strong>Contact Selection:</strong> ${
                    contactSelection === 'all' ? 'All contacts' :
                    contactSelection === 'saved_only' ? 'Only saved contacts' :
                    'Specific contacts selected'
                }</p>
                ${contactSelection === 'specific' ? `
                    <details>
                        <summary>View selected contacts</summary>
                        <ul class="list-group mt-2">
                            ${Array.from(document.querySelectorAll('.contact-select-checkbox:checked')).map(cb => {
                                const label = cb.parentElement.querySelector('label');
                                return `<li class="list-group-item">${label ? label.textContent : cb.value}</li>`;
                            }).join('')}
                        </ul>
                    </details>
                ` : ''}
            </div>
            <div class="alert alert-warning">
                <i class="bi bi-lightbulb me-2"></i>
                <strong>Available Variables:</strong><br>
                • <code>{name}</code> - Contact name<br>
                • <code>{phone}</code> - Phone number<br>
                • <code>{pushname}</code> - WhatsApp push name
            </div>
        `;
        
        previewContainer.innerHTML = `
            <h6 class="text-primary mb-3">Data Preview</h6>
            <p class="text-muted">Contact data from your WhatsApp account will be used.</p>
            <p>Each contact will receive an individual message with their data.</p>
        `;
    }
    
    populateColumnMapping() {
        if (!this.uploadedFileData || !this.uploadedFileData.headers) return;
        
        const mappingContainer = document.getElementById('modal-column-mapping');
        const previewContainer = document.getElementById('modal-data-preview');
        
        if (!mappingContainer || !previewContainer) return;
        
        // Create column mapping UI
        const headers = this.uploadedFileData.headers;
        const suggestedMapping = this.uploadedFileData.suggested_mapping || {};
        
        mappingContainer.innerHTML = `
            <div class="alert alert-info mb-3">
                <i class="bi bi-info-circle me-2"></i>
                Map your CSV columns to the required fields
            </div>
            <div class="mb-3">
                <label class="form-label">Phone Number Column *</label>
                <select class="form-select" id="mapping-phone">
                    <option value="">Select column...</option>
                    ${headers.map(h => 
                        `<option value="${h}" ${suggestedMapping.phone_number === h ? 'selected' : ''}>${h}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Name Column (optional)</label>
                <select class="form-select" id="mapping-name">
                    <option value="">Select column...</option>
                    ${headers.map(h => 
                        `<option value="${h}" ${suggestedMapping.name === h ? 'selected' : ''}>${h}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Additional Columns (for template variables)</label>
                <small class="text-muted">These columns can be used as {variables} in your message template</small>
                <div class="mt-2">
                    ${headers.map(h => `
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="${h}" id="mapping-var-${h}">
                            <label class="form-check-label" for="mapping-var-${h}">
                                ${h}
                            </label>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        // Show data preview
        if (this.uploadedFileData.sample_data && this.uploadedFileData.sample_data.length > 0) {
            const sampleData = this.uploadedFileData.sample_data.slice(0, 5); // Show first 5 rows
            
            previewContainer.innerHTML = `
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
                            ${headers.map(h => `<th>${h}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${sampleData.map(row => `
                            <tr>
                                ${headers.map(h => `<td>${row[h] || ''}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <small class="text-muted">Showing first ${sampleData.length} rows of ${this.uploadedFileData.rows} total</small>
            `;
        }
    }
    
    async launchModalCampaign() {
        try {
            // Prepare campaign data
            const campaignData = this.prepareCampaignData();
            
            // Get the selected source type
            const sourceType = document.getElementById('modal-contact-source')?.value;
            
            // Prepare the source configuration based on type
            let source = {};
            
            if (sourceType === 'csv') {
                // CSV Upload source
                if (!this.uploadedFileData || !this.uploadedFileData.file_path) {
                    throw new Error('Please upload a CSV file first');
                }
                
                source = {
                    source_type: 'csv_upload',
                    file_path: this.uploadedFileData.file_path,
                    start_row: parseInt(document.getElementById('modal-start-row')?.value || 1),
                    end_row: document.getElementById('modal-end-row')?.value ? 
                             parseInt(document.getElementById('modal-end-row').value) : null
                };
                
                // Get column mapping for CSV
                const columnMapping = {
                    phone_number: document.getElementById('mapping-phone')?.value || '',
                    name: document.getElementById('mapping-name')?.value || ''
                };
                
                // Add additional mapped columns
                const varCheckboxes = document.querySelectorAll('[id^="mapping-var-"]:checked');
                varCheckboxes.forEach(cb => {
                    const colName = cb.value;
                    if (colName && !columnMapping[colName]) {
                        columnMapping[colName] = colName;
                    }
                });
                
                source.column_mapping = columnMapping;
                
            } else if (sourceType === 'whatsapp_groups') {
                // WhatsApp Groups source
                const selectedGroups = Array.from(document.querySelectorAll('.group-select-checkbox:checked'))
                    .map(cb => cb.value);
                
                console.log('Selected groups:', selectedGroups);  // Debug log
                
                if (selectedGroups.length === 0) {
                    throw new Error('Please select at least one group');
                }
                
                const deliveryMethod = document.querySelector('input[name="group-delivery-method"]:checked')?.value || 'individual_dms';
                
                source = {
                    source_type: 'whatsapp_group',
                    group_ids: selectedGroups,
                    delivery_method: deliveryMethod,
                    auto_join: document.getElementById('auto-join-groups')?.checked || false
                };
                
            } else if (sourceType === 'my_contacts') {
                // User Contacts source
                const contactSelection = document.querySelector('input[name="contact-selection"]:checked')?.value || 'all';
                
                if (contactSelection === 'specific') {
                    // Get selected contact IDs
                    const selectedContacts = Array.from(document.querySelectorAll('.contact-select-checkbox:checked'))
                        .map(cb => cb.value);
                    
                    if (selectedContacts.length === 0) {
                        throw new Error('Please select at least one contact');
                    }
                    
                    source = {
                        source_type: 'user_contacts',
                        contact_selection: selectedContacts,
                        filter_only_my_contacts: false
                    };
                } else {
                    source = {
                        source_type: 'user_contacts',
                        contact_selection: 'all',
                        filter_only_my_contacts: contactSelection === 'saved_only'
                    };
                }
                
            } else {
                throw new Error('Please select a contact source');
            }
            
            // Check if scheduling is selected
            const launchOption = document.querySelector('input[name="launchOption"]:checked')?.value;
            const isScheduled = launchOption === 'scheduled';
            
            // Prepare the request payload
            const payload = {
                name: campaignData.name,
                session_name: campaignData.session_name,
                source: source,
                message_mode: campaignData.message_mode,
                message_samples: campaignData.message_samples,
                use_csv_samples: document.getElementById('modalUseCsvSamples')?.checked || false,
                delay_seconds: campaignData.delay_seconds,
                retry_attempts: campaignData.retry_attempts,
                max_daily_messages: parseInt(document.getElementById('modal-max-daily')?.value || 1000),
                exclude_my_contacts: document.getElementById('modal-exclude-my-contacts')?.checked || false,
                exclude_previous_conversations: document.getElementById('modal-exclude-previous-conversations')?.checked || false,
                save_contact_before_message: document.getElementById('modal-save-contact-before')?.checked || false,
                remove_duplicates: true,
                // Add start/end row for non-CSV sources (will be applied to contacts and group participants)
                start_row: parseInt(document.getElementById('modal-start-row')?.value || 1),
                end_row: document.getElementById('modal-end-row')?.value ? 
                         parseInt(document.getElementById('modal-end-row').value) : null,
                // Include user_id for session name mapping
                user_id: this.getUserId()
            };
            
            // Add scheduling fields if scheduled
            if (isScheduled) {
                const scheduleDate = document.getElementById('scheduleDate')?.value;
                const scheduleTime = document.getElementById('scheduleTime')?.value;
                
                if (!scheduleDate || !scheduleTime) {
                    throw new Error('Please select both date and time for scheduling');
                }
                
                // Combine date and time as local time
                const scheduledDateTime = new Date(`${scheduleDate}T${scheduleTime}`);
                
                // Check if scheduled time is in the future
                if (scheduledDateTime <= new Date()) {
                    throw new Error('Scheduled time must be in the future');
                }
                
                // Send as ISO string (UTC) - backend will store in UTC
                payload.scheduled_start_time = scheduledDateTime.toISOString();
                payload.is_scheduled = true;
                
                // Log for debugging
                console.log('Local time selected:', scheduledDateTime.toLocaleString());
                console.log('UTC time sent:', scheduledDateTime.toISOString());
            }
            
            console.log('Campaign payload:', JSON.stringify(payload, null, 2));  // Debug log
            
            // Create campaign using the new endpoint
            // Get dynamic URL
            const infrastructure = JSON.parse(localStorage.getItem('user_infrastructure') || '{}');
            const baseUrl = sessionStorage.getItem('API_URL') || infrastructure.apiUrl || '';
            const campaignUrl = baseUrl ? `${baseUrl}/api/campaigns/create-with-source` : '/api/campaigns/create-with-source';
            
            const response = await fetch(campaignUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Campaign creation failed');
            }
            
            const result = await response.json();
            
            if (result.success && result.data) {
                // Show campaign creation success with session info
                const sessionDisplay = result.data.session_display || result.data.session_name || 'Unknown session';
                const campaignName = result.data.name || 'Campaign';
                this.showToast(`Campaign "${campaignName}" created successfully!\nSession: ${sessionDisplay}`, 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('campaignWizardModal'));
                if (modal) modal.hide();
                
                // Reset wizard
                this.resetCampaignWizard();
                
                // Refresh campaigns list
                this.loadCampaigns();
                this.loadProcessingStatus();
            } else {
                throw new Error(result.error || 'Campaign creation failed');
            }
            
        } catch (error) {
            console.error('Error launching campaign:', error);
            this.showToast('Failed to launch campaign: ' + error.message, 'error');
        }
    }
    
    prepareCampaignData() {
        const name = document.getElementById('modal-campaign-name')?.value || 'New Campaign';
        const session = document.getElementById('modal-campaign-session')?.value || 'default';
        const delay = parseInt(document.getElementById('modal-delay-seconds')?.value) || 5;
        const retries = parseInt(document.getElementById('modal-retry-attempts')?.value) || 3;
        
        const messageMode = document.querySelector('input[name="modalMessageMode"]:checked')?.value || 'single';
        
        let messageData = {};
        if (messageMode === 'single') {
            const template = document.getElementById('modal-single-template')?.value || 'Hello {name}!';
            messageData = {
                message_mode: 'single',
                message_samples: [{ text: template }]
            };
        } else {
            const samples = Array.from(document.querySelectorAll('.modal-sample-text') || []).map(textarea => ({
                text: textarea.value || 'Hello {name}!'
            }));
            messageData = {
                message_mode: 'multiple',
                message_samples: samples.length > 0 ? samples : [{ text: 'Hello {name}!' }]
            };
        }
        
        return {
            name,
            session_name: session,
            delay_seconds: delay,
            retry_attempts: retries,
            ...messageData
        };
    }
    
    saveModalCampaignDraft() {
        this.showToast('Draft save functionality coming soon!', 'info');
    }
    
    previewModalTemplate() {
        const mode = document.querySelector('input[name="modalMessageMode"]:checked')?.value;
        const previewContainer = document.getElementById('modal-template-preview');
        
        if (!previewContainer) return;
        
        let templates = [];
        
        if (mode === 'single') {
            const template = document.getElementById('modal-single-template')?.value || '';
            if (template.trim()) {
                templates.push(template);
            }
        } else {
            const samples = document.querySelectorAll('.modal-sample-text');
            samples.forEach(sample => {
                if (sample.value.trim()) {
                    templates.push(sample.value);
                }
            });
        }
        
        if (templates.length === 0) {
            this.showToast('Please enter at least one message template', 'warning');
            return;
        }
        
        // Get sample data from uploaded file or use defaults
        let sampleData = {
            name: 'John Doe',
            phone_number: '1234567890'
        };
        
        // If we have uploaded file data, use the first row as sample
        if (this.uploadedFileData && this.uploadedFileData.sample_data && this.uploadedFileData.sample_data.length > 0) {
            const firstRow = this.uploadedFileData.sample_data[0];
            const nameCol = document.getElementById('mapping-name')?.value;
            
            if (nameCol && firstRow[nameCol]) {
                sampleData.name = firstRow[nameCol];
            }
            
            // Add all mapped columns to sample data
            const varCheckboxes = document.querySelectorAll('[id^="mapping-var-"]:checked');
            varCheckboxes.forEach(cb => {
                const colName = cb.value;
                if (colName && firstRow[colName]) {
                    sampleData[colName] = firstRow[colName];
                }
            });
        }
        
        // Generate preview HTML
        let previewHtml = `
            <div class="card border-primary mt-3 shadow-lg animate__animated animate__fadeIn">
                <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-eye me-2"></i>Message Preview</span>
                    <button type="button" class="btn-close btn-close-white" onclick="document.getElementById('modal-template-preview').style.display='none'" title="Close preview (ESC)"></button>
                </div>
                <div class="card-body">
        `;
        
        templates.forEach((template, index) => {
            // Replace variables in template
            let processedMessage = template;
            Object.keys(sampleData).forEach(key => {
                const regex = new RegExp(`\\{${key}\\}`, 'gi');
                processedMessage = processedMessage.replace(regex, sampleData[key]);
            });
            
            previewHtml += `
                <div class="mb-3">
                    ${templates.length > 1 ? `<h6 class="text-muted">Sample ${index + 1}:</h6>` : ''}
                    <div class="whatsapp-message-preview p-3 rounded" style="background-color: #DCF8C6; border-left: 3px solid #25D366;">
                        <div style="white-space: pre-wrap; font-family: 'Segoe UI', sans-serif;">${processedMessage}</div>
                        <div class="text-end mt-2">
                            <small class="text-muted">
                                <i class="bi bi-check2-all text-primary"></i> ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                            </small>
                        </div>
                    </div>
                </div>
            `;
        });
        
        previewHtml += `
                    <div class="alert alert-info mt-3">
                        <i class="bi bi-info-circle me-2"></i>
                        <small><strong>Variables detected:</strong> ${Object.keys(sampleData).map(k => `{${k}}`).join(', ')}</small>
                    </div>
                </div>
            </div>
        `;
        
        previewContainer.innerHTML = previewHtml;
        previewContainer.style.display = 'block';
        
        // Scroll to preview
        previewContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        // Add ESC key handler to close preview
        const escHandler = (e) => {
            if (e.key === 'Escape' && previewContainer.style.display !== 'none') {
                previewContainer.style.display = 'none';
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }
    
    resetCampaignWizard() {
        // Reset wizard state
        this.currentWizardStep = 1;
        this.uploadedFileData = null;
        
        // Clear form fields
        document.getElementById('modal-campaign-name').value = '';
        document.getElementById('modal-campaign-session').value = '';
        document.getElementById('modal-campaign-file').value = '';
        document.getElementById('modal-file-info').style.display = 'none';
        document.getElementById('modal-single-template').value = '';
        document.getElementById('modal-start-row').value = '1';
        document.getElementById('modal-end-row').value = '';
        
        // Reset to step 1
        this.updateWizardStepIndicators();
        this.showWizardStep(1);
    }
    
    // ==================== ANALYTICS ====================
    
    async loadAnalytics() {
        try {
            // Get user-specific analytics
            if (!this.userId) {
                console.log('No user ID, skipping analytics');
                return;
            }
            
            const response = await this.apiCall(`/api/analytics/user/${this.userId}`);
            const analytics = response.data || {
                total_campaigns: 0,
                total_sent: 0,
                success_rate: 0,
                avg_delivery_time: 0,
                active_campaigns: 0,
                sample_types: 0
            };
            
            this.displayAnalytics(analytics);
        } catch (error) {
            console.error('Error loading analytics:', error);
            this.showToast('Failed to load analytics', 'error');
        }
    }
    
    displayAnalytics(analytics) {
        // Update overview stats
        const elements = {
            'analytics-total-campaigns': analytics.total_campaigns || 0,
            'analytics-total-sent': analytics.total_sent || 0,
            'analytics-success-rate': (analytics.success_rate || 0) + '%',
            'analytics-avg-time': (analytics.avg_delivery_time || 0) + 's',
            'analytics-active': analytics.active_campaigns || 0,
            'analytics-samples': analytics.sample_types || 0
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        });
        
        // Display placeholder content for other sections
        this.displayPlaceholderAnalytics();
    }
    
    displayPlaceholderAnalytics() {
        const samplePerformance = document.getElementById('sample-performance');
        if (samplePerformance) {
            samplePerformance.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="bi bi-bar-chart display-4"></i>
                    <p class="mt-2">Sample performance data will appear here</p>
                </div>
            `;
        }
        
        const timeline = document.getElementById('campaign-timeline');
        if (timeline) {
            timeline.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="bi bi-clock-history display-4"></i>
                    <p class="mt-2">Recent campaign activity will appear here</p>
                </div>
            `;
        }
        
        const analyticsTable = document.getElementById('analytics-table');
        if (analyticsTable) {
            analyticsTable.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="bi bi-table display-4"></i>
                    <p class="mt-2">Detailed campaign reports will appear here</p>
                </div>
            `;
        }
    }

    init() {
        try {
            // Initialize application
            console.log('Initializing WhatsApp Agent...');
            
            // Refresh user context - get fresh user ID from cache
            this.userId = this.getUserId();
            console.log('Current user ID:', this.userId);
            
            // If no user ID, try to get from cache one more time
            if (!this.userId) {
                const user = UserCache.getUser();
                if (user && user.id) {
                    this.userId = user.id;
                    console.log('User ID retrieved from cache:', this.userId);
                } else {
                    console.warn('No user logged in - running in guest mode');
                }
            }
            
            // Clear any stale data if user changed
            this.clearUserData();
            
            this.checkServerStatus();
            this.loadSessions();
            this.populateSessionSelects();
            
            // Set up periodic refresh
            setInterval(() => {
                this.checkServerStatus();
                if (this.sessions.length > 0) {
                    this.loadSessions();
                }
            }, 30000); // Refresh every 30 seconds
            
            console.log('Initialization complete with user:', this.userId);
        } catch (error) {
            console.error('Error during initialization:', error);
            throw error;
        }
    }
    
    clearUserData() {
        // Clear any cached data when user changes
        const currentUser = UserCache.getUser();
        const lastUserId = sessionStorage.getItem('last_user_id');
        
        if (currentUser && currentUser.id !== lastUserId) {
            console.log('User changed, clearing cached data');
            // Clear session-specific data
            this.sessions = [];
            this.currentSession = null;
            this.currentChat = null;
            
            // Store new user ID
            sessionStorage.setItem('last_user_id', currentUser.id);
            
            // Force reload all data for new user
            this.refreshAllData();
        }
    }
    
    refreshAllData() {
        // Reload all user-specific data
        console.log('Refreshing all data for new user');
        this.loadUserSubscription();
        this.loadSessions();
        this.loadCampaigns();
        this.loadAnalytics();
        this.loadWarmerSessions();
        this.loadContacts();
    }

    // ==================== SUBSCRIPTION FUNCTIONS ====================
    
    async loadUserSubscription() {
        try {
            const user = UserCache.getUser();
            if (!user) {
                console.log('No user logged in');
                // Show login prompt in dashboard
                this.showLoginPrompt();
                return;
            }
            
            console.log(`Loading subscription for ${user.username} (${user.email})`);
            
            const response = await fetch(`/api/users/subscription/${user.id}`, {
                headers: {
                    'Authorization': `Bearer ${user.token || 'test_token'}`
                }
            });
            
            if (response.ok) {
                this.userSubscription = await response.json();
                this.updateSubscriptionDisplay();
            }
        } catch (error) {
            console.error('Error loading subscription:', error);
        }
    }
    
    updateSubscriptionDisplay() {
        if (!this.userSubscription) return;
        
        const user = UserCache.getUser();
        
        // Update upgrade buttons based on current plan
        this.updateUpgradeButtons();
        
        // Apply plan-based UI restrictions
        this.applyPlanRestrictions();
        
        // Get plan limits based on plan type
        const planLimits = this.getPlanLimits(this.userSubscription.plan_type);
        
        // Update the subscription plan display
        const planElement = document.getElementById('current-plan');
        if (planElement) {
            const planName = this.userSubscription.plan_type.charAt(0).toUpperCase() + 
                            this.userSubscription.plan_type.slice(1);
            
            // Calculate actual usage - map API response fields to display values
            const messagesUsed = this.userSubscription.messages_used || 0;
            const sessionsUsed = this.userSubscription.current_sessions || 0;
            const campaignsActive = this.userSubscription.campaigns_created || 0;
            
            planElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <small class="text-muted">Current Plan:</small>
                        <h5 class="text-success mb-0">${planName}</h5>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="app.logout()" title="Logout">
                        <i class="bi bi-box-arrow-right"></i>
                    </button>
                </div>
                ${user ? `
                <div class="mb-2">
                    <small class="text-primary d-block">
                        <i class="bi bi-person-circle me-1"></i>${user.username}
                    </small>
                    <small class="text-muted d-block" style="font-size: 0.75rem;">
                        ${user.email}
                    </small>
                </div>
                ` : ''}
                <div class="mt-2">
                    <small class="text-muted d-block">
                        Messages: ${messagesUsed.toLocaleString()}/${planLimits.messages}
                    </small>
                    <small class="text-muted d-block">
                        Campaigns: ${campaignsActive}/${planLimits.campaigns}
                    </small>
                    <small class="text-muted d-block">
                        Sessions: ${sessionsUsed}/${planLimits.sessions}
                    </small>
                    ${planLimits.warmer_hours > 0 ? `
                    <small class="text-muted d-block">
                        Warmer: ${(this.userSubscription.warmer_hours_used || 0).toFixed(1)}/${planLimits.warmer_hours} hours/month
                    </small>
                    ` : ''}
                </div>
            `;
        }
    }
    
    getPlanLimits(planType) {
        const limits = {
            'free': {
                messages: '100',
                campaigns: '∞',
                sessions: '1',
                warmer_hours: 0
            },
            'starter': {
                messages: '1,000',
                campaigns: '∞',
                sessions: '1',  // Reduced from 2 to 1
                warmer_hours: 0  // No warmer - needs min 2 sessions
            },
            'hobby': {
                messages: '10,000',
                campaigns: '∞',
                sessions: '3',  // Reduced from 5 to 3
                warmer_hours: 24
            },
            'pro': {
                messages: '30,000',
                campaigns: '∞',
                sessions: '10',  // Reduced from 15 to 10
                warmer_hours: 96
            },
            'premium': {
                messages: '∞',
                campaigns: '∞',
                sessions: '30',  // Reduced from 50 to 30
                warmer_hours: 360
            },
            'admin': {
                messages: '∞',
                campaigns: '∞',
                sessions: '∞',
                warmer_hours: '∞'
            }
        };
        
        return limits[planType] || limits['free'];
    }
    
    applyPlanRestrictions() {
        if (!this.userSubscription) return;
        
        const planType = this.userSubscription.plan_type;
        const hasScheduling = ['hobby', 'pro', 'premium'].includes(planType);
        
        // Update Start All Campaigns button
        const startAllBtn = document.getElementById('startAllBtn');
        const startAllBadge = document.getElementById('startAllPlanBadge');
        if (startAllBtn) {
            if (hasScheduling) {
                startAllBtn.style.display = 'inline-block';
                startAllBtn.disabled = false;
                if (startAllBadge) {
                    startAllBadge.textContent = planType.charAt(0).toUpperCase() + planType.slice(1);
                    startAllBadge.className = 'badge bg-light text-success ms-1';
                }
            } else {
                startAllBtn.style.display = 'inline-block';
                startAllBtn.disabled = true;
                startAllBtn.title = 'Upgrade to Hobby or higher to use this feature';
                if (startAllBadge) {
                    startAllBadge.textContent = 'Hobby+';
                    startAllBadge.className = 'badge bg-secondary ms-1';
                }
            }
        }
        
        // Update Schedule All Campaigns button
        const scheduleAllBtn = document.getElementById('scheduleAllBtn');
        const scheduleAllBadge = document.getElementById('scheduleAllPlanBadge');
        if (scheduleAllBtn) {
            if (hasScheduling) {
                scheduleAllBtn.style.display = 'inline-block';
                scheduleAllBtn.disabled = false;
                if (scheduleAllBadge) {
                    scheduleAllBadge.textContent = planType.charAt(0).toUpperCase() + planType.slice(1);
                    scheduleAllBadge.className = 'badge bg-light text-info ms-1';
                }
            } else {
                scheduleAllBtn.style.display = 'none';
            }
        }
        
        // Update Schedule Campaign option in modal
        const scheduleRadio = document.getElementById('launchScheduled');
        const scheduleBadge = document.getElementById('schedulePlanBadge');
        if (scheduleRadio) {
            if (hasScheduling) {
                scheduleRadio.disabled = false;
                if (scheduleBadge) {
                    scheduleBadge.textContent = planType.charAt(0).toUpperCase() + planType.slice(1);
                    scheduleBadge.className = 'badge bg-success ms-2';
                }
            } else {
                scheduleRadio.disabled = true;
                scheduleRadio.checked = false; // Ensure it's not selected
                document.getElementById('launchNow').checked = true; // Select "Launch Now" instead
                if (scheduleBadge) {
                    scheduleBadge.textContent = 'Requires Hobby+';
                    scheduleBadge.className = 'badge bg-secondary ms-2';
                }
            }
        }
        
        // Hide/show warmer features based on plan
        const warmerSection = document.querySelector('.warmer-section');
        if (warmerSection) {
            if (planType === 'free') {
                warmerSection.style.opacity = '0.5';
                warmerSection.title = 'Upgrade to use WhatsApp Warmer';
            } else {
                warmerSection.style.opacity = '1';
                warmerSection.title = '';
            }
        }
    }
    
    showLoginPrompt() {
        const planElement = document.getElementById('current-plan');
        if (planElement) {
            planElement.innerHTML = `
                <div class="text-center">
                    <i class="bi bi-person-x-fill text-warning display-4"></i>
                    <p class="mt-2 mb-3">Not logged in</p>
                    <a href="https://auth.cuwapp.com/sign-in" class="btn btn-sm btn-primary">
                        <i class="bi bi-box-arrow-in-right me-1"></i>Sign In
                    </a>
                </div>
            `;
        }
    }
    
    updateUpgradeButtons() {
        const buttonsContainer = document.getElementById('upgrade-buttons');
        if (!buttonsContainer || !this.userSubscription) return;
        
        const currentPlan = this.userSubscription.plan_type;
        const plans = [
            { id: 'starter', name: 'Starter', price: 7, icon: 'bi-rocket', color: 'primary' },
            { id: 'hobby', name: 'Hobby', price: 20, icon: 'bi-star', color: 'success' },
            { id: 'pro', name: 'Pro', price: 45, icon: 'bi-trophy', color: 'warning' },
            { id: 'premium', name: 'Premium', price: 99, icon: 'bi-crown', color: 'danger' }
        ];
        
        const planOrder = ['free', 'starter', 'hobby', 'pro', 'premium'];
        const currentPlanIndex = planOrder.indexOf(currentPlan);
        
        let html = '';
        plans.forEach(plan => {
            const planIndex = planOrder.indexOf(plan.id);
            const isCurrentPlan = plan.id === currentPlan;
            const isDowngrade = planIndex < currentPlanIndex;
            const isMaxPlan = currentPlan === 'premium';
            
            if (isCurrentPlan) {
                html += `
                    <button class="btn btn-secondary btn-sm" disabled>
                        <i class="bi ${plan.icon} me-1"></i>${plan.name} - Current Plan
                    </button>
                `;
            } else if (isDowngrade) {
                html += `
                    <button class="btn btn-outline-secondary btn-sm" disabled title="Downgrade not available">
                        <i class="bi ${plan.icon} me-1"></i>${plan.name} - $${plan.price}/mo
                    </button>
                `;
            } else if (!isMaxPlan) {
                html += `
                    <button class="btn btn-outline-${plan.color} btn-sm" onclick="upgradePlan('${plan.id}', ${plan.price})">
                        <i class="bi ${plan.icon} me-1"></i>Upgrade to ${plan.name} - $${plan.price}/mo
                    </button>
                `;
            }
        });
        
        if (currentPlan === 'premium') {
            html = '<div class="alert alert-info mb-0"><i class="bi bi-crown me-2"></i>You are on the highest plan!</div>';
        }
        
        buttonsContainer.innerHTML = html;
    }
    
    logout() {
        if (confirm('Are you sure you want to logout?')) {
            // Redirect to Clerk logout page which will handle everything
            window.location.href = 'https://auth.cuwapp.com/logout';
        }
    }
    
    applySubscriptionLimits() {
        if (!this.userSubscription) return;
        
        // Check session limit
        const createSessionBtn = document.querySelector('button[onclick="createSession()"]');
        if (createSessionBtn && this.sessions.length >= this.userSubscription.sessions_limit) {
            createSessionBtn.disabled = true;
            createSessionBtn.innerHTML = '<i class="bi bi-lock me-2"></i>Session Limit Reached';
        }
        
        // Check campaign limit
        const createCampaignBtn = document.querySelector('button[onclick="createCampaign()"]');
        if (createCampaignBtn && this.userSubscription.campaigns_created >= this.userSubscription.campaigns_limit) {
            if (this.userSubscription.campaigns_limit !== -1) {
                createCampaignBtn.disabled = true;
                createCampaignBtn.innerHTML = '<i class="bi bi-lock me-2"></i>Campaign Limit Reached';
            }
        }
    }
    
    async checkResourceLimit(resource, quantity = 1) {
        try {
            const user = UserCache.getUser();
            if (!user) return false;
            
            const response = await fetch(`/api/users/check-limit/${user.id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${user.token || 'test_token'}`
                },
                body: JSON.stringify({ resource, quantity })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (!result.allowed) {
                    this.showToast(`${resource} limit reached. Please upgrade your plan.`, 'warning');
                }
                return result.allowed;
            }
        } catch (error) {
            console.error('Error checking resource limit:', error);
        }
        return true; // Allow by default if check fails
    }
    
    async trackUsage(resource, quantity = 1) {
        try {
            const user = UserCache.getUser();
            if (!user) return;
            
            await fetch(`/api/users/track-usage/${user.id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${user.token || 'test_token'}`
                },
                body: JSON.stringify({ resource, quantity })
            });
            
            // Reload subscription to update counters
            this.loadUserSubscription();
        } catch (error) {
            console.error('Error tracking usage:', error);
        }
    }

    // ==================== UTILITY FUNCTIONS ====================
    
    showToast(message, type = 'info') {
        const toastElement = document.getElementById('notification-toast');
        const toastBody = document.getElementById('toast-message');
        
        toastBody.textContent = message;
        toastElement.className = `toast toast-${type}`;
        
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
    }

    formatTime(timestamp) {
        return new Date(timestamp * 1000).toLocaleTimeString();
    }

    formatDate(timestamp) {
        return new Date(timestamp * 1000).toLocaleDateString();
    }

    getInitials(name) {
        return name.split(' ').map(word => word[0]).join('').toUpperCase().slice(0, 2);
    }

    formatPhoneNumber(phone) {
        return phone.replace('@c.us', '').replace('@g.us', '');
    }

    // ==================== API FUNCTIONS ====================
    
    async apiCall(endpoint, options = {}) {
        try {
            // SECURITY: Check if user is logged in for protected endpoints
            const protectedEndpoints = [
                '/api/sessions', '/api/campaigns', '/api/warmer', 
                '/api/groups', '/api/contacts', '/api/metrics', 
                '/analytics', '/api/users/subscription'
            ];
            
            const requiresAuth = protectedEndpoints.some(path => endpoint.includes(path));
            
            if (requiresAuth && !this.userId) {
                // Try to get user from cache
                const user = UserCache.getUser();
                if (user && user.id) {
                    this.userId = user.id;
                } else {
                    // Show login prompt instead of error
                    this.showToast('Please sign in to continue', 'warning');
                    // Redirect to sign in after short delay
                    setTimeout(() => {
                        window.location.href = '/?signin=true';
                    }, 1500);
                    throw new Error('Authentication required');
                }
            }
            
            // === DYNAMIC URL SUPPORT ===
            // Get user's container URLs from storage (set by API Gateway)
            let baseUrl = '';
            const infrastructure = JSON.parse(localStorage.getItem('user_infrastructure') || '{}');
            
            // Determine which service URL to use based on endpoint
            if (endpoint.includes('/api/warmer')) {
                baseUrl = sessionStorage.getItem('WARMER_URL') || infrastructure.warmerUrl || '';
            } else if (endpoint.includes('/api/campaign')) {
                baseUrl = sessionStorage.getItem('CAMPAIGN_URL') || infrastructure.campaignUrl || '';
            } else {
                baseUrl = sessionStorage.getItem('API_URL') || infrastructure.apiUrl || '';
            }
            
            // Build full URL - if we have a baseUrl, use it; otherwise use relative URL
            let url = endpoint;
            if (baseUrl) {
                // Remove leading slash from endpoint if present
                const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
                url = `${baseUrl}/${cleanEndpoint}`;
            }
            
            // OLD CODE (commented for backup):
            // let url = endpoint;
            
            // Add user_id to the URL if available and not already present
            if (this.userId && !url.includes('user_id=')) {
                const separator = url.includes('?') ? '&' : '?';
                url = `${url}${separator}user_id=${this.userId}`;
            }
            
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            const contentType = response.headers.get('content-type');
            let data = null;
            
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            }
            
            if (!response.ok) {
                // Try to get error message from response
                const errorMessage = data?.detail || data?.error || `HTTP error! status: ${response.status}`;
                throw new Error(errorMessage);
            }
            
            return data || response;
        } catch (error) {
            console.error('API Error:', error);
            this.showToast(`API Error: ${error.message}`, 'error');
            throw error;
        }
    }

    // ==================== PHASE 2: CAMPAIGN MANAGEMENT ====================
    
    async loadCampaigns() {
        try {
            const response = await this.apiCall('/api/campaigns');
            
            // Handle response format
            let campaigns = [];
            if (response.success && response.data) {
                campaigns = response.data;
            } else if (Array.isArray(response)) {
                campaigns = response;
            } else {
                console.warn('Unexpected campaigns response format:', response);
            }
            
            this.displayCampaigns(campaigns);
            
            // Update Stop All button visibility based on campaign states
            this.updateStopAllButtonVisibility(campaigns);
            
            // Load campaign stats using new metrics endpoint
            try {
                const userId = this.getUserId();
                const metricsResponse = await this.apiCall(`/api/metrics/campaigns?user_id=${userId || 'admin'}`);
                const metrics = metricsResponse.metrics || metricsResponse;
                
                // Update stats with metrics from new endpoint
                this.updateCampaignStats({
                    total_campaigns: metrics.total_campaigns_created || campaigns.length,
                    active_campaigns: metrics.total_active_campaigns || campaigns.filter(c => c.status === 'running' || c.status === 'paused').length,
                    completed_campaigns: campaigns.filter(c => c.status === 'completed').length,
                    total_messages: metrics.total_messages_sent || 0
                });
            } catch (statsError) {
                console.warn('Failed to load campaign metrics:', statsError);
                // Set default stats if failed
                this.updateCampaignStats({
                    total_campaigns: campaigns.length,
                    active_campaigns: campaigns.filter(c => c.status === 'running' || c.status === 'paused').length,
                    completed_campaigns: campaigns.filter(c => c.status === 'completed').length,
                    total_messages: 0
                });
            }
            
        } catch (error) {
            console.error('Error loading campaigns:', error);
            this.showToast('Failed to load campaigns', 'error');
            
            // Show empty state
            this.displayCampaigns([]);
        }
    }
    
    updateStopAllButtonVisibility(campaigns) {
        const stopAllBtn = document.getElementById('stopAllBtn');
        if (stopAllBtn) {
            // Check if there are any running or queued campaigns
            const hasActiveOrQueuedCampaigns = campaigns.some(c => 
                c.status === 'running' || c.status === 'queued'
            );
            
            // Only show Stop All button if there are active/queued campaigns and user has scheduling feature
            const planType = this.userSubscription?.plan_type || 'free';
            const hasScheduling = ['hobby', 'pro', 'premium'].includes(planType);
            
            if (hasActiveOrQueuedCampaigns && hasScheduling) {
                stopAllBtn.style.display = 'inline-block';
            } else {
                stopAllBtn.style.display = 'none';
            }
        }
    }
    
    displayCampaigns(campaigns) {
        const container = document.getElementById('campaigns-list');
        const emptyState = document.getElementById('campaigns-empty');
        
        if (!campaigns || campaigns.length === 0) {
            container.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }
        
        container.style.display = 'block';
        emptyState.style.display = 'none';
        
        container.innerHTML = campaigns.map(campaign => {
            // Check if campaign is scheduled
            const isScheduled = campaign.is_scheduled && campaign.scheduled_start_time;
            let scheduledInfo = '';
            
            if (isScheduled) {
                const scheduledTime = new Date(campaign.scheduled_start_time);
                const now = new Date();
                const timeDiff = scheduledTime - now;
                
                if (timeDiff > 0) {
                    // Calculate time remaining
                    const hours = Math.floor(timeDiff / (1000 * 60 * 60));
                    const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
                    
                    const utcString = scheduledTime.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
                    scheduledInfo = `
                        <div class="alert alert-info p-2 mt-2">
                            <i class="bi bi-calendar-event me-2"></i>
                            <strong>Scheduled:</strong> ${scheduledTime.toLocaleString()}
                            <br>
                            <small class="text-muted">UTC: ${utcString}</small>
                            <br>
                            <small>Starts in ${hours}h ${minutes}m</small>
                        </div>
                    `;
                }
            }
            
            // Check if campaign is queued
            const isQueued = campaign.status === 'queued';
            let queuedInfo = '';
            
            if (isQueued) {
                queuedInfo = `
                    <div class="alert alert-warning p-2 mt-2">
                        <i class="bi bi-hourglass-split me-2"></i>
                        <strong>Queued:</strong> Waiting for previous campaign to complete
                    </div>
                `;
            }
            
            return `
            <div class="campaign-card card mb-3" onclick="selectCampaign('${campaign.id}')" data-campaign-id="${campaign.id}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h6 class="card-title mb-0">
                            ${campaign.name}
                            ${isScheduled ? '<span class="badge bg-info ms-2">Scheduled</span>' : ''}
                            ${isQueued ? '<span class="badge bg-warning ms-2">Queued</span>' : ''}
                        </h6>
                        <span class="campaign-status status-${campaign.status.toLowerCase()}">${campaign.status}</span>
                    </div>
                    ${scheduledInfo}
                    ${queuedInfo}
                    <div class="row">
                        <div class="col-md-6">
                            <small class="text-muted">Session:</small>
                            <div class="fw-bold">${campaign.session_display || campaign.session_name}</div>
                            <small class="text-muted">Created:</small>
                            <div>${new Date(campaign.created_at).toLocaleDateString()}</div>
                        </div>
                        <div class="col-md-6">
                            <small class="text-muted">Progress:</small>
                            <div class="fw-bold">${campaign.processed_rows || 0}/${campaign.total_rows || 0} messages</div>
                            <div class="campaign-progress">
                                <div class="campaign-progress-bar" style="width: ${this.calculateProgress(campaign)}%"></div>
                            </div>
                        </div>
                    </div>
                    <div class="mt-2">
                        <small class="text-muted">Success Rate:</small>
                        <span class="fw-bold text-success">${this.calculateSuccessRate(campaign)}%</span>
                        <small class="text-muted ms-3">Message Mode:</small>
                        <span class="fw-bold">${campaign.message_mode === 'multiple' ? '🎲 Multiple Samples' : '📝 Single Template'}</span>
                    </div>
                </div>
            </div>
            `;
        }).join('');
    }
    
    calculateProgress(campaign) {
        if (!campaign.total_rows || campaign.total_rows === 0) return 0;
        return Math.round((campaign.processed_rows || 0) / campaign.total_rows * 100);
    }
    
    calculateSuccessRate(campaign) {
        if (!campaign.processed_rows || campaign.processed_rows === 0) return 0;
        return Math.round((campaign.success_count || 0) / campaign.processed_rows * 100);
    }
    
    updateCampaignStats(stats) {
        document.getElementById('total-campaigns').textContent = stats.total_campaigns || 0;
        document.getElementById('active-campaigns').textContent = stats.active_campaigns || 0;
        document.getElementById('completed-campaigns').textContent = stats.completed_campaigns || 0;
        document.getElementById('total-messages').textContent = stats.total_messages || stats.total_messages_sent || 0;
    }
    
    async selectCampaign(campaignId) {
        try {
            // Remove active class from all campaign cards
            document.querySelectorAll('.campaign-card').forEach(card => {
                card.classList.remove('active');
            });
            
            // Add active class to selected card
            const selectedCard = document.querySelector(`[data-campaign-id="${campaignId}"]`);
            if (selectedCard) {
                selectedCard.classList.add('active');
            }
            
            // Load campaign details
            const response = await this.apiCall(`/api/campaigns/${campaignId}`);
            // Extract campaign data from response
            const campaign = response.data || response;
            this.displayCampaignControls(campaign);
            
        } catch (error) {
            console.error('Error selecting campaign:', error);
            this.showToast('Failed to load campaign details', 'error');
        }
    }
    
    displayCampaignControls(campaign) {
        const container = document.getElementById('campaign-controls');
        
        // Check if user has scheduling permissions
        const hasScheduling = this.userSubscription && 
                             ['hobby', 'pro', 'premium'].includes(this.userSubscription.plan_type);
        
        // Check if campaign is scheduled
        const isScheduled = campaign.is_scheduled && campaign.scheduled_start_time;
        let scheduledInfo = '';
        
        if (isScheduled) {
            const scheduledTime = new Date(campaign.scheduled_start_time);
            const utcString = scheduledTime.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
            scheduledInfo = `
                <div class="alert alert-info p-2 mb-3">
                    <i class="bi bi-calendar-event me-2"></i>
                    <strong>Scheduled:</strong> ${scheduledTime.toLocaleString()}
                    <br>
                    <small class="text-muted">UTC: ${utcString}</small>
                </div>
            `;
        }
        
        container.innerHTML = `
            <div class="campaign-details">
                <h6 class="text-primary">${campaign.name}</h6>
                <div class="mb-3">
                    <small class="text-muted">Status:</small>
                    <span class="campaign-status status-${campaign.status.toLowerCase()} ms-2">${campaign.status}</span>
                </div>
                
                ${scheduledInfo}
                
                <div class="row mb-3">
                    <div class="col-6">
                        <small class="text-muted">Total Messages:</small>
                        <div class="fw-bold">${campaign.total_rows || 0}</div>
                    </div>
                    <div class="col-6">
                        <small class="text-muted">Processed:</small>
                        <div class="fw-bold">${campaign.processed_rows || 0}</div>
                    </div>
                </div>
                
                <div class="row mb-3">
                    <div class="col-6">
                        <small class="text-muted">Success:</small>
                        <div class="fw-bold text-success">${campaign.success_count || 0}</div>
                    </div>
                    <div class="col-6">
                        <small class="text-muted">Failed:</small>
                        <div class="fw-bold text-danger">${(campaign.processed_rows || 0) - (campaign.success_count || 0)}</div>
                    </div>
                </div>
                
                <div class="d-grid gap-2">
                    ${this.getCampaignActionButtons(campaign)}
                </div>
                
                <div class="mt-3">
                    <h6 class="text-secondary">Settings</h6>
                    <small class="text-muted">Delay:</small> <span class="fw-bold">${campaign.delay_seconds}s</span><br>
                    <small class="text-muted">Retries:</small> <span class="fw-bold">${campaign.retry_attempts}</span><br>
                    <small class="text-muted">Mode:</small> <span class="fw-bold">${campaign.message_mode === 'multiple' ? 'Multiple Samples' : 'Single Template'}</span>
                </div>
            </div>
        `;
    }
    
    getCampaignActionButtons(campaign) {
        const planType = this.userSubscription?.plan_type || 'free';
        const hasScheduling = ['hobby', 'pro', 'premium'].includes(planType);
        
        switch (campaign.status) {
            case 'created':
                return `
                    <button class="btn btn-success" onclick="startCampaign('${campaign.id}')">
                        <i class="bi bi-play-fill"></i> Start Campaign
                    </button>
                    ${hasScheduling && !campaign.is_scheduled ? `
                        <button class="btn btn-primary" onclick="scheduleCampaign('${campaign.id}')">
                            <i class="bi bi-clock"></i> Schedule
                        </button>
                    ` : ''}
                    <button class="btn btn-outline-danger" onclick="deleteCampaign('${campaign.id}')">
                        <i class="bi bi-trash"></i> Delete
                    </button>
                `;
            case 'scheduled':
                return `
                    <button class="btn btn-success" onclick="startCampaign('${campaign.id}')">
                        <i class="bi bi-play-fill"></i> Start Now
                    </button>
                    <button class="btn btn-warning" onclick="cancelSchedule('${campaign.id}')">
                        <i class="bi bi-calendar-x"></i> Cancel Schedule
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteCampaign('${campaign.id}')">
                        <i class="bi bi-trash"></i> Delete
                    </button>
                `;
            case 'queued':
                return `
                    <div class="alert alert-info mb-2">
                        <i class="bi bi-hourglass-split me-2"></i>Queued for execution (Position: ${campaign.queue_position || 'Pending'})
                    </div>
                    <button class="btn btn-outline-danger" onclick="stopCampaign('${campaign.id}')">
                        <i class="bi bi-x-circle"></i> Remove from Queue
                    </button>
                `;
            case 'running':
                return `
                    <button class="btn btn-warning" onclick="pauseCampaign('${campaign.id}')">
                        <i class="bi bi-pause-fill"></i> Pause Campaign
                    </button>
                    <button class="btn btn-outline-danger" onclick="stopCampaign('${campaign.id}')">
                        <i class="bi bi-stop-fill"></i> Stop Campaign
                    </button>
                `;
            case 'paused':
                return `
                    <button class="btn btn-success" onclick="resumeCampaign('${campaign.id}')">
                        <i class="bi bi-play-fill"></i> Resume Campaign
                    </button>
                    <button class="btn btn-outline-danger" onclick="stopCampaign('${campaign.id}')">
                        <i class="bi bi-stop-fill"></i> Stop Campaign
                    </button>
                `;
            case 'completed':
                return `
                    <button class="btn btn-primary" onclick="showRestartCampaignModal('${campaign.id}')">
                        <i class="bi bi-arrow-clockwise"></i> Restart Campaign
                    </button>
                    <button class="btn btn-outline-info" onclick="viewCampaignReport('${campaign.id}')">
                        <i class="bi bi-file-text"></i> View Report
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteCampaign('${campaign.id}')">
                        <i class="bi bi-trash"></i> Delete
                    </button>
                `;
            case 'failed':
            case 'cancelled':
                return `
                    <button class="btn btn-outline-info" onclick="viewCampaignReport('${campaign.id}')">
                        <i class="bi bi-file-text"></i> View Report
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteCampaign('${campaign.id}')">
                        <i class="bi bi-trash"></i> Delete
                    </button>
                `;
            default:
                return '<p class="text-muted">No actions available</p>';
        } 
    }
    
    async loadProcessingStatus() {
        try {
            // Get all campaigns to count running and queued
            const campaigns = await this.apiCall('/api/campaigns');
            const campaignList = campaigns.data || campaigns || [];
            
            // Count running and queued campaigns
            const runningCount = campaignList.filter(c => c.status === 'running').length;
            const queuedCount = campaignList.filter(c => c.status === 'queued').length;
            
            this.displayProcessingStatus(runningCount, queuedCount);
        } catch (error) {
            console.error('Error loading processing status:', error);
            // Show default empty state
            this.displayProcessingStatus(0, 0);
        }
    }
    
    displayProcessingStatus(runningCount, queuedCount) {
        const container = document.getElementById('processing-status');
        if (!container) return;
        
        const totalActive = runningCount + queuedCount;
        
        if (totalActive === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-pause-circle display-4"></i>
                    <p class="mt-2">No active campaigns</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="row text-center">
                <div class="col-6">
                    <div class="d-flex flex-column align-items-center">
                        <div class="text-success display-6 fw-bold">${runningCount}</div>
                        <small class="text-muted">Running</small>
                    </div>
                </div>
                <div class="col-6">
                    <div class="d-flex flex-column align-items-center">
                        <div class="text-info display-6 fw-bold">${queuedCount}</div>
                        <small class="text-muted">Queued</small>
                    </div>
                </div>
            </div>
            ${runningCount > 0 ? `
                <div class="mt-3 text-center">
                    <div class="spinner-border spinner-border-sm text-success" role="status">
                        <span class="visually-hidden">Processing...</span>
                    </div>
                    <small class="text-muted ms-2">Campaigns in progress</small>
                </div>
            ` : ''}
        `;
    }
    
    getStatusIconType(status) {
        switch (status) {
            case 'RUNNING': return 'success';
            case 'PAUSED': return 'warning';
            case 'FAILED': return 'danger';
            default: return 'info';
        }
    }
    
    getStatusIcon(status) {
        switch (status) {
            case 'RUNNING': return 'play-fill';
            case 'PAUSED': return 'pause-fill';
            case 'FAILED': return 'exclamation-triangle-fill';
            default: return 'info-circle-fill';
        }
    }

    // ==================== SERVER STATUS ====================
    
    async checkServerStatus() {
        try {
            const response = await this.apiCall('/api/ping');
            const statusElement = document.getElementById('server-status');
            statusElement.innerHTML = '<i class="bi bi-circle-fill me-1"></i>Connected';
            statusElement.className = 'badge bg-success me-3';
            
            // Load server info
            this.loadServerInfo();
        } catch (error) {
            const statusElement = document.getElementById('server-status');
            statusElement.innerHTML = '<i class="bi bi-circle-fill me-1"></i>Disconnected';
            statusElement.className = 'badge bg-danger me-3';
        }
    }

    async loadServerInfo() {
        try {
            const result = await this.apiCall('/api/server/info');
            if (result.success) {
                const serverInfoElement = document.getElementById('server-info');
                const { version, status } = result.data;
                
                serverInfoElement.innerHTML = `
                    <div class="mb-2">
                        <strong>Version:</strong> ${version.version || 'Unknown'}
                    </div>
                    <div class="mb-2">
                        <strong>Engine:</strong> ${version.engine || 'Unknown'}
                    </div>
                    <div>
                        <strong>Tier:</strong> 
                        <span class="badge bg-primary">${version.tier || 'Unknown'}</span>
                    </div>
                `;
            }
        } catch (error) {
            document.getElementById('server-info').innerHTML = `
                <div class="text-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Unable to load server info
                </div>
            `;
        }
    }

    // ==================== SESSION MANAGEMENT ====================
    
    async loadSessions() {
        try {
            // Include user_id in the request if available
            const url = this.userId ? `/api/sessions?user_id=${this.userId}` : '/api/sessions';
            const result = await this.apiCall(url);
            if (result.success) {
                this.sessions = result.data || [];
                this.displaySessions(result.data || []);
                this.populateSessionSelects();
            } else {
                // Handle empty sessions gracefully
                this.sessions = [];
                this.displaySessions([]);
                this.populateSessionSelects();
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
            // Don't show error for empty sessions
            if (error.message && !error.message.includes('no matches found')) {
                this.showToast('Failed to load sessions', 'error');
            }
            // Still display empty state
            this.sessions = [];
            this.displaySessions([]);
        }
    }

    displaySessions(sessions) {
        const container = document.getElementById('sessions-list');
        const emptyState = document.getElementById('sessions-empty');
        
        if (sessions.length === 0) {
            container.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        container.innerHTML = sessions.map(session => {
            const statusClass = session.status === 'WORKING' ? 'status-working' : 
                              session.status === 'STARTING' ? 'status-starting' : 
                              session.status === 'SCAN_QR_CODE' ? 'status-qr' : 'status-stopped';
            
            return `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card session-card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start mb-3">
                                <div>
                                    <h6 class="card-title mb-0">
                                        <i class="bi bi-phone me-2"></i>${session.name}
                                    </h6>
                                    ${session.me && session.me.id ? `
                                        <small class="text-muted">
                                            <i class="bi bi-telephone"></i> ${session.me.id.replace('@c.us', '')}
                                        </small>
                                    ` : ''}
                                </div>
                                <span class="session-status ${statusClass}">
                                    ${session.status}
                                </span>
                            </div>
                            
                            <div class="session-actions">
                                <div class="btn-group btn-group-sm mb-2">
                                    ${session.status === 'WORKING' ? `
                                        <button class="btn btn-outline-success btn-sm" onclick="app.stopSession('${session.name}')" title="Stop">
                                            <i class="bi bi-stop-fill"></i>
                                        </button>
                                    ` : session.status === 'STOPPED' ? `
                                        <button class="btn btn-outline-primary btn-sm" onclick="app.startSession('${session.name}')" title="Start">
                                            <i class="bi bi-play-fill"></i>
                                        </button>
                                    ` : ''}
                                    
                                    <!-- LOGOUT BUTTON - Always visible -->
                                    <button class="btn btn-outline-warning btn-sm" onclick="app.logoutSession('${session.name}')" title="Logout WhatsApp">
                                        <i class="bi bi-box-arrow-right"></i> Logout
                                    </button>
                                    
                                    <button class="btn btn-outline-danger btn-sm" onclick="app.deleteSession('${session.name}')" title="Delete">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                                
                                <!-- Login with Code button for QR state -->
                                ${session.status === 'SCAN_QR_CODE' ? `
                                    <button class="btn btn-sm btn-secondary" onclick="app.loginWithCode('${session.name}')" title="Login with Code">
                                        <i class="bi bi-123"></i> Use Code
                                    </button>
                                ` : ''}
                                
                                <!-- Screenshot button -->
                                ${session.status === 'WORKING' || session.status === 'SCAN_QR_CODE' ? `
                                    <button class="btn btn-sm btn-info" onclick="app.getScreenshot('${session.name}')" 
                                            title="${session.status === 'SCAN_QR_CODE' ? 'Capture QR Code' : 'Take Screenshot'}">
                                        <i class="bi bi-camera"></i>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    populateSessionSelects() {
        const selects = [
            'chat-session-select', 'contacts-session-select', 'groups-session-select',
            'check-session-select', 'group-session-select', 'message-session-select',
            'modal-campaign-session'  // Added for campaign creation modal
        ];
        
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                const currentValue = select.value;
                select.innerHTML = '<option value="">Select Session</option>' +
                    this.sessions
                        .filter(s => s.status === 'WORKING')
                        .map(s => `<option value="${s.name}">${s.name}</option>`)
                        .join('');
                
                // Restore previous selection if still valid
                if (currentValue && this.sessions.some(s => s.name === currentValue && s.status === 'WORKING')) {
                    select.value = currentValue;
                }
            }
        });
    }

    async createSession() {
        const sessionName = document.getElementById('session-name').value.trim();
        if (!sessionName) {
            this.showToast('Please enter a session name', 'warning');
            return;
        }

        // Check if user is logged in
        if (!this.userId) {
            const user = UserCache.getUser();
            if (!user) {
                this.showToast('Please sign in to create sessions', 'error');
                return;
            }
            this.userId = user.id;
        }

        console.log('Creating session with user ID:', this.userId);

        // First check existing session names
        try {
            const namesResponse = await this.apiCall(`/api/sessions/names?user_id=${this.userId}`);
            if (namesResponse.success && namesResponse.session_names) {
                const existingNames = namesResponse.session_names;
                if (existingNames.includes(sessionName)) {
                    // Show error with existing names
                    const namesList = existingNames.join(', ');
                    this.showToast(`Session name '${sessionName}' already exists! Your existing sessions: ${namesList}`, 'error');
                    
                    // Suggest alternative name
                    let counter = 2;
                    let suggestedName = `${sessionName}_${counter}`;
                    while (existingNames.includes(suggestedName)) {
                        counter++;
                        suggestedName = `${sessionName}_${counter}`;
                    }
                    document.getElementById('session-name').value = suggestedName;
                    this.showToast(`Try: ${suggestedName}`, 'info');
                    return;
                }
            }
        } catch (error) {
            console.warn('Could not check existing names:', error);
        }

        try {
            const result = await this.apiCall('/api/sessions', {
                method: 'POST',
                body: JSON.stringify({ name: sessionName })
            });

            if (result.success) {
                this.currentSession = sessionName;
                this.showToast('Session created successfully', 'success');
                this.showQRCode(sessionName);
                this.startStatusPolling(sessionName);
                this.loadSessions(); // Reload sessions list
            } else {
                // Parse error message for better display
                let errorMsg = result.error || 'Failed to create session';
                if (errorMsg.includes('already exists')) {
                    // Extract just the main error without SQL details
                    errorMsg = errorMsg.split('.')[0] + '.';
                }
                this.showToast(errorMsg, 'error');
            }
        } catch (error) {
            console.error('Session creation error:', error);
            // Clean up error message
            let errorMsg = error.message || 'Failed to create session';
            if (errorMsg.includes('already exists')) {
                errorMsg = errorMsg.split('.')[0] + '.';
            } else if (errorMsg.includes('UNIQUE constraint')) {
                errorMsg = `Session name '${sessionName}' already exists. Please choose a different name.`;
            }
            this.showToast(errorMsg, 'error');
        }
    }

    async showQRCode(sessionName) {
        const qrSection = document.getElementById('qr-section');
        const qrImage = document.getElementById('qr-image');
        
        qrSection.style.display = 'block';
        
        // Set QR code source with error handling - include user_id
        const userId = this.getUserId();
        const qrUrl = `/api/sessions/${sessionName}/qr?user_id=${userId}&t=${Date.now()}`;
        qrImage.src = qrUrl;
        
        // Handle image load error
        qrImage.onerror = () => {
            console.error('Failed to load QR code');
            qrImage.style.display = 'none';
            // Try to reload after a short delay
            setTimeout(() => {
                qrImage.src = `/api/sessions/${sessionName}/qr?user_id=${userId}&t=${Date.now()}`;
                qrImage.style.display = 'block';
            }, 1000);
        };
        
        // Handle successful load
        qrImage.onload = () => {
            qrImage.style.display = 'block';
        };
    }

    startStatusPolling(sessionName) {
        const loading = document.getElementById('auth-loading');
        const success = document.getElementById('auth-success');
        
        loading.style.display = 'block';
        success.style.display = 'none';
        
        this.pollingInterval = setInterval(async () => {
            try {
                const result = await this.apiCall(`/api/sessions/${sessionName}`);
                
                if (result.success && result.data.status === 'WORKING') {
                    clearInterval(this.pollingInterval);
                    loading.style.display = 'none';
                    success.style.display = 'block';
                    
                    this.showToast('Session connected successfully!', 'success');
                    this.loadSessions();
                    
                    setTimeout(() => {
                        document.getElementById('qr-section').style.display = 'none';
                        document.getElementById('session-name').value = '';
                    }, 3000);
                }
            } catch (error) {
                console.error('Status polling error:', error);
            }
        }, 2000);
    }

    async startSession(sessionName) {
        try {
            await this.apiCall(`/api/sessions/${sessionName}/start`, { method: 'POST' });
            this.showToast('Session started', 'success');
            setTimeout(() => this.loadSessions(), 1000);
        } catch (error) {
            this.showToast('Failed to start session', 'error');
        }
    }

    async stopSession(sessionName) {
        try {
            await this.apiCall(`/api/sessions/${sessionName}/stop`, { method: 'POST' });
            this.showToast('Session stopped', 'success');
            setTimeout(() => this.loadSessions(), 1000);
        } catch (error) {
            this.showToast('Failed to stop session', 'error');
        }
    }

    async restartSession(sessionName) {
        try {
            await this.apiCall(`/api/sessions/${sessionName}/restart`, { method: 'POST' });
            this.showToast('Session restarted', 'success');
            setTimeout(() => this.loadSessions(), 1000);
        } catch (error) {
            this.showToast('Failed to restart session', 'error');
        }
    }

    async deleteSession(sessionName) {
        if (!confirm(`Are you sure you want to delete session "${sessionName}"?`)) {
            return;
        }

        try {
            await this.apiCall(`/api/sessions/${sessionName}`, { method: 'DELETE' });
            this.showToast('Session deleted', 'success');
            this.loadSessions();
        } catch (error) {
            this.showToast('Failed to delete session', 'error');
        }
    }

    async logoutSession(sessionName) {
        if (!confirm(`Are you sure you want to logout from WhatsApp on "${sessionName}"? You'll need to scan QR code again.`)) {
            return;
        }

        try {
            await this.apiCall(`/api/sessions/${sessionName}/logout`, { method: 'POST' });
            this.showToast('Logged out from WhatsApp', 'success');
            setTimeout(() => this.loadSessions(), 1000);
        } catch (error) {
            this.showToast('Failed to logout', 'error');
        }
    }

    async loginWithCode(sessionName) {
        // Create modal for authentication code process
        const modalHtml = `
            <div class="modal fade" id="loginCodeModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Login with Authentication Code</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="codeStep1">
                                <p><strong>Enter Your Phone Number</strong></p>
                                <p>Enter your WhatsApp phone number to generate a pairing code.</p>
                                <div class="mb-3">
                                    <label class="form-label">Phone Number</label>
                                    <input type="tel" class="form-control" id="phoneNumberInput" 
                                           placeholder="17024215458" required>
                                    <small class="text-muted">Enter phone with country code (e.g., 1 for USA, 44 for UK)</small>
                                </div>
                                <button type="button" class="btn btn-primary w-100" onclick="app.requestAuthCode('${sessionName}')">
                                    <i class="bi bi-phone"></i> Generate Pairing Code
                                </button>
                            </div>
                            
                            <div id="codeStep2" style="display: none;">
                                <div class="alert alert-success">
                                    <h5 class="alert-heading">Pairing Code Generated!</h5>
                                    <hr>
                                    <p class="mb-2"><strong>Enter this code in WhatsApp:</strong></p>
                                    <h2 class="text-center my-3" id="pairingCodeDisplay" style="font-family: monospace; letter-spacing: 0.3em;"></h2>
                                </div>
                                <div class="mt-3">
                                    <p><strong>How to use this code:</strong></p>
                                    <ol class="small">
                                        <li>Open WhatsApp on your phone</li>
                                        <li>Go to Settings → Linked Devices</li>
                                        <li>Tap "Link a Device"</li>
                                        <li>Choose "Link with phone number instead"</li>
                                        <li>Enter the code shown above</li>
                                    </ol>
                                </div>
                                <button type="button" class="btn btn-secondary w-100 mt-3" 
                                        onclick="app.requestAuthCode('${sessionName}')">
                                    <i class="bi bi-arrow-clockwise"></i> Generate New Code
                                </button>
                            </div>
                            
                            <div id="codeLoading" style="display: none;" class="text-center py-4">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2">Processing...</p>
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

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('loginCodeModal'));
        modal.show();

        // Format input as user types
        document.getElementById('pairingCode').addEventListener('input', (e) => {
            let value = e.target.value.replace(/[^0-9]/g, '');
            if (value.length > 4) {
                value = value.slice(0, 4) + '-' + value.slice(4, 8);
            }
            e.target.value = value;
        });
    }

    async requestAuthCode(sessionName) {
        // Show loading
        document.getElementById('codeStep1').style.display = 'none';
        document.getElementById('codeLoading').style.display = 'block';

        try {
            // Get phone number from input
            const phoneInput = document.getElementById('phoneNumberInput');
            let phoneNumber = phoneInput ? phoneInput.value.trim() : '';
            
            if (!phoneNumber) {
                this.showToast('Please enter your phone number', 'warning');
                document.getElementById('codeStep1').style.display = 'block';
                document.getElementById('codeLoading').style.display = 'none';
                return;
            }
            
            // Clean phone number - remove any non-digits
            phoneNumber = phoneNumber.replace(/\D/g, '');
            
            // Validate it's a reasonable phone number (at least 10 digits)
            if (phoneNumber.length < 10) {
                this.showToast('Please enter a valid phone number with country code', 'warning');
                document.getElementById('codeStep1').style.display = 'block';
                document.getElementById('codeLoading').style.display = 'none';
                return;
            }

            // Request the pairing code through our API
            const result = await this.apiCall(`/api/sessions/${sessionName}/auth/request-code`, {
                method: 'POST',
                body: JSON.stringify({
                    phoneNumber: phoneNumber
                })
            });

            if (result && result.success && result.code) {
                // Display the pairing code
                document.getElementById('pairingCodeDisplay').textContent = result.code;
                document.getElementById('codeLoading').style.display = 'none';
                document.getElementById('codeStep2').style.display = 'block';
                this.showToast('Pairing code generated! Enter it in WhatsApp.', 'success');
                
                // Start checking session status
                this.startSessionStatusCheck(sessionName);
            } else {
                this.showToast(result.error || 'Failed to send code', 'error');
                document.getElementById('codeLoading').style.display = 'none';
                document.getElementById('codeStep1').style.display = 'block';
            }
        } catch (error) {
            console.error('Error requesting code:', error);
            this.showToast('Failed to request authentication code', 'error');
            document.getElementById('codeLoading').style.display = 'none';
            document.getElementById('codeStep1').style.display = 'block';
        }
    }

    startSessionStatusCheck(sessionName) {
        // Check session status every 3 seconds
        this.statusCheckInterval = setInterval(async () => {
            try {
                const result = await this.apiCall(`/api/sessions/${sessionName}`);
                if (result && result.data && result.data.status === 'WORKING') {
                    // Session is now connected!
                    clearInterval(this.statusCheckInterval);
                    this.showToast('WhatsApp connected successfully!', 'success');
                    
                    // Close modal
                    const modal = document.getElementById('loginCodeModal');
                    if (modal) {
                        const modalInstance = bootstrap.Modal.getInstance(modal);
                        if (modalInstance) modalInstance.hide();
                    }
                    
                    // Reload sessions
                    this.loadSessions();
                }
            } catch (error) {
                console.error('Error checking session status:', error);
            }
        }, 3000);
        
        // Stop checking after 2 minutes
        setTimeout(() => {
            if (this.statusCheckInterval) {
                clearInterval(this.statusCheckInterval);
                this.showToast('Pairing code expired. Please generate a new one.', 'warning');
            }
        }, 120000);
    }

    async getScreenshot(sessionName) {
        try {
            // Show loading toast
            this.showToast('Capturing screenshot...', 'info');
            
            // Get the screenshot
            const url = `/api/sessions/${sessionName}/screenshot` + 
                       (this.userId ? `?user_id=${this.userId}` : '');
            
            const response = await fetch(url);
            
            if (response.ok) {
                const blob = await response.blob();
                const imageUrl = URL.createObjectURL(blob);
                
                // Create and show modal with screenshot
                this.showScreenshotModal(sessionName, imageUrl);
            } else {
                this.showToast('Failed to capture screenshot', 'error');
            }
        } catch (error) {
            console.error('Screenshot error:', error);
            this.showToast('Failed to get screenshot', 'error');
        }
    }

    showScreenshotModal(sessionName, imageUrl) {
        // Create modal HTML
        const modalHtml = `
            <div class="modal fade" id="screenshotModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Screenshot - ${sessionName}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">
                            <img src="${imageUrl}" class="img-fluid" alt="WhatsApp Screenshot" 
                                 style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 8px;">
                        </div>
                        <div class="modal-footer">
                            <a href="${imageUrl}" download="whatsapp_screenshot_${sessionName}_${Date.now()}.png" 
                               class="btn btn-primary">
                                <i class="bi bi-download"></i> Download
                            </a>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
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

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('screenshotModal'));
        modal.show();

        // Clean up blob URL when modal is closed
        document.getElementById('screenshotModal').addEventListener('hidden.bs.modal', () => {
            URL.revokeObjectURL(imageUrl);
        });
    }

    // ==================== CHAT MANAGEMENT ====================
    
    async loadChats() {
        const sessionSelect = document.getElementById('chat-session-select');
        const session = sessionSelect.value;
        
        if (!session) {
            document.getElementById('chats-empty').style.display = 'block';
            document.getElementById('chats-list').innerHTML = '';
            return;
        }

        try {
            const result = await this.apiCall(`/api/chats/${session}`);
            if (result.success) {
                this.displayChats(result.data);
            }
        } catch (error) {
            this.showToast('Failed to load chats', 'error');
        }
    }

    displayChats(chats) {
        const container = document.getElementById('chats-list');
        const emptyState = document.getElementById('chats-empty');
        
        if (chats.length === 0) {
            container.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        container.innerHTML = chats.map(chat => {
            const lastMessage = chat.lastMessage || {};
            const displayName = chat.name || this.formatPhoneNumber(chat.id);
            
            return `
                <div class="list-group-item chat-item" onclick="app.selectChat('${chat.id}', '${displayName}')">
                    <div class="d-flex align-items-center">
                        <div class="chat-avatar me-3">
                            ${this.getInitials(displayName)}
                        </div>
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between align-items-start">
                                <div class="chat-name">${displayName}</div>
                                <div class="chat-time">
                                    ${lastMessage.timestamp ? this.formatTime(lastMessage.timestamp) : ''}
                                </div>
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <div class="chat-last-message">
                                    ${lastMessage.body || 'No messages'}
                                </div>
                                ${chat.unreadCount > 0 ? `
                                    <div class="unread-count">${chat.unreadCount}</div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    async selectChat(chatId, chatName) {
        this.currentChat = chatId;
        document.getElementById('chat-title').innerHTML = `
            <i class="bi bi-chat-square-dots me-2"></i>${chatName}
        `;
        
        document.getElementById('refresh-messages-btn').disabled = false;
        
        // Mark chat items as active
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
        event.target.closest('.chat-item').classList.add('active');
        
        await this.loadMessages(chatId);
    }

    async loadMessages(chatId) {
        const sessionSelect = document.getElementById('chat-session-select');
        const session = sessionSelect.value;
        
        if (!session || !chatId) return;

        try {
            const result = await this.apiCall(`/api/chats/${session}/${chatId}/messages?limit=50`);
            if (result.success) {
                this.displayMessages(result.data);
            }
        } catch (error) {
            this.showToast('Failed to load messages', 'error');
        }
    }

    displayMessages(messages) {
        const container = document.getElementById('messages-list');
        
        if (messages.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-chat-square-text display-1"></i>
                    <p class="mt-3">No messages in this chat</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="d-flex flex-column">
                ${messages.reverse().map(message => {
                    const isFromMe = message.fromMe;
                    const messageClass = isFromMe ? 'message-sent' : 'message-received';
                    
                    return `
                        <div class="message ${messageClass}">
                            ${!isFromMe ? `<div class="message-from">${this.formatPhoneNumber(message.from)}</div>` : ''}
                            <div class="message-content">${message.body || '[Media]'}</div>
                            <div class="message-time">${this.formatTime(message.timestamp)}</div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    async refreshMessages() {
        if (this.currentChat) {
            await this.loadMessages(this.currentChat);
        }
    }

    // ==================== CONTACT MANAGEMENT ====================
    
    async loadContacts() {
        const sessionSelect = document.getElementById('contacts-session-select');
        const session = sessionSelect.value;
        
        if (!session) {
            document.getElementById('contacts-empty').style.display = 'block';
            document.getElementById('contacts-list').innerHTML = '';
            return;
        }

        // Show loading modal
        const modal = new bootstrap.Modal(document.getElementById('contactsLoadingModal'));
        modal.show();
        
        // Helper functions for updating stages
        const updateStage = (stage, status) => {
            const spinner = document.getElementById(`contacts-${stage}-spinner`);
            const check = document.getElementById(`contacts-${stage}-check`);
            
            if (spinner && check) {
                if (status === 'active') {
                    spinner.classList.remove('d-none');
                    check.classList.add('d-none');
                } else if (status === 'complete') {
                    spinner.classList.add('d-none');
                    check.classList.remove('d-none');
                }
            }
        };
        
        const updateProgress = (percent, text) => {
            const progressBar = document.getElementById('contacts-progress-bar');
            const progressText = document.getElementById('contacts-progress-text');
            if (progressBar) {
                progressBar.style.width = `${percent}%`;
            }
            if (progressText) {
                progressText.textContent = text;
            }
        };

        try {
            // Stage 1: Connecting
            updateStage('connecting', 'active');
            updateProgress(20, 'Connecting to session...');
            
            // Small delay for visual feedback
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Stage 2: Fetching
            updateStage('connecting', 'complete');
            updateStage('fetching', 'active');
            updateProgress(50, 'Fetching contacts...');
            
            const result = await this.apiCall(`/api/contacts/${session}`);
            
            // Stage 3: Processing
            updateStage('fetching', 'complete');
            updateStage('processing', 'active');
            updateProgress(80, 'Processing contact data...');
            
            if (result.success) {
                // Update contact count
                const countText = document.getElementById('contacts-count-text');
                if (countText) {
                    countText.textContent = `Found ${result.data.length} contacts`;
                }
                
                // Complete
                updateStage('processing', 'complete');
                updateProgress(100, `Loaded ${result.data.length} contacts`);
                
                // Display contacts
                this.displayContacts(result.data);
                
                // Close modal after a short delay
                setTimeout(() => {
                    modal.hide();
                }, 1000);
            } else {
                throw new Error('Failed to load contacts');
            }
        } catch (error) {
            console.error('Error loading contacts:', error);
            this.showToast('Failed to load contacts', 'error');
            modal.hide();
        }
    }

    displayContacts(contacts) {
        const container = document.getElementById('contacts-list');
        const emptyState = document.getElementById('contacts-empty');
        
        if (contacts.length === 0) {
            container.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        container.innerHTML = contacts.map(contact => {
            // Use the 'number' field from WAHA which is clean (no @c.us or @lid)
            const phoneNumber = contact.number ? '+' + contact.number : '';
            
            // Display name priority: saved name > pushname > phone number
            const displayName = contact.name || contact.pushname || phoneNumber || 'Unknown';
            
            return `
                <div class="contact-card p-3 mb-2 border rounded">
                    <div class="d-flex align-items-center">
                        <div class="contact-avatar me-3">
                            ${this.getInitials(displayName)}
                        </div>
                        <div class="flex-grow-1">
                            <div class="contact-name">${displayName}</div>
                            <div class="contact-phone">${phoneNumber}</div>
                        </div>
                        <div class="dropdown">
                            <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown">
                                <i class="bi bi-three-dots-vertical"></i>
                            </button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item" href="#" onclick="app.openChat('${contact.id}', '${displayName}')">
                                    <i class="bi bi-chat me-2"></i>Open Chat
                                </a></li>
                                <li><a class="dropdown-item" href="#" onclick="app.blockContact('${contact.id}')">
                                    <i class="bi bi-slash-circle me-2"></i>Block
                                </a></li>
                            </ul>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    filterContacts() {
        const searchTerm = document.getElementById('contacts-search').value.toLowerCase();
        const contacts = document.querySelectorAll('.contact-card');
        
        contacts.forEach(contact => {
            const name = contact.querySelector('.contact-name').textContent.toLowerCase();
            const phone = contact.querySelector('.contact-phone').textContent.toLowerCase();
            
            if (name.includes(searchTerm) || phone.includes(searchTerm)) {
                contact.style.display = 'block';
            } else {
                contact.style.display = 'none';
            }
        });
    }

    async checkNumber() {
        const phone = document.getElementById('check-phone').value.trim();
        const session = document.getElementById('check-session-select').value;
        
        if (!phone || !session) {
            this.showToast('Please enter phone number and select session', 'warning');
            return;
        }

        try {
            const result = await this.apiCall(`/api/contacts/${session}/check/${phone}`);
            if (result.success) {
                const resultDiv = document.getElementById('check-result');
                const exists = result.data.numberExists;
                
                resultDiv.innerHTML = `
                    <div class="alert ${exists ? 'alert-success' : 'alert-warning'}">
                        <i class="bi bi-${exists ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
                        Number ${exists ? 'exists' : 'does not exist'} on WhatsApp
                    </div>
                `;
            }
        } catch (error) {
            this.showToast('Failed to check number', 'error');
        }
    }

    async blockContact(contactId) {
        const session = document.getElementById('contacts-session-select').value;
        
        if (!session) {
            this.showToast('Please select a session', 'warning');
            return;
        }

        try {
            await this.apiCall('/api/contacts/block', {
                method: 'POST',
                body: JSON.stringify({ contactId, session })
            });
            this.showToast('Contact blocked', 'success');
        } catch (error) {
            this.showToast('Failed to block contact', 'error');
        }
    }

    openChat(contactId, contactName) {
        // Switch to chats section and select the contact
        this.showSection('chats');
        document.getElementById('chat-session-select').value = document.getElementById('contacts-session-select').value;
        this.loadChats();
        
        setTimeout(() => {
            this.selectChat(contactId, contactName);
        }, 1000);
    }

    // ==================== GROUP MANAGEMENT ====================
    
    async loadGroups() {
        const sessionSelect = document.getElementById('groups-session-select');
        const session = sessionSelect.value;
        
        if (!session) {
            document.getElementById('groups-empty').style.display = 'block';
            document.getElementById('groups-list').innerHTML = '';
            return;
        }

        // Show loading modal
        const modal = new bootstrap.Modal(document.getElementById('groupsLoadingModal'));
        modal.show();
        
        // Helper functions for updating stages
        const updateStage = (stage, status) => {
            const spinner = document.getElementById(`groups-${stage}-spinner`);
            const check = document.getElementById(`groups-${stage}-check`);
            
            if (spinner && check) {
                if (status === 'active') {
                    spinner.classList.remove('d-none');
                    check.classList.add('d-none');
                } else if (status === 'complete') {
                    spinner.classList.add('d-none');
                    check.classList.remove('d-none');
                }
            }
        };
        
        const updateProgress = (percent, text) => {
            const progressBar = document.getElementById('groups-progress-bar');
            const progressText = document.getElementById('groups-progress-text');
            if (progressBar) {
                progressBar.style.width = `${percent}%`;
            }
            if (progressText) {
                progressText.textContent = text;
            }
        };

        try {
            // Stage 1: Connecting
            updateStage('connecting', 'active');
            updateProgress(20, 'Connecting to session...');
            
            // Small delay for visual feedback
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Stage 2: Fetching
            updateStage('connecting', 'complete');
            updateStage('fetching', 'active');
            updateProgress(50, 'Fetching groups...');
            
            // Load lightweight data first (no participants)
            const result = await this.apiCall(`/api/groups/${session}?lightweight=true`);
            
            // Stage 3: Processing
            updateStage('fetching', 'complete');
            updateStage('processing', 'active');
            updateProgress(80, 'Processing group data...');
            
            if (result.success) {
                // Store groups data for later use
                this.groupsData = result.data.map(group => ({
                    id: group.id?._serialized || group.id,
                    name: group.name || 'Unnamed Group',
                    isGroup: group.isGroup,
                    timestamp: group.timestamp,
                    participantsLoaded: false,
                    participants: null,
                    participantCount: null
                }));
                
                // Complete
                updateStage('processing', 'complete');
                updateProgress(100, `Loaded ${this.groupsData.length} groups`);
                
                // Display groups
                this.displayGroups(this.groupsData);
                
                // Close modal after a short delay
                setTimeout(() => {
                    modal.hide();
                }, 1000);
            } else {
                throw new Error('Failed to load groups');
            }
        } catch (error) {
            console.error('Error loading groups:', error);
            this.showToast('Failed to load groups', 'error');
            modal.hide();
        }
    }

    displayGroups(groups) {
        const container = document.getElementById('groups-list');
        const emptyState = document.getElementById('groups-empty');
        
        if (groups.length === 0) {
            container.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        container.innerHTML = groups.map(group => {
            // Show loading state if participants not loaded yet
            const participantCount = group.participantsLoaded 
                ? (group.participantCount || group.participants?.length || 0)
                : 'Loading...';
            
            return `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card group-card" onclick="app.loadGroupDetails('${group.id}')" style="cursor: pointer;">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-3">
                                <div class="group-avatar me-3">
                                    <i class="bi bi-people-fill"></i>
                                </div>
                                <div class="flex-grow-1">
                                    <h6 class="card-title mb-1">${group.name}</h6>
                                    <small class="text-muted" id="group-count-${group.id}">
                                        ${participantCount} ${typeof participantCount === 'number' ? 'members' : ''}
                                    </small>
                                </div>
                            </div>
                            
                            <div class="d-flex justify-content-between">
                                <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); app.openChat('${group.id}', '${group.name}')">
                                    <i class="bi bi-chat me-1"></i>Open
                                </button>
                                <div class="dropdown">
                                    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown" onclick="event.stopPropagation()">
                                        <i class="bi bi-three-dots"></i>
                                    </button>
                                    <ul class="dropdown-menu">
                                        <li><a class="dropdown-item ${!group.participantsLoaded ? 'disabled' : ''}" href="#" onclick="event.stopPropagation(); app.exportGroupParticipants('${group.id}', '${group.name}')">
                                            <i class="bi bi-download me-2"></i>Export Participants
                                        </a></li>
                                        <li><hr class="dropdown-divider"></li>
                                        <li><a class="dropdown-item" href="#" onclick="event.stopPropagation(); app.leaveGroup('${group.id}')">
                                            <i class="bi bi-box-arrow-right me-2"></i>Leave Group
                                        </a></li>
                                        <li><a class="dropdown-item text-danger" href="#" onclick="app.deleteGroup('${group.id}')">
                                            <i class="bi bi-trash me-2"></i>Delete Group
                                        </a></li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    async createGroup() {
        const name = document.getElementById('group-name').value.trim();
        const session = document.getElementById('group-session-select').value;
        const participantsText = document.getElementById('group-participants').value.trim();
        
        if (!name || !session || !participantsText) {
            this.showToast('Please fill all fields', 'warning');
            return;
        }

        const participants = participantsText.split('\n')
            .map(p => p.trim())
            .filter(p => p.length > 0);

        try {
            await this.apiCall(`/api/groups/${session}`, {
                method: 'POST',
                body: JSON.stringify({ name, participants })
            });
            
            this.showToast('Group created successfully', 'success');
            document.getElementById('group-name').value = '';
            document.getElementById('group-participants').value = '';
            this.loadGroups();
        } catch (error) {
            this.showToast('Failed to create group', 'error');
        }
    }

    async leaveGroup(groupId) {
        const session = document.getElementById('groups-session-select').value;
        
        if (!confirm('Are you sure you want to leave this group?')) {
            return;
        }

        try {
            await this.apiCall(`/api/groups/${session}/${groupId}/leave`, { method: 'POST' });
            this.showToast('Left group successfully', 'success');
            this.loadGroups();
        } catch (error) {
            this.showToast('Failed to leave group', 'error');
        }
    }

    async deleteGroup(groupId) {
        const session = document.getElementById('groups-session-select').value;
        
        if (!confirm('Are you sure you want to delete this group?')) {
            return;
        }

        try {
            await this.apiCall(`/api/groups/${session}/${groupId}`, { method: 'DELETE' });
            this.showToast('Group deleted successfully', 'success');
            this.loadGroups();
        } catch (error) {
            this.showToast('Failed to delete group', 'error');
        }
    }
    
    async loadGroupDetails(groupId) {
        const sessionSelect = document.getElementById('groups-session-select');
        const session = sessionSelect.value;
        
        if (!session) return;
        
        // Find the group in our stored data
        const groupIndex = this.groupsData?.findIndex(g => g.id === groupId);
        if (groupIndex === -1) return;
        
        const group = this.groupsData[groupIndex];
        
        // If already loaded, don't reload
        if (group.participantsLoaded) return;
        
        try {
            // Update UI to show loading
            const countElement = document.getElementById(`group-count-${groupId}`);
            if (countElement) {
                countElement.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Loading...';
            }
            
            // Fetch full group details
            const result = await this.apiCall(`/api/groups/${session}/${groupId}`);
            if (result.success && result.data) {
                // Update stored data
                group.participants = result.data.groupMetadata?.participants || [];
                group.participantCount = group.participants.length;
                group.participantsLoaded = true;
                
                // Update UI
                if (countElement) {
                    countElement.textContent = `${group.participantCount} members`;
                }
                
                // Enable export button
                const exportButton = document.querySelector(`[onclick*="exportGroupParticipants('${groupId}'"]`);
                if (exportButton) {
                    exportButton.classList.remove('disabled');
                }
            }
        } catch (error) {
            console.error('Failed to load group details:', error);
            const countElement = document.getElementById(`group-count-${groupId}`);
            if (countElement) {
                countElement.innerHTML = '<span class="text-danger">Failed to load</span>';
            }
        }
    }
    
    async exportGroupParticipants(groupId, groupName) {
        const session = document.getElementById('groups-session-select').value;
        
        if (!session) {
            this.showToast('Please select a session first', 'warning');
            return;
        }
        
        // Show loading toast
        this.showToast('Exporting participants... This may take a moment', 'info');
        
        try {
            const response = await this.apiCall(`/api/groups/${session}/${groupId}/export`);
            
            if (response.success && response.data) {
                const exportData = response.data;
                
                // Download JSON file
                if (exportData.json_url) {
                    const jsonLink = document.createElement('a');
                    jsonLink.href = `/static${exportData.json_url}`;
                    jsonLink.download = `${groupName}_participants.json`;
                    jsonLink.click();
                }
                
                // Download Excel file with a small delay
                setTimeout(() => {
                    if (exportData.excel_url) {
                        const excelLink = document.createElement('a');
                        excelLink.href = `/static${exportData.excel_url}`;
                        excelLink.download = `${groupName}_participants.xlsx`;
                        excelLink.click();
                    }
                }, 500);
                
                // Download CSV file with a small delay
                setTimeout(() => {
                    if (exportData.csv_url) {
                        const csvLink = document.createElement('a');
                        csvLink.href = `/static${exportData.csv_url}`;
                        csvLink.download = `${groupName}_participants.csv`;
                        csvLink.click();
                    }
                }, 1000);
                
                this.showToast(
                    `Successfully exported ${exportData.participant_count} participants!`, 
                    'success'
                );
            } else {
                throw new Error('Invalid export response');
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showToast('Failed to export participants: ' + error.message, 'error');
        }
    }

    async exportContacts() {
        const session = document.getElementById('contacts-session-select').value;
        
        if (!session) {
            this.showToast('Please select a session first', 'warning');
            return;
        }
        
        // Show loading toast
        this.showToast('Exporting contacts... This may take a moment', 'info');
        
        try {
            const response = await this.apiCall(`/api/contacts/${session}/export`);
            
            if (response.success && response.data) {
                const exportData = response.data;
                
                // Download JSON file
                if (exportData.json_url) {
                    const jsonLink = document.createElement('a');
                    jsonLink.href = `/static${exportData.json_url}`;
                    jsonLink.download = `contacts_${session}.json`;
                    jsonLink.click();
                }
                
                // Download Excel file with a small delay
                setTimeout(() => {
                    if (exportData.excel_url) {
                        const excelLink = document.createElement('a');
                        excelLink.href = `/static${exportData.excel_url}`;
                        excelLink.download = `contacts_${session}.xlsx`;
                        excelLink.click();
                    }
                }, 500);
                
                // Download CSV file with a small delay
                setTimeout(() => {
                    if (exportData.csv_url) {
                        const csvLink = document.createElement('a');
                        csvLink.href = `/static${exportData.csv_url}`;
                        csvLink.download = `contacts_${session}.csv`;
                        csvLink.click();
                    }
                }, 1000);
                
                this.showToast(
                    `Successfully exported ${exportData.contact_count} contacts!`, 
                    'success'
                );
            } else {
                throw new Error('Invalid export response');
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showToast('Failed to export contacts: ' + error.message, 'error');
        }
    }

    // ==================== MESSAGING ====================
    
    async sendTextMessage() {
        const session = document.getElementById('message-session-select').value;
        const chatId = document.getElementById('message-chat-id').value.trim();
        const text = document.getElementById('message-text').value.trim();
        
        if (!session || !chatId || !text) {
            this.showToast('Please fill all fields', 'warning');
            return;
        }

        try {
            const result = await this.apiCall('/api/messages/text', {
                method: 'POST',
                body: JSON.stringify({ session, chatId, text })
            });
            
            if (result.success) {
                this.showToast('Message sent successfully', 'success');
                document.getElementById('message-text').value = '';
                this.updateMessageStatus('Text message sent', 'success');
            }
        } catch (error) {
            this.showToast('Failed to send message', 'error');
            this.updateMessageStatus('Failed to send message', 'error');
        }
    }

    async sendFileMessage() {
        const session = document.getElementById('message-session-select').value;
        const chatId = document.getElementById('message-chat-id').value.trim();
        const fileInput = document.getElementById('message-file');
        const caption = document.getElementById('file-caption').value.trim();
        
        if (!session || !chatId || !fileInput.files[0]) {
            this.showToast('Please fill all fields and select a file', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('chatId', chatId);
        formData.append('session', session);
        formData.append('caption', caption);

        try {
            const result = await this.apiCall('/api/messages/file', {
                method: 'POST',
                body: formData,
                headers: {} // Remove Content-Type to let browser set it with boundary
            });
            
            if (result.success) {
                this.showToast('File sent successfully', 'success');
                fileInput.value = '';
                document.getElementById('file-caption').value = '';
                this.updateMessageStatus('File message sent', 'success');
            }
        } catch (error) {
            this.showToast('Failed to send file', 'error');
            this.updateMessageStatus('Failed to send file', 'error');
        }
    }

    async sendLocationMessage() {
        const session = document.getElementById('message-session-select').value;
        const chatId = document.getElementById('message-chat-id').value.trim();
        const latitude = parseFloat(document.getElementById('location-lat').value);
        const longitude = parseFloat(document.getElementById('location-lng').value);
        const title = document.getElementById('location-title').value.trim();
        
        if (!session || !chatId || isNaN(latitude) || isNaN(longitude)) {
            this.showToast('Please fill all required fields', 'warning');
            return;
        }

        try {
            const result = await this.apiCall('/api/messages/location', {
                method: 'POST',
                body: JSON.stringify({ session, chatId, latitude, longitude, title })
            });
            
            if (result.success) {
                this.showToast('Location sent successfully', 'success');
                document.getElementById('location-lat').value = '';
                document.getElementById('location-lng').value = '';
                document.getElementById('location-title').value = '';
                this.updateMessageStatus('Location message sent', 'success');
            }
        } catch (error) {
            this.showToast('Failed to send location', 'error');
            this.updateMessageStatus('Failed to send location', 'error');
        }
    }

    updateMessageStatus(message, type) {
        const statusElement = document.getElementById('message-status');
        const iconClass = type === 'success' ? 'bi-check-circle text-success' : 'bi-x-circle text-danger';
        
        statusElement.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi ${iconClass} me-2"></i>
                <span>${message}</span>
            </div>
            <small class="text-muted">${new Date().toLocaleTimeString()}</small>
        `;
    }

    // ==================== WHATSAPP WARMER ====================
    
    async loadWarmerSessions() {
        try {
            const response = await this.apiCall('/api/warmer/list');
            this.displayWarmerSessions(response);
        } catch (error) {
            console.error('Error loading warmer sessions:', error);
            // Show empty state
            const container = document.getElementById('warmer-sessions-list');
            if (container) {
                container.innerHTML = `
                    <div class="text-center text-muted py-5">
                        <i class="bi bi-fire display-1"></i>
                        <p class="mt-3">No warmer sessions created yet</p>
                        <button class="btn btn-danger" onclick="showCreateWarmerModal()">
                            <i class="bi bi-plus-circle me-2"></i>Create First Warmer
                        </button>
                    </div>
                `;
            }
        }
    }
    
    displayWarmerSessions(warmers) {
        const container = document.getElementById('warmer-sessions-list');
        if (!container) return;
        
        if (!warmers || warmers.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-fire display-1"></i>
                    <p class="mt-3">No warmer sessions created yet</p>
                    <button class="btn btn-danger" onclick="showCreateWarmerModal()">
                        <i class="bi bi-plus-circle me-2"></i>Create First Warmer
                    </button>
                </div>
            `;
            return;
        }
        
        container.innerHTML = warmers.map(warmer => `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card warmer-card ${warmer.is_active ? 'active' : ''}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <h6 class="card-title mb-0">
                                <i class="bi bi-fire text-danger me-2"></i>${warmer.name}
                            </h6>
                            <span class="badge bg-${warmer.is_active ? 'success' : 'secondary'}">
                                ${warmer.status}
                            </span>
                        </div>
                        
                        <div class="warmer-stats mb-3">
                            <div class="row">
                                <div class="col-6">
                                    <small class="text-muted">Sessions:</small>
                                    <div class="fw-bold">${warmer.all_sessions ? warmer.all_sessions.length : 0}</div>
                                </div>
                                <div class="col-6">
                                    <small class="text-muted">Messages:</small>
                                    <div class="fw-bold">${warmer.total_messages_sent || 0}</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="btn-group btn-group-sm w-100" role="group">
                            ${warmer.is_active ? `
                                <button class="btn btn-warning" onclick="stopWarmer(${warmer.id})" title="Stop">
                                    <i class="bi bi-pause-fill"></i>
                                </button>
                            ` : `
                                <button class="btn btn-success" onclick="startWarmer(${warmer.id})" title="Start">
                                    <i class="bi bi-play-fill"></i>
                                </button>
                            `}
                            <button class="btn btn-primary" onclick="showManageSessionsModal(${warmer.id})" title="Manage Sessions">
                                <i class="bi bi-people"></i>
                            </button>
                            <button class="btn btn-primary" onclick="showAddGroupsModal(${warmer.id})" title="Manage Groups">
                                <i class="bi bi-plus-circle"></i>
                            </button>
                            <button class="btn btn-info" onclick="viewWarmerMetrics(${warmer.id})" title="View Metrics">
                                <i class="bi bi-graph-up"></i>
                            </button>
                            ${!warmer.is_active ? `
                                <button class="btn btn-danger" onclick="deleteWarmer(${warmer.id})" title="Delete">
                                    <i class="bi bi-trash"></i>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    async showCreateWarmerModal() {
        // Load available sessions for warmer
        try {
            const result = await this.apiCall('/api/sessions');
            if (result.success) {
                const workingSessions = result.data.filter(s => s.status === 'WORKING');
                const checkboxContainer = document.getElementById('warmer-session-checkboxes');
                
                if (!checkboxContainer) return;
                
                if (workingSessions.length < 2) {
                    checkboxContainer.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            You need at least 2 working sessions to create a warmer. 
                            Currently you have ${workingSessions.length} working session(s).
                        </div>
                    `;
                    return;
                }
                
                checkboxContainer.innerHTML = workingSessions.map((session, index) => `
                    <div class="d-flex align-items-center mb-2 p-2" style="background: #f8f9fa; border-radius: 5px;">
                        <input class="form-check-input warmer-session-checkbox me-2" 
                               type="checkbox" 
                               value="${session.name}" 
                               id="warmer-session-${session.name}"
                               style="width: 20px; height: 20px; min-width: 20px; cursor: pointer; margin: 0;">
                        <label class="form-check-label mb-0" for="warmer-session-${session.name}" style="cursor: pointer; font-weight: 500; flex-grow: 1;">
                            ${session.name} ${index === 0 ? '<span class="badge bg-primary ms-2">Will be orchestrator</span>' : ''}
                        </label>
                    </div>
                `).join('');
                
                // Show modal
                const modal = new bootstrap.Modal(document.getElementById('createWarmerModal'));
                modal.show();
            }
        } catch (error) {
            this.showToast('Failed to load sessions', 'error');
        }
    }
    
    async createWarmerSession() {
        const name = document.getElementById('warmer-name').value.trim();
        const selectedSessions = Array.from(document.querySelectorAll('.warmer-session-checkbox:checked'))
            .map(cb => cb.value);
        
        if (!name) {
            this.showToast('Please enter a name for the warmer session', 'warning');
            return;
        }
        
        if (selectedSessions.length < 2) {
            this.showToast('Please select at least 2 sessions for warming', 'warning');
            return;
        }
        
        const groupDelayMin = parseInt(document.getElementById('group-delay-min').value) || 30;
        const groupDelayMax = parseInt(document.getElementById('group-delay-max').value) || 300;
        const directDelayMin = parseInt(document.getElementById('direct-delay-min').value) || 120;
        const directDelayMax = parseInt(document.getElementById('direct-delay-max').value) || 600;
        
        try {
            const warmerData = {
                name: name,
                orchestrator_session: selectedSessions[0],
                participant_sessions: selectedSessions.slice(1),
                config: {
                    group_message_delay_min: groupDelayMin,
                    group_message_delay_max: groupDelayMax,
                    direct_message_delay_min: directDelayMin,
                    direct_message_delay_max: directDelayMax
                }
            };
            
            const response = await this.apiCall('/api/warmer/create', {
                method: 'POST',
                body: JSON.stringify(warmerData)
            });
            
            if (response.success) {
                this.showToast('Warmer session created successfully!', 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('createWarmerModal'));
                if (modal) modal.hide();
                
                // Reset form
                document.getElementById('warmer-name').value = '';
                document.querySelectorAll('.warmer-session-checkbox').forEach(cb => cb.checked = false);
                
                // Reload warmer sessions
                this.loadWarmerSessions();
            } else {
                throw new Error(response.error || 'Failed to create warmer session');
            }
        } catch (error) {
            console.error('Error creating warmer:', error);
            this.showToast('Failed to create warmer session: ' + error.message, 'error');
        }
    }
    
    async startWarmer(warmerId) {
        try {
            // Show the startup modal
            this.showWarmerStartupModal();
            this.currentStartingWarmerId = warmerId;
            
            // Stage 1: Check configuration
            this.updateWarmerStage('checking', 'active');
            
            // Check group status
            const groupCheck = await this.apiCall(`/api/warmer/${warmerId}/groups/check`);
            
            this.updateWarmerStage('checking', 'complete');
            
            if (!groupCheck.has_enough_groups) {
                // Stage 2: Join groups
                this.updateWarmerStage('groups', 'active');
                document.getElementById('groups-status').textContent = `Joining ${groupCheck.groups_needed} groups...`;
                
                // Auto-join groups if we have links
                // For now, we'll need the user to provide group links
                this.hideWarmerStartupModal();
                this.showJoinGroupsModalForStart(warmerId, groupCheck);
                return;
            }
            
            // Stage 2: Groups already joined
            this.updateWarmerStage('groups', 'complete');
            document.getElementById('groups-status').textContent = `${groupCheck.common_groups_count} groups ready`;
            
            // Stage 3: Save contacts
            this.updateWarmerStage('contacts', 'active');
            
            // Stage 4: Start warmer
            setTimeout(async () => {
                this.updateWarmerStage('contacts', 'complete');
                document.getElementById('contacts-status').textContent = 'Contacts saved';
                
                this.updateWarmerStage('starting', 'active');
                
                const response = await this.apiCall(`/api/warmer/${warmerId}/start`, {
                    method: 'POST'
                });
                
                if (response.success) {
                    this.updateWarmerStage('starting', 'complete');
                    document.getElementById('starting-status').textContent = 'Warmer started!';
                    
                    setTimeout(() => {
                        this.hideWarmerStartupModal();
                        this.showToast('Warmer started successfully!', 'success');
                        this.loadWarmerSessions();
                    }, 1500);
                } else {
                    throw new Error(response.error || 'Failed to start warmer');
                }
            }, 1500);
            
        } catch (error) {
            console.error('Error starting warmer:', error);
            this.hideWarmerStartupModal();
            this.showToast('Failed to start warmer: ' + error.message, 'error');
        }
    }
    
    showWarmerStartupModal() {
        const modalElement = document.getElementById('warmerStartupModal');
        if (!modalElement) {
            console.error('Warmer startup modal not found');
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        
        // Reset all stages
        ['checking', 'groups', 'contacts', 'starting'].forEach(stage => {
            const spinner = document.getElementById(`${stage}-spinner`);
            const check = document.getElementById(`${stage}-check`);
            const pending = document.getElementById(`${stage}-pending`);
            
            if (spinner) spinner.classList.add('d-none');
            if (check) check.classList.add('d-none');
            if (pending) pending.classList.remove('d-none');
        });
    }
    
    hideWarmerStartupModal() {
        const modalEl = document.getElementById('warmerStartupModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) {
            modal.hide();
        }
    }
    
    updateWarmerStage(stage, status) {
        const spinner = document.getElementById(`${stage}-spinner`);
        const check = document.getElementById(`${stage}-check`);
        const pending = document.getElementById(`${stage}-pending`);
        
        if (!spinner || !check || !pending) {
            console.error(`Missing elements for stage: ${stage}`);
            return;
        }
        
        if (status === 'active') {
            spinner.classList.remove('d-none');
            check.classList.add('d-none');
            pending.classList.add('d-none');
        } else if (status === 'complete') {
            spinner.classList.add('d-none');
            check.classList.remove('d-none');
            pending.classList.add('d-none');
        } else {
            spinner.classList.add('d-none');
            check.classList.add('d-none');
            pending.classList.remove('d-none');
        }
    }
    
    async cancelWarmerStartup() {
        if (!confirm('Are you sure you want to cancel the warmer startup?')) {
            return;
        }
        
        try {
            if (this.currentStartingWarmerId) {
                // Try to stop the warmer if it was partially started
                await this.apiCall(`/api/warmer/${this.currentStartingWarmerId}/stop`, {
                    method: 'POST'
                });
            }
        } catch (error) {
            console.error('Error stopping warmer:', error);
        }
        
        this.hideWarmerStartupModal();
        this.showToast('Warmer startup cancelled', 'info');
        this.currentStartingWarmerId = null;
    }
    
    async continueWarmerStartup(warmerId) {
        // Called after groups are joined, continue with the startup process
        this.showWarmerStartupModal();
        
        // Groups are now joined
        this.updateWarmerStage('checking', 'complete');
        this.updateWarmerStage('groups', 'complete');
        document.getElementById('groups-status').textContent = '5 groups joined';
        
        // Stage 3: Save contacts
        this.updateWarmerStage('contacts', 'active');
        
        setTimeout(async () => {
            this.updateWarmerStage('contacts', 'complete');
            document.getElementById('contacts-status').textContent = 'Contacts saved';
            
            // Stage 4: Start warmer
            this.updateWarmerStage('starting', 'active');
            
            try {
                const response = await this.apiCall(`/api/warmer/${warmerId}/start`, {
                    method: 'POST'
                });
                
                if (response.success) {
                    this.updateWarmerStage('starting', 'complete');
                    document.getElementById('starting-status').textContent = 'Warmer started!';
                    
                    setTimeout(() => {
                        this.hideWarmerStartupModal();
                        this.showToast('Warmer started successfully!', 'success');
                        this.loadWarmerSessions();
                    }, 1500);
                } else {
                    throw new Error(response.error || 'Failed to start warmer');
                }
            } catch (error) {
                console.error('Error starting warmer:', error);
                this.hideWarmerStartupModal();
                this.showToast('Failed to start warmer: ' + error.message, 'error');
            }
        }, 1500);
    }
    
    async stopWarmer(warmerId) {
        if (!confirm('Are you sure you want to stop this warmer session?')) {
            return;
        }
        
        try {
            const response = await this.apiCall(`/api/warmer/${warmerId}/stop`, {
                method: 'POST'
            });
            
            if (response.success) {
                this.showToast(response.message || 'Warmer stopped successfully', 'success');
                this.loadWarmerSessions();
            } else {
                throw new Error(response.error || 'Failed to stop warmer');
            }
        } catch (error) {
            console.error('Error stopping warmer:', error);
            this.showToast('Failed to stop warmer: ' + error.message, 'error');
        }
    }
    
    async deleteWarmer(warmerId) {
        if (!confirm('Are you sure you want to delete this warmer session? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await this.apiCall(`/api/warmer/${warmerId}`, {
                method: 'DELETE'
            });
            
            if (response.success) {
                this.showToast('Warmer session deleted successfully', 'success');
                this.loadWarmerSessions();
            } else {
                throw new Error(response.error || 'Failed to delete warmer');
            }
        } catch (error) {
            console.error('Error deleting warmer:', error);
            this.showToast('Failed to delete warmer: ' + error.message, 'error');
        }
    }
    
    async viewWarmerMetrics(warmerId) {
        try {
            const response = await this.apiCall(`/api/warmer/${warmerId}/metrics`);
            
            // Update metrics display
            const metricsContainer = document.getElementById('warmer-metrics');
            if (metricsContainer && response) {
                metricsContainer.innerHTML = `
                    <h5 class="mb-3">${response.name} - Metrics</h5>
                    <div class="row">
                        <div class="col-md-4">
                            <div class="metric-card">
                                <div class="metric-value">${response.statistics.total_messages}</div>
                                <div class="metric-label">Total Messages</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="metric-card">
                                <div class="metric-value">${response.statistics.active_groups}</div>
                                <div class="metric-label">Active Groups</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="metric-card">
                                <div class="metric-value">${response.statistics.message_rate_per_minute}</div>
                                <div class="metric-label">Messages/Min</div>
                            </div>
                        </div>
                    </div>
                    <div class="row mt-3">
                        <div class="col-md-6">
                            <small class="text-muted">Group Messages:</small> ${response.statistics.group_messages}<br>
                            <small class="text-muted">Direct Messages:</small> ${response.statistics.direct_messages}
                        </div>
                        <div class="col-md-6">
                            <small class="text-muted">Duration:</small> ${response.statistics.duration_minutes} minutes<br>
                            <small class="text-muted">Groups Created:</small> ${response.statistics.groups_created}
                        </div>
                    </div>
                `;
            }
            
            // Update recent conversations
            const conversationsContainer = document.getElementById('warmer-conversations');
            if (conversationsContainer && response.recent_conversations) {
                conversationsContainer.innerHTML = response.recent_conversations.map(conv => `
                    <div class="conversation-item">
                        <div class="d-flex justify-content-between">
                            <strong>${conv.sender}</strong>
                            <span class="badge bg-${conv.type === 'group' ? 'primary' : 'info'}">${conv.type}</span>
                        </div>
                        <div class="text-muted">${conv.message}</div>
                        <small class="text-muted">${new Date(conv.sent_at).toLocaleTimeString()}</small>
                    </div>
                `).join('');
            }
            
        } catch (error) {
            console.error('Error loading warmer metrics:', error);
            this.showToast('Failed to load warmer metrics', 'error');
        }
    }
    
    async showManageSessionsModal(warmerId) {
        // Show modal for managing warmer sessions
        try {
            // Store warmer ID for later use
            this.currentWarmerId = warmerId;
            
            // Get warmer details
            const warmerResponse = await this.apiCall(`/api/warmer/${warmerId}`);
            const warmer = warmerResponse.data;
            
            // Get all available sessions
            const sessionsResponse = await this.apiCall('/api/sessions');
            const allSessions = sessionsResponse.data || [];
            
            // Display warmer info
            const infoDiv = document.getElementById('warmer-sessions-info');
            infoDiv.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <h6>${warmer.name}</h6>
                        <p class="mb-1"><strong>Orchestrator:</strong> ${warmer.orchestrator_session}</p>
                        <p class="mb-0"><strong>Total Sessions:</strong> ${warmer.participant_sessions.length + 1}</p>
                    </div>
                </div>
            `;
            
            // Display current sessions
            const currentSessionsList = document.getElementById('current-sessions-list');
            currentSessionsList.innerHTML = `
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${warmer.orchestrator_session}</strong>
                            <span class="badge bg-primary ms-2">Orchestrator</span>
                        </div>
                    </div>
                </div>
                ${warmer.participant_sessions.map(session => `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${session}</strong>
                                <span class="badge bg-secondary ms-2">Participant</span>
                            </div>
                            <button class="btn btn-sm btn-danger" onclick="removeSessionFromWarmer('${warmerId}', '${session}')">
                                <i class="bi bi-x"></i> Remove
                            </button>
                        </div>
                    </div>
                `).join('')}
            `;
            
            // Display available sessions (exclude current warmer sessions)
            const currentSessionNames = [warmer.orchestrator_session, ...warmer.participant_sessions];
            const availableSessions = allSessions.filter(s => !currentSessionNames.includes(s.name));
            
            const availableSessionsList = document.getElementById('available-sessions-list');
            if (availableSessions.length > 0) {
                availableSessionsList.innerHTML = availableSessions.map(session => `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${session.name}</strong>
                                <small class="text-muted d-block">${session.status || 'Unknown'}</small>
                            </div>
                            <button class="btn btn-sm btn-success" onclick="addSessionToWarmer('${warmerId}', '${session.name}')">
                                <i class="bi bi-plus"></i> Add
                            </button>
                        </div>
                    </div>
                `).join('');
            } else {
                availableSessionsList.innerHTML = '<p class="text-muted">No available sessions to add</p>';
            }
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('manageSessionsModal'));
            modal.show();
            
        } catch (error) {
            console.error('Error loading sessions:', error);
            this.showToast('Failed to load sessions', 'error');
        }
    }
    
    async addSessionToWarmer(warmerId, sessionName) {
        const progressDiv = document.getElementById('manage-sessions-progress');
        const statusText = document.getElementById('manage-sessions-status');
        
        progressDiv.style.display = 'block';
        statusText.textContent = `Adding ${sessionName}...`;
        
        try {
            const response = await this.apiCall(`/api/warmer/${warmerId}/sessions/add`, {
                method: 'POST',
                body: JSON.stringify({ session_name: sessionName })
            });
            
            if (response && response.success) {
                this.showToast(`Successfully added ${sessionName} to warmer`, 'success');
                // Refresh the modal
                this.showManageSessionsModal(warmerId);
            } else {
                throw new Error(response?.error || 'Failed to add session');
            }
        } catch (error) {
            console.error('Error adding session:', error);
            this.showToast('Failed to add session: ' + error.message, 'error');
        } finally {
            progressDiv.style.display = 'none';
        }
    }
    
    async removeSessionFromWarmer(warmerId, sessionName) {
        if (!confirm(`Are you sure you want to remove ${sessionName} from this warmer?`)) {
            return;
        }
        
        const progressDiv = document.getElementById('manage-sessions-progress');
        const statusText = document.getElementById('manage-sessions-status');
        
        progressDiv.style.display = 'block';
        statusText.textContent = `Removing ${sessionName}...`;
        
        try {
            const response = await this.apiCall(`/api/warmer/${warmerId}/sessions/remove`, {
                method: 'POST',
                body: JSON.stringify({ session_name: sessionName })
            });
            
            if (response && response.success) {
                this.showToast(`Successfully removed ${sessionName} from warmer`, 'success');
                // Refresh the modal
                this.showManageSessionsModal(warmerId);
            } else {
                throw new Error(response?.error || 'Failed to remove session');
            }
        } catch (error) {
            console.error('Error removing session:', error);
            this.showToast('Failed to remove session: ' + error.message, 'error');
        } finally {
            progressDiv.style.display = 'none';
        }
    }
    
    async showAddGroupsModal(warmerId) {
        // Show modal for manually adding groups to warmer
        try {
            // Get current groups for this warmer
            const response = await this.apiCall(`/api/warmer/${warmerId}/groups`);
            const currentGroups = response?.groups || [];
            
            // Store warmer ID
            document.getElementById('add-groups-warmer-id').value = warmerId;
            
            // Show current groups
            const groupsList = document.getElementById('current-groups-list');
            if (currentGroups.length > 0) {
                groupsList.innerHTML = `
                    <h6>Current Groups (${currentGroups.length}):</h6>
                    <div class="list-group mb-3">
                        ${currentGroups.map(group => `
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>${group.group_name || 'Unknown Group'}</strong>
                                    <small class="text-muted d-block">${group.group_id}</small>
                                </div>
                                <button class="btn btn-sm btn-danger" onclick="removeGroupFromWarmer('${warmerId}', '${group.id}')">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        `).join('')}
                    </div>
                `;
            } else {
                groupsList.innerHTML = '<p class="text-muted">No groups added yet</p>';
            }
            
            // Clear textarea
            document.getElementById('add-groups-links').value = '';
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('addGroupsModal'));
            modal.show();
            
        } catch (error) {
            console.error('Error loading groups:', error);
            this.showToast('Failed to load groups', 'error');
        }
    }
    
    async addGroupsToWarmer() {
        const warmerId = document.getElementById('add-groups-warmer-id').value;
        const linksText = document.getElementById('add-groups-links').value.trim();
        
        if (!linksText) {
            this.showToast('Please enter at least one group link', 'warning');
            return;
        }
        
        const links = linksText.split('\n').map(link => link.trim()).filter(link => link);
        
        if (links.length === 0) {
            this.showToast('Please enter valid group links', 'warning');
            return;
        }
        
        const progressDiv = document.getElementById('add-groups-progress');
        const statusText = document.getElementById('add-groups-status');
        const addBtn = document.getElementById('add-groups-btn');
        
        progressDiv.style.display = 'block';
        addBtn.disabled = true;
        
        try {
            // Add groups to warmer
            const response = await this.apiCall(`/api/warmer/${warmerId}/groups/add`, {
                method: 'POST',
                body: JSON.stringify({ group_links: links })
            });
            
            if (response && response.success) {
                const addedCount = response.added_count || 0;
                this.showToast(`Successfully added ${addedCount} groups`, 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('addGroupsModal'));
                if (modal) {
                    modal.hide();
                }
                
                // Reload warmer data
                this.loadWarmers();
            } else {
                const errorMsg = response?.error || response?.message || 'Failed to add groups';
                throw new Error(errorMsg);
            }
            
        } catch (error) {
            console.error('Error adding groups:', error);
            this.showToast('Failed to add groups: ' + error.message, 'error');
        } finally {
            progressDiv.style.display = 'none';
            addBtn.disabled = false;
        }
    }
    
    async removeGroupFromWarmer(warmerId, groupId) {
        if (!confirm('Are you sure you want to remove this group from the warmer?')) {
            return;
        }
        
        try {
            const response = await this.apiCall(`/api/warmer/${warmerId}/groups/${groupId}`, {
                method: 'DELETE'
            });
            
            if (response.success) {
                this.showToast('Group removed successfully', 'success');
                // Refresh the modal
                this.showAddGroupsModal(warmerId);
            } else {
                throw new Error(response.error || 'Failed to remove group');
            }
        } catch (error) {
            console.error('Error removing group:', error);
            this.showToast('Failed to remove group', 'error');
        }
    }
    
    showJoinGroupsModal(warmerId) {
        // This is for manual join groups button - always shows 5 inputs
        this.apiCall(`/api/warmer/${warmerId}/groups/check`).then(groupCheck => {
            this.showJoinGroupsModalWithCount(warmerId, 5, groupCheck);
        });
    }
    
    showJoinGroupsModalForStart(warmerId, groupCheck) {
        // This is called from start warmer - shows only needed inputs
        const groupsNeeded = groupCheck.groups_needed;
        this.showJoinGroupsModalWithCount(warmerId, groupsNeeded, groupCheck, true);
    }
    
    showJoinGroupsModalWithCount(warmerId, inputCount, groupCheck, isForStart = false) {
        // Store the warmer ID and count
        document.getElementById('join-groups-warmer-id').value = warmerId;
        document.getElementById('join-groups-needed').value = inputCount;
        
        // Update the info message
        const messageElement = document.getElementById('join-groups-message');
        if (isForStart) {
            messageElement.innerHTML = `
                <strong>Groups needed to start warmer:</strong><br>
                Currently ${groupCheck.common_groups_count} common groups found. 
                Need ${groupCheck.groups_needed} more groups to reach the minimum of 5.
            `;
        } else {
            messageElement.innerHTML = `
                <strong>Join Groups:</strong><br>
                Currently ${groupCheck.common_groups_count} common groups found. 
                You can add up to ${inputCount} more groups.
            `;
        }
        
        // Generate dynamic inputs
        const container = document.getElementById('group-links-container');
        container.innerHTML = '';
        
        for (let i = 1; i <= inputCount; i++) {
            const inputDiv = document.createElement('div');
            inputDiv.className = 'mb-3';
            inputDiv.innerHTML = `
                <label class="form-label">Group Invite Link ${i}</label>
                <input type="url" class="form-control group-link-input" 
                       placeholder="https://chat.whatsapp.com/..." required>
            `;
            container.appendChild(inputDiv);
        }
        
        // Update button text
        const joinBtn = document.getElementById('join-groups-btn');
        if (isForStart) {
            joinBtn.innerHTML = '<i class="bi bi-play-fill me-2"></i>Join Groups & Start Warmer';
            joinBtn.setAttribute('data-start-after', 'true');
        } else {
            joinBtn.innerHTML = '<i class="bi bi-link-45deg me-2"></i>Join Groups';
            joinBtn.setAttribute('data-start-after', 'false');
        }
        
        // Reset progress
        document.getElementById('join-groups-progress').style.display = 'none';
        document.querySelector('#join-groups-progress .progress-bar').style.width = '0%';
        joinBtn.disabled = false;
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('joinGroupsModal'));
        modal.show();
    }
    
    async joinGroupsForWarmer() {
        const warmerId = document.getElementById('join-groups-warmer-id').value;
        const linkInputs = document.querySelectorAll('.group-link-input');
        const inviteLinks = [];
        const shouldStartAfter = document.getElementById('join-groups-btn').getAttribute('data-start-after') === 'true';
        
        // Validate and collect links
        for (let input of linkInputs) {
            const link = input.value.trim();
            if (!link) {
                this.showToast(`Please provide all ${linkInputs.length} group invite links`, 'warning');
                return;
            }
            if (!link.startsWith('https://chat.whatsapp.com/')) {
                this.showToast('All links must be valid WhatsApp group invite links', 'warning');
                return;
            }
            inviteLinks.push(link);
        }
        
        // Disable button and show progress
        document.getElementById('join-groups-btn').disabled = true;
        document.getElementById('join-groups-progress').style.display = 'block';
        document.getElementById('join-groups-status').textContent = 'Joining groups...';
        
        try {
            const response = await this.apiCall(`/api/warmer/${warmerId}/join-groups`, {
                method: 'POST',
                body: JSON.stringify({ invite_links: inviteLinks })
            });
            
            if (response.success) {
                // Update progress to 50%
                document.querySelector('#join-groups-progress .progress-bar').style.width = '50%';
                document.getElementById('join-groups-status').textContent = 'Successfully joined groups!';
                
                if (shouldStartAfter) {
                    // Close the join groups modal
                    bootstrap.Modal.getInstance(document.getElementById('joinGroupsModal')).hide();
                    
                    // Continue with the warmer startup process
                    this.continueWarmerStartup(warmerId);
                    return;
                } else {
                    // Just joined groups
                    document.querySelector('#join-groups-progress .progress-bar').style.width = '100%';
                    this.showToast(response.message || 'Groups joined successfully!', 'success');
                }
                
                // Close modal after delay
                setTimeout(() => {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('joinGroupsModal'));
                    if (modal) modal.hide();
                    
                    // Reload warmer sessions
                    this.loadWarmerSessions();
                }, 2000);
            } else {
                throw new Error(response.error || 'Failed to join groups');
            }
        } catch (error) {
            console.error('Error joining groups:', error);
            this.showToast('Failed: ' + error.message, 'error');
            
            // Re-enable button
            document.getElementById('join-groups-btn').disabled = false;
            document.getElementById('join-groups-progress').style.display = 'none';
        }
    }

    // ==================== NAVIGATION ====================
    
    showSection(sectionName) {
        // Hide all sections
        const sections = ['sessions', 'chats', 'contacts', 'groups', 'campaigns', 'analytics', 'warmer'];
        sections.forEach(section => {
            const sectionElement = document.getElementById(`${section}-section`);
            if (sectionElement) {
                sectionElement.style.display = 'none';
            }
        });
        
        // Show selected section
        const targetSection = document.getElementById(`${sectionName}-section`);
        if (targetSection) {
            targetSection.style.display = 'block';
        }
        
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Add active class to clicked link
        if (event && event.target) {
            event.target.classList.add('active');
        }
        
        // Load section data
        switch (sectionName) {
            case 'chats':
                this.loadChats();
                break;
            case 'contacts':
                this.loadContacts();
                break;
            case 'groups':
                this.loadGroups();
                break;
            case 'campaigns':
                this.loadCampaigns();
                this.loadProcessingStatus();
                break;
            case 'analytics':
                this.loadAnalytics();
                break;
            case 'warmer':
                this.loadWarmerSessions();
                break;
        }
    }

    // ==================== SOURCE SELECTION FUNCTIONS ====================
    
    async toggleSourceOptions() {
        const sourceSelect = document.getElementById('modal-contact-source');
        const csvSection = document.getElementById('csv-source-section');
        const groupSection = document.getElementById('group-source-section');
        const contactSection = document.getElementById('contact-source-section');
        
        if (!sourceSelect) return;
        
        // Hide all sections first
        if (csvSection) csvSection.style.display = 'none';
        if (groupSection) groupSection.style.display = 'none';
        if (contactSection) contactSection.style.display = 'none';
        
        // Show the selected section
        switch(sourceSelect.value) {
            case 'csv':
                if (csvSection) csvSection.style.display = 'block';
                break;
            case 'whatsapp_groups':
                if (groupSection) groupSection.style.display = 'block';
                await this.loadSourceGroups();
                break;
            case 'my_contacts':
                if (contactSection) contactSection.style.display = 'block';
                break;
        }
        
        // Update button state whenever source changes
        this.updateWizardButtons();
    }
    
    async loadSourceOptions() {
        const sessionSelect = document.getElementById('modal-campaign-session');
        if (!sessionSelect || !sessionSelect.value) return;
        
        const sessionName = sessionSelect.value;
        
        // Load both groups and contacts when session changes
        await this.loadSourceGroups(sessionName);
        await this.loadSourceContacts(sessionName);
    }
    
    async loadSourceGroups(sessionName = null) {
        const sessionSelect = document.getElementById('modal-campaign-session');
        const groupsContainer = document.getElementById('group-selection-list');
        
        if (!groupsContainer) return;
        
        const session = sessionName || sessionSelect?.value;
        if (!session) {
            groupsContainer.innerHTML = '<p class="text-muted">Select a session first</p>';
            return;
        }
        
        try {
            console.log('Loading groups for session:', session);
            
            // Load groups for the session
            const response = await this.apiCall(`/api/groups/${session}/for-campaign`);
            console.log('Groups response:', response);
            
            // Handle both possible response formats
            const groups = response.groups || response.data || [];
            
            if (!Array.isArray(groups)) {
                console.error('Groups is not an array:', groups);
                groupsContainer.innerHTML = '<p class="text-warning">No groups available. Make sure you have joined some groups.</p>';
                return;
            }
            
            if (groups.length === 0) {
                groupsContainer.innerHTML = '<p class="text-muted">No groups found for this session. Join some groups first.</p>';
                return;
            }
            
            groupsContainer.innerHTML = groups.map(group => {
                // Create safe ID for HTML element (replace @ and . with underscores)
                const safeId = (group.id || '').replace(/@/g, '_at_').replace(/\./g, '_dot_').replace(/:/g, '_');
                return `
                    <div class="form-check">
                        <input class="form-check-input group-select-checkbox" 
                               type="checkbox" 
                               value="${group.id || ''}" 
                               data-group-id="${group.id || ''}"
                               id="group-${safeId}"
                               onchange="app.updateWizardButtons()">
                        <label class="form-check-label" for="group-${safeId}">
                            ${group.name || 'Unnamed Group'} 
                            <small class="text-muted">(${group.participantCount || group.participant_count || 0} members)</small>
                        </label>
                    </div>
                `;
            }).join('');
            
            // Update buttons after loading groups
            this.updateWizardButtons();
            
        } catch (error) {
            console.error('Error loading groups:', error);
            console.error('Error details:', error.message);
            groupsContainer.innerHTML = `<p class="text-danger">Failed to load groups: ${error.message}</p>`;
        }
    }
    
    async loadSourceContacts(sessionName = null) {
        const sessionSelect = document.getElementById('modal-campaign-session');
        const contactsContainer = document.getElementById('contact-selection-list');
        const session = sessionName || sessionSelect?.value;
        
        if (!session) return;
        
        try {
            console.log('Loading contacts for session:', session);
            
            // Load contacts for the session
            const response = await this.apiCall(`/api/contacts/${session}/for-campaign`);
            console.log('Contacts response:', response);
            
            const contacts = response.contacts || response.data || [];
            const summary = response.summary || {};
            
            // Store contacts for later use
            this.availableContacts = contacts;
            
            // Update contact counts
            const allCountElement = document.getElementById('all-contacts-count');
            const myCountElement = document.getElementById('my-contacts-count');
            
            if (allCountElement) allCountElement.textContent = summary.total_contacts || 0;
            if (myCountElement) myCountElement.textContent = summary.my_contacts_count || 0;
            
            // Update info text
            const infoElement = document.getElementById('contacts-info');
            if (infoElement) {
                infoElement.textContent = `Found ${summary.total_contacts} contacts (${summary.my_contacts_count} saved, ${summary.other_contacts_count} with chat history)`;
            }
            
            // Populate contact checkboxes if container exists
            if (contactsContainer && contacts.length > 0) {
                contactsContainer.innerHTML = contacts.map(contact => {
                    // Create safe ID for HTML element
                    const safeId = contact.id.replace(/@/g, '_at_').replace(/\./g, '_dot_');
                    return `
                        <div class="form-check">
                            <input class="form-check-input contact-select-checkbox" 
                                   type="checkbox" 
                                   value="${contact.id}" 
                                   data-is-my-contact="${contact.isMyContact}"
                                   data-contact-id="${contact.id}"
                                   id="contact-${safeId}"
                                   onchange="app.updateWizardButtons()">
                            <label class="form-check-label" for="contact-${safeId}">
                                ${contact.display_name}
                                ${contact.isMyContact ? '<span class="badge bg-primary ms-1">Saved</span>' : ''}
                                ${contact.isBusiness ? '<span class="badge bg-info ms-1">Business</span>' : ''}
                            </label>
                        </div>
                    `;
                }).join('');
            } else if (contactsContainer) {
                contactsContainer.innerHTML = '<p class="text-muted">No contacts found for this session</p>';
            }
            
        } catch (error) {
            console.error('Error loading contacts:', error);
            if (contactsContainer) {
                contactsContainer.innerHTML = '<p class="text-danger">Failed to load contacts</p>';
            }
        }
    }
    
    toggleContactList() {
        const contactListContainer = document.getElementById('contact-selection-list');
        const selectedOption = document.querySelector('input[name="contact-selection"]:checked')?.value;
        
        if (contactListContainer) {
            if (selectedOption === 'specific') {
                contactListContainer.style.display = 'block';
            } else {
                contactListContainer.style.display = 'none';
                
                // If switching to saved_only, automatically check only saved contacts
                if (selectedOption === 'saved_only' && this.availableContacts) {
                    const checkboxes = document.querySelectorAll('.contact-select-checkbox');
                    checkboxes.forEach(cb => {
                        cb.checked = cb.dataset.isMyContact === 'true';
                    });
                }
            }
        }
        
        // Update button state when contact selection mode changes
        this.updateWizardButtons();
    }

    refreshData() {
        this.checkServerStatus();
        this.loadSessions();
        
        const currentSection = document.querySelector('[id$="-section"]:not([style*="display: none"])');
        if (currentSection) {
            const sectionName = currentSection.id.replace('-section', '');
            switch (sectionName) {
                case 'chats':
                    this.loadChats();
                    break;
                case 'contacts':
                    this.loadContacts();
                    break;
                case 'groups':
                    this.loadGroups();
                    break;
                case 'campaigns':
                    this.loadCampaigns();
                    this.loadProcessingStatus();
                    break;
                case 'analytics':
                    this.loadAnalytics();
                    break;
                case 'warmer':
                    this.loadWarmerSessions();
                    break;
            }
        }
    }
}

// Global functions for HTML onclick events
window.showSection = function(section) {
    // Get the event from the global window.event (for onclick handlers)
    const clickEvent = window.event || event;
    // Temporarily store the event so showSection can access it
    const originalEvent = window.event;
    window.event = clickEvent;
    app.showSection(section);
    window.event = originalEvent;
};
window.createSession = () => app.createSession();
window.loadSessions = () => app.loadSessions();
window.loadChats = () => app.loadChats();
window.loadContacts = () => app.loadContacts();
window.loadGroups = () => app.loadGroups();
window.filterContacts = () => app.filterContacts();
window.checkNumber = () => app.checkNumber();
window.createGroup = () => app.createGroup();
window.loadGroupDetails = (groupId) => app.loadGroupDetails(groupId);
window.exportGroupParticipants = (groupId, groupName) => app.exportGroupParticipants(groupId, groupName);
window.exportContacts = () => app.exportContacts();
window.sendTextMessage = () => app.sendTextMessage();
window.sendFileMessage = () => app.sendFileMessage();
window.sendLocationMessage = () => app.sendLocationMessage();
window.refreshData = () => app.refreshData();

// Phase 2: Campaign Management Functions
window.loadCampaigns = () => app.loadCampaigns();
window.selectCampaign = (id) => app.selectCampaign(id);
window.startCampaign = (id) => app.startCampaign(id);
window.pauseCampaign = (id) => app.pauseCampaign(id);
window.resumeCampaign = (id) => app.resumeCampaign(id);
window.stopCampaign = (id) => app.stopCampaign(id);
window.deleteCampaign = (id) => app.deleteCampaign(id);
window.cancelSchedule = (id) => app.cancelSchedule(id);
window.viewCampaignReport = (id) => app.viewCampaignReport(id);
window.showRestartCampaignModal = (id) => app.showRestartCampaignModal(id);
window.restartCampaign = () => app.restartCampaign();
window.closeReportAndShowRestart = (id) => {
    // Close the report modal first
    const reportModal = document.getElementById('campaignReportModal');
    if (reportModal) {
        const modal = bootstrap.Modal.getInstance(reportModal);
        if (modal) {
            modal.hide();
        }
    }
    // Wait a bit for the modal to close, then show restart modal
    setTimeout(() => {
        app.showRestartCampaignModal(id);
    }, 300);
};

// Modal Campaign Wizard Functions
window.modalNextStep = () => app.modalNextStep();
window.modalPrevStep = () => app.modalPrevStep();
window.handleModalFileUpload = () => app.handleModalFileUpload();
window.toggleModalMessageMode = () => app.toggleModalMessageMode();
window.addModalSample = () => app.addModalSample();
window.removeModalSample = (btn) => app.removeModalSample(btn);
window.generateSimilarTemplates = () => app.generateSimilarTemplates();
window.launchModalCampaign = () => app.launchModalCampaign();
window.saveModalCampaignDraft = () => app.saveModalCampaignDraft();
window.previewModalTemplate = () => app.previewModalTemplate();

// Source Selection Functions
window.toggleSourceOptions = () => app.toggleSourceOptions();
window.loadSourceOptions = () => app.loadSourceOptions();
window.toggleContactList = () => app.toggleContactList();

// WhatsApp Warmer Functions
window.loadWarmerSessions = () => app.loadWarmerSessions();
window.showCreateWarmerModal = () => app.showCreateWarmerModal();
window.createWarmerSession = () => app.createWarmerSession();
window.startWarmer = (id) => app.startWarmer(id);
window.stopWarmer = (id) => app.stopWarmer(id);
window.deleteWarmer = (id) => app.deleteWarmer(id);
window.viewWarmerMetrics = (id) => app.viewWarmerMetrics(id);
window.showManageSessionsModal = (id) => app.showManageSessionsModal(id);
window.addSessionToWarmer = (warmerId, sessionName) => app.addSessionToWarmer(warmerId, sessionName);
window.removeSessionFromWarmer = (warmerId, sessionName) => app.removeSessionFromWarmer(warmerId, sessionName);
window.showAddGroupsModal = (id) => app.showAddGroupsModal(id);
window.addGroupsToWarmer = () => app.addGroupsToWarmer();
window.removeGroupFromWarmer = (warmerId, groupId) => app.removeGroupFromWarmer(warmerId, groupId);
window.showJoinGroupsModal = (id) => app.showJoinGroupsModal(id);
window.showJoinGroupsModalForStart = (id, groupCheck) => app.showJoinGroupsModalForStart(id, groupCheck);
window.joinGroupsForWarmer = () => app.joinGroupsForWarmer();

// Schedule UI Functions
function toggleScheduleOptions() {
    const launchOption = document.querySelector('input[name="launchOption"]:checked')?.value;
    const scheduleSection = document.getElementById('scheduleTimeSection');
    const launchBtnText = document.getElementById('launch-btn-text');
    
    if (launchOption === 'scheduled') {
        scheduleSection.style.display = 'block';
        if (launchBtnText) {
            launchBtnText.textContent = 'Schedule Campaign';
        }
        
        // Set minimum date to today
        const today = new Date().toISOString().split('T')[0];
        const dateInput = document.getElementById('scheduleDate');
        if (dateInput) {
            dateInput.min = today;
            if (!dateInput.value) {
                dateInput.value = today;
            }
        }
        
        // Set default time to current time + 1 hour
        const timeInput = document.getElementById('scheduleTime');
        if (timeInput && !timeInput.value) {
            const now = new Date();
            now.setHours(now.getHours() + 1);
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            timeInput.value = `${hours}:${minutes}`;
        }
    } else {
        scheduleSection.style.display = 'none';
        if (launchBtnText) {
            launchBtnText.textContent = 'Launch Campaign';
        }
    }
}

// Start All Campaigns Function
async function startAllCampaigns() {
    if (!confirm('This will start all created campaigns (excluding scheduled ones) sequentially. Continue?')) {
        return;
    }
    
    try {
        const response = await fetch(getDynamicUrl('/api/campaigns/start-all'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                skip_scheduled: true  // Skip scheduled campaigns
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start campaigns');
        }
        
        const result = await response.json();
        
        if (result.success) {
            if (result.campaigns_queued === 0) {
                app.showToast('No unscheduled campaigns found to start. All created campaigns are either scheduled or already running.', 'warning');
            } else {
                app.showToast(`Starting ${result.campaigns_queued} campaigns sequentially`, 'success');
            }
            
            // Refresh campaign list
            if (app) {
                app.loadCampaigns();
            }
        }
    } catch (error) {
        console.error('Error starting all campaigns:', error);
        if (app) {
            app.showToast(error.message || 'Failed to start campaigns', 'danger');
        } else {
            alert(error.message || 'Failed to start campaigns');
        }
    }
}

// Schedule Individual Campaign
async function scheduleCampaign(campaignId) {
    const planType = app?.userSubscription?.plan_type || 'free';
    const hasScheduling = ['hobby', 'pro', 'premium'].includes(planType);
    
    if (!hasScheduling) {
        app.showToast('Campaign scheduling is available for Hobby, Pro, and Premium plans only', 'warning');
        return;
    }
    
    // Create modal HTML if it doesn't exist
    if (!document.getElementById('scheduleCampaignModal')) {
        const modalHtml = `
            <div class="modal fade" id="scheduleCampaignModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Schedule Campaign</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">Schedule Date</label>
                                <input type="date" class="form-control" id="scheduleCampaignDate">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Schedule Time (Your Local Time)</label>
                                <input type="time" class="form-control" id="scheduleCampaignTime">
                                <small class="text-muted">Time will be converted to UTC for scheduling</small>
                            </div>
                            <div class="alert alert-info">
                                <i class="bi bi-info-circle"></i> Active warmers will be automatically paused when this campaign starts.
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="confirmScheduleCampaign('${campaignId}')">
                                <i class="bi bi-clock"></i> Schedule Campaign
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
    
    // Set minimum date to today
    const dateInput = document.getElementById('scheduleCampaignDate');
    const today = new Date().toISOString().split('T')[0];
    dateInput.min = today;
    dateInput.value = today;
    
    // Set default time to 1 hour from now
    const now = new Date();
    now.setHours(now.getHours() + 1);
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    document.getElementById('scheduleCampaignTime').value = `${hours}:${minutes}`;
    
    // Update the confirm button with the campaign ID
    const confirmBtn = document.querySelector('#scheduleCampaignModal .modal-footer .btn-primary');
    confirmBtn.setAttribute('onclick', `confirmScheduleCampaign('${campaignId}')`);
    
    // Initialize and show the modal
    const modal = new bootstrap.Modal(document.getElementById('scheduleCampaignModal'));
    modal.show();
}

// Confirm Schedule Campaign
async function confirmScheduleCampaign(campaignId) {
    const date = document.getElementById('scheduleCampaignDate').value;
    const time = document.getElementById('scheduleCampaignTime').value;
    
    if (!date || !time) {
        app.showToast('Please select both date and time', 'warning');
        return;
    }
    
    const scheduledTime = new Date(`${date}T${time}`);
    
    if (scheduledTime <= new Date()) {
        app.showToast('Scheduled time must be in the future', 'warning');
        return;
    }
    
    try {
        const response = await fetch(getDynamicUrl('/api/campaigns/schedule'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                campaign_id: parseInt(campaignId),
                scheduled_time: scheduledTime.toISOString(),
                user_id: app.getUserId()  // Include user_id for permission check
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to schedule campaign');
        }
        
        const result = await response.json();
        
        app.showToast('Campaign scheduled successfully', 'success');
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('scheduleCampaignModal'));
        modal.hide();
        
        // Refresh campaign list
        if (app) {
            app.loadCampaigns();
        }
    } catch (error) {
        console.error('Error scheduling campaign:', error);
        app.showToast(error.message || 'Failed to schedule campaign', 'danger');
    }
}

// Schedule Start All Campaigns
async function scheduleStartAll() {
    const planType = app?.userSubscription?.plan_type || 'free';
    const hasScheduling = ['hobby', 'pro', 'premium'].includes(planType);
    
    if (!hasScheduling) {
        app.showToast('Campaign scheduling is available for Hobby, Pro, and Premium plans only', 'warning');
        return;
    }
    
    // Create modal HTML if it doesn't exist
    if (!document.getElementById('scheduleStartAllModal')) {
        const modalHtml = `
            <div class="modal fade" id="scheduleStartAllModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Schedule Start All Campaigns</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">Schedule Date</label>
                                <input type="date" class="form-control" id="scheduleAllDate">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Schedule Time (Your Local Time)</label>
                                <input type="time" class="form-control" id="scheduleAllTime">
                                <small class="text-muted">Time will be converted to UTC for scheduling</small>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">
                                    Stagger Interval 
                                    <i class="bi bi-info-circle" data-bs-toggle="tooltip" title="Space out campaign start times by this many seconds"></i>
                                </label>
                                <select class="form-select" id="scheduleStagger">
                                    <option value="0">No stagger (all at same time)</option>
                                    <option value="30" selected>30 seconds apart</option>
                                    <option value="60">1 minute apart</option>
                                    <option value="120">2 minutes apart</option>
                                    <option value="300">5 minutes apart</option>
                                </select>
                                <small class="text-muted">Campaigns will start sequentially with this delay between each</small>
                            </div>
                            <div class="alert alert-info">
                                <i class="bi bi-info-circle"></i> All created campaigns (excluding already scheduled ones) will be scheduled with the specified interval between each.
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="confirmScheduleStartAll()">
                                <i class="bi bi-clock"></i> Schedule All
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
    
    // Set minimum date to today
    const dateInput = document.getElementById('scheduleAllDate');
    const today = new Date().toISOString().split('T')[0];
    dateInput.min = today;
    dateInput.value = today;
    
    // Set default time to 1 hour from now
    const now = new Date();
    now.setHours(now.getHours() + 1);
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    document.getElementById('scheduleAllTime').value = `${hours}:${minutes}`;
    
    // Initialize and show the modal
    const modal = new bootstrap.Modal(document.getElementById('scheduleStartAllModal'));
    modal.show();
}

// Confirm Schedule Start All
async function confirmScheduleStartAll() {
    const date = document.getElementById('scheduleAllDate').value;
    const time = document.getElementById('scheduleAllTime').value;
    const staggerSeconds = parseInt(document.getElementById('scheduleStagger').value) || 0;
    
    if (!date || !time) {
        app.showToast('Please select both date and time', 'warning');
        return;
    }
    
    const scheduledTime = new Date(`${date}T${time}`);
    
    if (scheduledTime <= new Date()) {
        app.showToast('Scheduled time must be in the future', 'warning');
        return;
    }
    
    // Log for debugging
    console.log('Schedule All - Local time selected:', scheduledTime.toLocaleString());
    console.log('Schedule All - UTC time to send:', scheduledTime.toISOString());
    console.log('Schedule All - Stagger seconds:', staggerSeconds);
    
    try {
        const response = await fetch(getDynamicUrl('/api/campaigns/schedule-all'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                scheduled_time: scheduledTime.toISOString(),
                skip_scheduled: true,
                stagger_seconds: staggerSeconds
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to schedule campaigns');
        }
        
        const result = await response.json();
        
        if (result.campaigns_scheduled === 0) {
            app.showToast('No unscheduled campaigns found to schedule', 'warning');
        } else {
            const utcString = scheduledTime.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
            app.showToast(`${result.campaigns_scheduled} campaigns scheduled to start at ${scheduledTime.toLocaleString()} (${utcString})`, 'success');
        }
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('scheduleStartAllModal'));
        modal.hide();
        
        // Refresh campaign list
        if (app) {
            app.loadCampaigns();
        }
    } catch (error) {
        console.error('Error scheduling campaigns:', error);
        app.showToast(error.message || 'Failed to schedule campaigns', 'danger');
    }
}

// Stop All Campaigns Function
async function stopAllCampaigns() {
    if (!confirm('This will stop all running campaigns and reset queued campaigns. Continue?')) {
        return;
    }
    
    try {
        const response = await fetch(getDynamicUrl('/api/campaigns/stop-all'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to stop campaigns');
        }
        
        const result = await response.json();
        
        if (result.success) {
            if (result.total_affected === 0) {
                app.showToast('No campaigns to stop', 'info');
            } else {
                let message = `Stopped ${result.total_affected} campaign(s)`;
                if (result.campaigns_cancelled > 0) {
                    message += ` - ${result.campaigns_cancelled} cancelled`;
                }
                if (result.campaigns_reset > 0) {
                    message += `, ${result.campaigns_reset} reset to created`;
                }
                app.showToast(message, 'success');
            }
            
            // Refresh campaign list
            if (app) {
                app.loadCampaigns();
            }
        }
    } catch (error) {
        console.error('Error stopping all campaigns:', error);
        if (app) {
            app.showToast(error.message || 'Failed to stop campaigns', 'danger');
        } else {
            alert(error.message || 'Failed to stop campaigns');
        }
    }
}

// Password Reset Functions
function openPasswordReset() {
    const modal = new bootstrap.Modal(document.getElementById('passwordResetModal'));
    modal.show();
}

function redirectToPasswordReset() {
    // Redirect to Clerk's password reset page
    window.location.href = 'https://auth.cuwapp.com/sign-in#/reset-password';
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        // Redirect to Clerk logout page
        window.location.href = 'https://auth.cuwapp.com/logout';
    }
}

// Initialize app when DOM is loaded
let app;
document.addEventListener('DOMContentLoaded', () => {
    try {
        app = new WhatsAppAgent();
        console.log('WhatsApp Agent initialized successfully');
        
        // Add event listeners for scheduling options
        const launchNowRadio = document.getElementById('launchNow');
        const launchScheduledRadio = document.getElementById('launchScheduled');
        
        if (launchNowRadio) {
            launchNowRadio.addEventListener('change', toggleScheduleOptions);
        }
        if (launchScheduledRadio) {
            launchScheduledRadio.addEventListener('change', toggleScheduleOptions);
        }
    } catch (error) {
        console.error('Error initializing WhatsApp Agent:', error);
        // Show error to user
        document.body.innerHTML = `
            <div class="container mt-5">
                <div class="alert alert-danger">
                    <h4>Error Loading Application</h4>
                    <p>There was an error initializing the application. Please check the console for details.</p>
                    <pre>${error.message}</pre>
                </div>
            </div>
        `;
    }
});