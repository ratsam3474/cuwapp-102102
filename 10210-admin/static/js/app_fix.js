// FIX 1: Update populateSessionSelects to include modal-campaign-session
// Find the populateSessionSelects function and replace it with this:

populateSessionSelects() {
    const selects = [
        'chat-session-select', 'contacts-session-select', 'groups-session-select',
        'check-session-select', 'group-session-select', 'message-session-select',
        'modal-campaign-session'  // ← ADDED THIS FOR CAMPAIGN MODAL
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

// FIX 2: Replace handleModalFileUpload with real API call
async handleModalFileUpload() {
    const fileInput = document.getElementById('modal-campaign-file');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    const fileInfo = document.getElementById('modal-file-info');
    
    // Show file info with loading state
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
    
    try {
        // Prepare form data for upload
        const formData = new FormData();
        formData.append('file', file);
        
        // Upload file to backend
        const uploadResponse = await fetch('/api/files/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const uploadResult = await uploadResponse.json();
        
        if (uploadResult.success) {
            // Store the uploaded file data
            this.uploadedFileData = uploadResult.data;
            
            // Display success with file info
            fileInfo.innerHTML = `
                <div class="file-info-card">
                    <div class="d-flex align-items-center">
                        <div class="file-icon">
                            <i class="bi bi-check-circle-fill text-success"></i>
                        </div>
                        <div class="flex-grow-1">
                            <div class="fw-bold">${file.name}</div>
                            <small class="text-success">✅ ${uploadResult.data.total_rows} rows found</small>
                            <div class="mt-1">
                                <small class="text-muted">Headers: ${uploadResult.data.headers.join(', ')}</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Update Step 2 with column mapping
            this.updateDataMappingStep(uploadResult.data);
            
            this.showToast('File uploaded successfully', 'success');
            this.updateWizardButtons();
        } else {
            throw new Error('Upload failed');
        }
        
    } catch (error) {
        console.error('File upload error:', error);
        
        // Show error state
        fileInfo.innerHTML = `
            <div class="file-info-card">
                <div class="d-flex align-items-center">
                    <div class="file-icon">
                        <i class="bi bi-x-circle-fill text-danger"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-bold">${file.name}</div>
                        <small class="text-danger">❌ Upload failed: ${error.message}</small>
                        <div class="mt-1">
                            <button class="btn btn-sm btn-outline-primary" onclick="document.getElementById('modal-campaign-file').click()">
                                Try Again
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.showToast(`Upload failed: ${error.message}`, 'error');
        this.uploadedFileData = null;
        this.updateWizardButtons();
    }
}

// ADD NEW FUNCTION: Update data mapping step with real data
updateDataMappingStep(fileData) {
    const mappingContainer = document.getElementById('modal-column-mapping');
    const previewContainer = document.getElementById('modal-data-preview');
    
    if (!mappingContainer || !previewContainer) return;
    
    // Build column mapping UI
    const suggestedMapping = fileData.suggested_mapping || {};
    const requiredFields = ['phone_number', 'name'];
    const optionalFields = ['company', 'custom_field_1', 'custom_field_2'];
    
    mappingContainer.innerHTML = `
        <div class="mb-3">
            <p class="text-muted mb-2">Map your CSV columns to campaign fields:</p>
            
            <h6 class="text-danger mb-2">Required Fields:</h6>
            ${requiredFields.map(field => `
                <div class="mb-2">
                    <label class="form-label text-capitalize">${field.replace('_', ' ')} *</label>
                    <select class="form-select form-select-sm column-mapping" data-field="${field}">
                        <option value="">-- Select Column --</option>
                        ${fileData.headers.map(header => `
                            <option value="${header}" ${suggestedMapping[field] === header ? 'selected' : ''}>
                                ${header}
                            </option>
                        `).join('')}
                    </select>
                </div>
            `).join('')}
            
            <h6 class="text-info mb-2 mt-3">Optional Fields:</h6>
            ${optionalFields.map(field => `
                <div class="mb-2">
                    <label class="form-label text-capitalize">${field.replace('_', ' ')}</label>
                    <select class="form-select form-select-sm column-mapping" data-field="${field}">
                        <option value="">-- None --</option>
                        ${fileData.headers.map(header => `
                            <option value="${header}" ${suggestedMapping[field] === header ? 'selected' : ''}>
                                ${header}
                            </option>
                        `).join('')}
                    </select>
                </div>
            `).join('')}
        </div>
    `;
    
    // Build data preview
    if (fileData.sample_data && fileData.sample_data.length > 0) {
        previewContainer.innerHTML = `
            <table class="table table-sm table-bordered">
                <thead>
                    <tr>
                        ${fileData.headers.map(header => `<th>${header}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${fileData.sample_data.slice(0, 5).map(row => `
                        <tr>
                            ${fileData.headers.map(header => `<td>${row[header] || ''}</td>`).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            <small class="text-muted">Showing first 5 rows of ${fileData.total_rows} total</small>
        `;
    }
}

// UPDATE validateCurrentStep to check column mappings
validateCurrentStep() {
    switch (this.currentWizardStep) {
        case 1:
            const name = document.getElementById('modal-campaign-name').value;
            const session = document.getElementById('modal-campaign-session').value;
            const file = document.getElementById('modal-campaign-file').files[0];
            return name && session && file && this.uploadedFileData;
            
        case 2:
            // Check if required fields are mapped
            const phoneMapping = document.querySelector('[data-field="phone_number"]')?.value;
            const nameMapping = document.querySelector('[data-field="name"]')?.value;
            return this.uploadedFileData && phoneMapping && nameMapping;
            
        case 3:
            return true; // Template validation
            
        case 4:
            return true;
            
        default:
            return false;
    }
}

// UPDATE launchModalCampaign to use real data
async launchModalCampaign() {
    try {
        // Get all form data
        const campaignData = this.prepareCampaignData();
        
        // Get column mapping
        const columnMapping = {};
        document.querySelectorAll('.column-mapping').forEach(select => {
            const field = select.dataset.field;
            const value = select.value;
            if (value) {
                columnMapping[field] = value;
            }
        });
        
        // Add file data and mapping
        campaignData.file_path = this.uploadedFileData.file_path;
        campaignData.column_mapping = columnMapping;
        campaignData.start_row = parseInt(document.getElementById('modal-start-row')?.value) || 1;
        campaignData.end_row = document.getElementById('modal-end-row')?.value || null;
        if (campaignData.end_row) {
            campaignData.end_row = parseInt(campaignData.end_row);
        }
        
        // Create campaign with proper data
        const response = await this.apiCall('/api/campaigns', {
            method: 'POST',
            body: JSON.stringify(campaignData)
        });
        
        if (response.success || response.id) {
            this.showToast('Campaign created successfully!', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('campaignWizardModal'));
            if (modal) modal.hide();
            
            // Reset wizard
            this.currentWizardStep = 1;
            this.uploadedFileData = null;
            document.getElementById('modal-campaign-file').value = '';
            document.getElementById('modal-file-info').style.display = 'none';
            
            // Refresh campaigns list
            this.loadCampaigns();
            this.loadProcessingStatus();
        } else {
            throw new Error(response.error || 'Campaign creation failed');
        }
        
    } catch (error) {
        console.error('Error launching campaign:', error);
        this.showToast('Failed to launch campaign: ' + error.message, 'error');
    }
}

// UPDATE showWizardStep to handle step 4 review
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
    
    // If moving to step 4, show campaign summary
    if (stepNumber === 4 && this.uploadedFileData) {
        this.showCampaignSummary();
    }
    
    // Update buttons
    this.updateWizardButtons();
}

// ADD NEW FUNCTION: Show campaign summary
showCampaignSummary() {
    const summaryContainer = document.getElementById('modal-campaign-summary');
    if (!summaryContainer) return;
    
    const name = document.getElementById('modal-campaign-name').value;
    const session = document.getElementById('modal-campaign-session').value;
    const startRow = document.getElementById('modal-start-row').value || 1;
    const endRow = document.getElementById('modal-end-row').value || this.uploadedFileData.total_rows;
    const delay = document.getElementById('modal-delay-seconds').value;
    const mode = document.querySelector('input[name="modalMessageMode"]:checked').value;
    
    summaryContainer.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-primary mb-3">Campaign Details</h6>
                <table class="table table-sm">
                    <tr>
                        <th>Campaign Name:</th>
                        <td>${name}</td>
                    </tr>
                    <tr>
                        <th>WhatsApp Session:</th>
                        <td>${session}</td>
                    </tr>
                    <tr>
                        <th>File:</th>
                        <td>${this.uploadedFileData.filename}</td>
                    </tr>
                    <tr>
                        <th>Total Recipients:</th>
                        <td>${endRow - startRow + 1} contacts</td>
                    </tr>
                    <tr>
                        <th>Row Range:</th>
                        <td>${startRow} to ${endRow}</td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6 class="text-primary mb-3">Message Settings</h6>
                <table class="table table-sm">
                    <tr>
                        <th>Message Mode:</th>
                        <td>${mode === 'single' ? '📝 Single Template' : '🎲 Multiple Samples'}</td>
                    </tr>
                    <tr>
                        <th>Delay Between Messages:</th>
                        <td>${delay} seconds</td>
                    </tr>
                    <tr>
                        <th>Estimated Duration:</th>
                        <td>${Math.ceil(((endRow - startRow + 1) * delay) / 60)} minutes</td>
                    </tr>
                    <tr>
                        <th>Daily Limit:</th>
                        <td>${document.getElementById('modal-max-daily').value} messages</td>
                    </tr>
                </table>
            </div>
        </div>
    `;
}
