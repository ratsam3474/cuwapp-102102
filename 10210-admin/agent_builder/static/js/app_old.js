/**
 * Agent Builder Frontend Application
 */

// Global state
let currentAgent = null;
let selectedTriggers = new Set();
let selectedTools = {
    waha: new Set(),
    builtin: new Set(),
    mcp: new Set(),
    custom: new Set()
};
let triggerInstructions = {};

// API client
const api = {
    async fetchAgents() {
        const response = await fetch('/api/agents');
        return response.json();
    },
    
    async fetchAgent(id) {
        const response = await fetch(`/api/agents/${id}`);
        return response.json();
    },
    
    async createAgent(data) {
        const response = await fetch('/api/agents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    async updateAgent(id, data) {
        const response = await fetch(`/api/agents/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    async deleteAgent(id) {
        const response = await fetch(`/api/agents/${id}`, {
            method: 'DELETE'
        });
        return response.json();
    },
    
    async fetchTriggers() {
        const response = await fetch('/api/triggers');
        return response.json();
    },
    
    async fetchTools() {
        const response = await fetch('/api/tools');
        return response.json();
    },
    
    // Lifecycle operations
    async startAgent(id) {
        const response = await fetch(`/api/agents/${id}/start`, { method: 'POST' });
        return response.json();
    },
    
    async stopAgent(id) {
        const response = await fetch(`/api/agents/${id}/stop`, { method: 'POST' });
        return response.json();
    },
    
    async pauseAgent(id) {
        const response = await fetch(`/api/agents/${id}/pause`, { method: 'POST' });
        return response.json();
    },
    
    async resumeAgent(id) {
        const response = await fetch(`/api/agents/${id}/resume`, { method: 'POST' });
        return response.json();
    },
    
    async restartAgent(id) {
        const response = await fetch(`/api/agents/${id}/restart`, { method: 'POST' });
        return response.json();
    },
    
    async getAgentStatus(id) {
        const response = await fetch(`/api/agents/${id}/status`);
        return response.json();
    },
    
    async getAgentLogs(id, lines = 100) {
        const response = await fetch(`/api/agents/${id}/logs?lines=${lines}`);
        return response.json();
    }
};

// UI Functions
function showCreateAgent() {
    currentAgent = null;
    selectedTriggers.clear();
    selectedTools.waha.clear();
    selectedTools.builtin.clear();
    selectedTools.mcp.clear();
    selectedTools.custom.clear();
    triggerInstructions = {};
    
    document.getElementById('agent-form').classList.remove('hidden');
    document.getElementById('form-title').textContent = 'Create New Agent';
    document.getElementById('agent-name').value = '';
    document.getElementById('agent-description').value = '';
    document.getElementById('additional-instructions').value = '';
    document.getElementById('model-select').value = 'gemini-2.0-flash';
    document.getElementById('temperature').value = 0.7;
    document.getElementById('temperature-value').textContent = '0.7';
    
    loadTriggers();
    loadTools();
}

function cancelAgentForm() {
    document.getElementById('agent-form').classList.add('hidden');
}

async function loadAgents() {
    try {
        const agents = await api.fetchAgents();
        const agentsList = document.getElementById('agents-list');
        
        if (agents.length === 0) {
            agentsList.innerHTML = '<div class="empty-state">No agents yet. Create your first agent!</div>';
            return;
        }
        
        agentsList.innerHTML = agents.map(agent => createAgentCard(agent)).join('');
    } catch (error) {
        console.error('Failed to load agents:', error);
    }
}

function createAgentCard(agent) {
    const statusClass = agent.status === 'active' ? 'status-active' : 
                       agent.status === 'error' ? 'status-error' : 'status-inactive';
    
    return `
        <div class="agent-card" data-agent-id="${agent.id}">
            <div class="agent-header">
                <h3>${agent.name}</h3>
                <span class="agent-status ${statusClass}">${agent.status}</span>
            </div>
            <p class="agent-description">${agent.description || 'No description'}</p>
            <div class="agent-meta">
                <span>🎯 ${agent.triggers.length} triggers</span>
                <span>🛠️ ${getTotalToolsCount(agent.tools)} tools</span>
                <span>🤖 ${agent.model}</span>
            </div>
            <div class="agent-controls">
                ${renderAgentControls(agent)}
            </div>
            <div class="agent-actions">
                <button class="btn btn-sm" onclick="editAgent('${agent.id}')">Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deleteAgentConfirm('${agent.id}')">Delete</button>
            </div>
        </div>
    `;
}

function renderAgentControls(agent) {
    if (agent.status === 'active') {
        return `
            <button class="btn btn-sm btn-warning" onclick="pauseAgent('${agent.id}')">⏸️ Pause</button>
            <button class="btn btn-sm btn-danger" onclick="stopAgent('${agent.id}')">⏹️ Stop</button>
            <button class="btn btn-sm" onclick="viewLogs('${agent.id}')">📋 Logs</button>
        `;
    } else if (agent.status === 'paused') {
        return `
            <button class="btn btn-sm btn-success" onclick="resumeAgent('${agent.id}')">▶️ Resume</button>
            <button class="btn btn-sm btn-danger" onclick="stopAgent('${agent.id}')">⏹️ Stop</button>
            <button class="btn btn-sm" onclick="viewLogs('${agent.id}')">📋 Logs</button>
        `;
    } else {
        return `
            <button class="btn btn-sm btn-success" onclick="startAgent('${agent.id}')">▶️ Start</button>
            <button class="btn btn-sm" onclick="viewLogs('${agent.id}')">📋 Logs</button>
        `;
    }
}

function getTotalToolsCount(tools) {
    return (tools.waha_tools?.length || 0) + 
           (tools.builtin_tools?.length || 0) + 
           (tools.mcp_tools?.length || 0) + 
           (tools.custom_tools?.length || 0);
}

async function loadTriggers() {
    try {
        const triggers = await api.fetchTriggers();
        const triggersList = document.getElementById('triggers-list');
        
        let html = '';
        for (const [category, items] of Object.entries(triggers)) {
            html += `<div class="trigger-category">
                <h4>${category}</h4>
                <div class="triggers-group">`;
            
            for (const trigger of items) {
                const checked = selectedTriggers.has(trigger.id) ? 'checked' : '';
                html += `
                    <label class="trigger-item">
                        <input type="checkbox" value="${trigger.id}" ${checked} 
                               onchange="toggleTrigger('${trigger.id}')">
                        <span class="trigger-icon">${trigger.icon}</span>
                        <div class="trigger-info">
                            <div class="trigger-name">${trigger.name}</div>
                            <div class="trigger-description">${trigger.description}</div>
                        </div>
                    </label>
                `;
            }
            
            html += '</div></div>';
        }
        
        triggersList.innerHTML = html;
        updateTriggerInstructions();
    } catch (error) {
        console.error('Failed to load triggers:', error);
    }
}

function toggleTrigger(triggerId) {
    if (selectedTriggers.has(triggerId)) {
        selectedTriggers.delete(triggerId);
        delete triggerInstructions[triggerId];
    } else {
        selectedTriggers.add(triggerId);
    }
    updateTriggerInstructions();
}

function updateTriggerInstructions() {
    const container = document.getElementById('trigger-instructions');
    
    if (selectedTriggers.size === 0) {
        container.innerHTML = '<p class="text-muted">Select triggers to configure their instructions</p>';
        return;
    }
    
    let html = '';
    for (const triggerId of selectedTriggers) {
        const value = triggerInstructions[triggerId] || '';
        html += `
            <div class="trigger-instruction">
                <label for="instruction-${triggerId}">${triggerId} Instructions</label>
                <textarea id="instruction-${triggerId}" 
                          placeholder="How should the agent respond to ${triggerId} events?"
                          onchange="updateTriggerInstruction('${triggerId}', this.value)"
                          rows="3">${value}</textarea>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

function updateTriggerInstruction(triggerId, value) {
    triggerInstructions[triggerId] = value;
}

async function loadTools() {
    try {
        const tools = await api.fetchTools();
        showToolCategory('waha');
    } catch (error) {
        console.error('Failed to load tools:', error);
    }
}

async function showToolCategory(category) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Load tools for category
    const tools = await api.fetchTools();
    const toolsList = document.getElementById('tools-list');
    
    let html = '<div class="tools-select-all">';
    html += `<label><input type="checkbox" onchange="toggleAllTools('${category}', this.checked)"> Select All</label>`;
    html += '</div>';
    
    html += '<div class="tools-grid">';
    
    const categoryTools = tools[category] || [];
    for (const tool of categoryTools) {
        const checked = selectedTools[category].has(tool.id) ? 'checked' : '';
        html += `
            <label class="tool-item">
                <input type="checkbox" value="${tool.id}" ${checked}
                       onchange="toggleTool('${category}', '${tool.id}')">
                <div class="tool-info">
                    <div class="tool-name">${tool.name}</div>
                    <div class="tool-description">${tool.description}</div>
                </div>
            </label>
        `;
    }
    
    html += '</div>';
    toolsList.innerHTML = html;
}

function toggleTool(category, toolId) {
    if (selectedTools[category].has(toolId)) {
        selectedTools[category].delete(toolId);
    } else {
        selectedTools[category].add(toolId);
    }
}

function toggleAllTools(category, checked) {
    const checkboxes = document.querySelectorAll('#tools-list input[type="checkbox"]:not(:first-child)');
    checkboxes.forEach(cb => {
        cb.checked = checked;
        const toolId = cb.value;
        if (checked) {
            selectedTools[category].add(toolId);
        } else {
            selectedTools[category].delete(toolId);
        }
    });
}

async function saveAgent() {
    const name = document.getElementById('agent-name').value;
    const description = document.getElementById('agent-description').value;
    const additionalInstructions = document.getElementById('additional-instructions').value;
    const model = document.getElementById('model-select').value;
    const temperature = parseFloat(document.getElementById('temperature').value);
    
    if (!name) {
        alert('Please enter an agent name');
        return;
    }
    
    if (selectedTriggers.size === 0) {
        alert('Please select at least one trigger');
        return;
    }
    
    const data = {
        name,
        description,
        triggers: Array.from(selectedTriggers),
        trigger_instructions: triggerInstructions,
        additional_instructions: additionalInstructions,
        tools: {
            waha_tools: Array.from(selectedTools.waha),
            builtin_tools: Array.from(selectedTools.builtin),
            mcp_tools: Array.from(selectedTools.mcp),
            custom_tools: Array.from(selectedTools.custom)
        },
        model,
        temperature,
        whatsapp_session: 'default'
    };
    
    try {
        if (currentAgent) {
            await api.updateAgent(currentAgent.id, data);
        } else {
            await api.createAgent(data);
        }
        
        cancelAgentForm();
        await loadAgents();
    } catch (error) {
        console.error('Failed to save agent:', error);
        alert('Failed to save agent: ' + error.message);
    }
}

async function editAgent(id) {
    try {
        const agent = await api.fetchAgent(id);
        currentAgent = agent;
        
        // Reset selections
        selectedTriggers.clear();
        selectedTools.waha.clear();
        selectedTools.builtin.clear();
        selectedTools.mcp.clear();
        selectedTools.custom.clear();
        
        // Load agent data
        document.getElementById('agent-name').value = agent.name;
        document.getElementById('agent-description').value = agent.description || '';
        document.getElementById('additional-instructions').value = agent.additional_instructions || '';
        document.getElementById('model-select').value = agent.model;
        document.getElementById('temperature').value = agent.temperature;
        document.getElementById('temperature-value').textContent = agent.temperature;
        
        // Load triggers
        agent.triggers.forEach(t => selectedTriggers.add(t));
        triggerInstructions = agent.trigger_instructions || {};
        
        // Load tools
        if (agent.tools) {
            agent.tools.waha_tools?.forEach(t => selectedTools.waha.add(t));
            agent.tools.builtin_tools?.forEach(t => selectedTools.builtin.add(t));
            agent.tools.mcp_tools?.forEach(t => selectedTools.mcp.add(t));
            agent.tools.custom_tools?.forEach(t => selectedTools.custom.add(t));
        }
        
        document.getElementById('form-title').textContent = 'Edit Agent';
        document.getElementById('agent-form').classList.remove('hidden');
        
        await loadTriggers();
        await loadTools();
    } catch (error) {
        console.error('Failed to load agent:', error);
    }
}

async function deleteAgentConfirm(id) {
    if (confirm('Are you sure you want to delete this agent?')) {
        try {
            await api.deleteAgent(id);
            await loadAgents();
        } catch (error) {
            console.error('Failed to delete agent:', error);
        }
    }
}

// Lifecycle operations
async function startAgent(id) {
    try {
        await api.startAgent(id);
        await loadAgents();
    } catch (error) {
        console.error('Failed to start agent:', error);
        alert('Failed to start agent: ' + error.message);
    }
}

async function stopAgent(id) {
    try {
        await api.stopAgent(id);
        await loadAgents();
    } catch (error) {
        console.error('Failed to stop agent:', error);
    }
}

async function pauseAgent(id) {
    try {
        await api.pauseAgent(id);
        await loadAgents();
    } catch (error) {
        console.error('Failed to pause agent:', error);
    }
}

async function resumeAgent(id) {
    try {
        await api.resumeAgent(id);
        await loadAgents();
    } catch (error) {
        console.error('Failed to resume agent:', error);
    }
}

async function viewLogs(id) {
    try {
        const result = await api.getAgentLogs(id);
        const logs = result.logs.join('');
        
        // Create modal to show logs
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Agent Logs</h3>
                    <button onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <pre class="logs-viewer">${logs || 'No logs available'}</pre>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    } catch (error) {
        console.error('Failed to get logs:', error);
    }
}

// Temperature slider
document.getElementById('temperature').addEventListener('input', function(e) {
    document.getElementById('temperature-value').textContent = e.target.value;
});

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    loadAgents();
    
    // Refresh agents every 10 seconds
    setInterval(loadAgents, 10000);
});