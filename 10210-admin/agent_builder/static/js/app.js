/**
 * WhatsApp Agent Builder - Modern UI
 */

// Global state
let currentAgent = null;
let selectedTriggers = new Set();
let selectedTools = {
    waha: new Set(),
    builtin: new Set()
};

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
        const response = await fetch('/api/triggers/flat');
        return response.json();
    },
    
    async fetchSessions() {
        const response = await fetch('https://app.cuwapp.com/api/sessions');
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

// Tab navigation
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        
        // Update active tab
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('tab-active'));
        btn.classList.add('tab-active');
        
        // Show/hide content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.add('hidden');
        });
        document.getElementById(`${tab}-tab`).classList.remove('hidden');
        
        // Load content for tab
        if (tab === 'agents') {
            loadAgents();
        } else if (tab === 'tools') {
            loadToolsTab();
        }
    });
});

// Temperature slider
function updateTemperatureValue(slider) {
    document.getElementById('temperature-value').textContent = slider.value;
}

// Load agents
async function loadAgents() {
    try {
        const agents = await api.fetchAgents();
        const grid = document.getElementById('agents-grid');
        
        if (agents.length === 0) {
            grid.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <i class="fas fa-robot text-6xl text-gray-300 mb-4"></i>
                    <p class="text-gray-500">No agents yet. Create your first agent!</p>
                    <button onclick="showCreateTab()" class="mt-4 bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700">
                        <i class="fas fa-plus mr-2"></i>Create Agent
                    </button>
                </div>
            `;
            return;
        }
        
        grid.innerHTML = agents.map(agent => createAgentCard(agent)).join('');
    } catch (error) {
        console.error('Failed to load agents:', error);
    }
}

function createAgentCard(agent) {
    const statusColor = agent.status === 'ACTIVE' ? 'green' : 
                       agent.status === 'ERROR' ? 'red' : 'gray';
    const statusIcon = agent.status === 'ACTIVE' ? 'fa-check-circle' : 
                      agent.status === 'ERROR' ? 'fa-exclamation-circle' : 'fa-pause-circle';
    
    return `
        <div class="bg-white rounded-lg shadow-md p-6 card-hover">
            <div class="flex justify-between items-start mb-4">
                <h3 class="text-lg font-semibold text-gray-800">${agent.name}</h3>
                <span class="text-${statusColor}-500">
                    <i class="fas ${statusIcon}"></i>
                </span>
            </div>
            
            <p class="text-gray-600 text-sm mb-4">${agent.description || 'No description'}</p>
            
            <div class="flex flex-wrap gap-2 mb-4">
                <span class="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                    <i class="fas fa-bolt mr-1"></i>${agent.triggers.length} triggers
                </span>
                <span class="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                    <i class="fas fa-tools mr-1"></i>${getTotalTools(agent)} tools
                </span>
                <span class="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                    <i class="fas fa-brain mr-1"></i>${agent.model}
                </span>
            </div>
            
            <div class="flex gap-2">
                ${renderAgentActions(agent)}
            </div>
        </div>
    `;
}

function getTotalTools(agent) {
    return (agent.waha_tools?.length || 0) + 
           (agent.builtin_tools?.length || 0) + 
           (agent.mcp_tools?.length || 0) + 
           (agent.custom_tools?.length || 0);
}

function renderAgentActions(agent) {
    let actions = '';
    
    if (agent.status === 'ACTIVE') {
        actions += `
            <button onclick="pauseAgent('${agent.id}')" class="text-yellow-600 hover:text-yellow-700" title="Pause">
                <i class="fas fa-pause"></i>
            </button>
            <button onclick="stopAgent('${agent.id}')" class="text-red-600 hover:text-red-700" title="Stop">
                <i class="fas fa-stop"></i>
            </button>
        `;
    } else {
        actions += `
            <button onclick="startAgent('${agent.id}')" class="text-green-600 hover:text-green-700" title="Start">
                <i class="fas fa-play"></i>
            </button>
        `;
    }
    
    actions += `
        <button onclick="showAgentDetails('${agent.id}')" class="text-blue-600 hover:text-blue-700 ml-auto" title="Details">
            <i class="fas fa-info-circle"></i>
        </button>
        <button onclick="deleteAgentConfirm('${agent.id}')" class="text-red-600 hover:text-red-700" title="Delete">
            <i class="fas fa-trash"></i>
        </button>
    `;
    
    return actions;
}

// Show create tab
function showCreateTab() {
    document.querySelector('[data-tab="create"]').click();
}

// Create agent form
document.getElementById('create-agent-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        name: formData.get('name'),
        description: formData.get('description'),
        whatsapp_session: formData.get('whatsapp_session'),
        model: formData.get('model'),
        temperature: parseFloat(formData.get('temperature')),
        triggers: Array.from(selectedTriggers),
        waha_tools: Array.from(selectedTools.waha),
        builtin_tools: Array.from(selectedTools.builtin),
        mcp_tools: [],
        custom_tools: [],
        root_instruction: formData.get('root_instruction'),
        trigger_instructions: {}
    };
    
    // Add trigger-specific instructions
    selectedTriggers.forEach(trigger => {
        const instructionEl = document.getElementById(`trigger-instruction-${trigger}`);
        if (instructionEl && instructionEl.value) {
            data.trigger_instructions[trigger] = instructionEl.value;
        }
    });
    
    try {
        if (currentAgent) {
            await api.updateAgent(currentAgent.id, data);
        } else {
            await api.createAgent(data);
        }
        
        // Reset form and switch to agents tab
        e.target.reset();
        selectedTriggers.clear();
        selectedTools.waha.clear();
        selectedTools.builtin.clear();
        currentAgent = null;
        
        document.querySelector('[data-tab="agents"]').click();
    } catch (error) {
        console.error('Failed to save agent:', error);
        alert('Failed to save agent: ' + error.message);
    }
});

// Load triggers
async function loadTriggers() {
    try {
        const triggers = await api.fetchTriggers();
        const grid = document.getElementById('triggers-grid');
        
        grid.innerHTML = triggers.map(trigger => `
            <div>
                <input type="checkbox" id="trigger-${trigger.id}" value="${trigger.id}" 
                    class="trigger-checkbox" onchange="toggleTrigger('${trigger.id}')">
                <label for="trigger-${trigger.id}" class="trigger-label block border-2 border-gray-200 rounded-lg p-3 text-sm">
                    <span class="text-lg">${trigger.icon}</span> ${trigger.name}
                    <div class="text-xs text-gray-500 mt-1">${trigger.description}</div>
                </label>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load triggers:', error);
    }
}

// Toggle trigger selection
function toggleTrigger(value) {
    if (selectedTriggers.has(value)) {
        selectedTriggers.delete(value);
        // Remove instruction field
        const instructionDiv = document.getElementById(`trigger-instruction-div-${value}`);
        if (instructionDiv) instructionDiv.remove();
    } else {
        selectedTriggers.add(value);
        // Add instruction field
        addTriggerInstructionField(value);
    }
}

// Add trigger instruction field
function addTriggerInstructionField(trigger) {
    const container = document.getElementById('triggers-grid').parentElement;
    const div = document.createElement('div');
    div.id = `trigger-instruction-div-${trigger}`;
    div.className = 'mt-4';
    div.innerHTML = `
        <label class="block text-sm font-medium text-gray-700 mb-2">
            Instructions for ${trigger}
        </label>
        <textarea id="trigger-instruction-${trigger}" rows="2" 
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            placeholder="How should the agent handle ${trigger} events?"></textarea>
    `;
    container.appendChild(div);
}

// Load tools
async function loadToolsForForm() {
    try {
        const tools = await api.fetchTools();
        
        // WAHA tools
        const wahaGrid = document.getElementById('waha-tools-grid');
        wahaGrid.innerHTML = tools.waha.map(tool => `
            <div>
                <input type="checkbox" id="waha-${tool.id}" value="${tool.id}" 
                    class="trigger-checkbox" onchange="toggleTool('waha', '${tool.id}')">
                <label for="waha-${tool.id}" class="trigger-label block border-2 border-gray-200 rounded-lg p-3 text-sm">
                    ${tool.name}
                </label>
            </div>
        `).join('');
        
        // Built-in tools
        const builtinGrid = document.getElementById('builtin-tools-grid');
        builtinGrid.innerHTML = tools.builtin.map(tool => `
            <div>
                <input type="checkbox" id="builtin-${tool.id}" value="${tool.id}" 
                    class="trigger-checkbox" onchange="toggleTool('builtin', '${tool.id}')">
                <label for="builtin-${tool.id}" class="trigger-label block border-2 border-gray-200 rounded-lg p-3 text-sm">
                    ${tool.name}
                </label>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load tools:', error);
    }
}

// Toggle tool selection
function toggleTool(category, id) {
    if (selectedTools[category].has(id)) {
        selectedTools[category].delete(id);
    } else {
        selectedTools[category].add(id);
    }
}

// Load tools tab
async function loadToolsTab() {
    try {
        const tools = await api.fetchTools();
        
        // WAHA tools list
        const wahaList = document.getElementById('tools-waha-list');
        wahaList.innerHTML = tools.waha.map(tool => `
            <div class="bg-white rounded-lg shadow p-4">
                <h4 class="font-medium text-gray-800">${tool.name}</h4>
                <p class="text-sm text-gray-600 mt-1">${tool.description}</p>
            </div>
        `).join('');
        
        // Built-in tools list
        const builtinList = document.getElementById('tools-builtin-list');
        builtinList.innerHTML = tools.builtin.map(tool => `
            <div class="bg-white rounded-lg shadow p-4">
                <h4 class="font-medium text-gray-800">${tool.name}</h4>
                <p class="text-sm text-gray-600 mt-1">${tool.description}</p>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load tools:', error);
    }
}

// Agent operations
async function startAgent(id) {
    try {
        const result = await api.startAgent(id);
        if (result.success) {
            loadAgents();
        } else {
            alert('Failed to start agent: ' + result.error);
        }
    } catch (error) {
        console.error('Failed to start agent:', error);
    }
}

async function stopAgent(id) {
    try {
        await api.stopAgent(id);
        loadAgents();
    } catch (error) {
        console.error('Failed to stop agent:', error);
    }
}

async function pauseAgent(id) {
    try {
        await api.pauseAgent(id);
        loadAgents();
    } catch (error) {
        console.error('Failed to pause agent:', error);
    }
}

async function deleteAgentConfirm(id) {
    if (confirm('Are you sure you want to delete this agent?')) {
        try {
            await api.deleteAgent(id);
            loadAgents();
        } catch (error) {
            console.error('Failed to delete agent:', error);
        }
    }
}

// Show agent details
async function showAgentDetails(id) {
    try {
        const agent = await api.fetchAgent(id);
        const status = await api.getAgentStatus(id);
        
        document.getElementById('modal-agent-name').textContent = agent.name;
        document.getElementById('modal-content').innerHTML = `
            <div class="space-y-4">
                <div>
                    <h4 class="font-medium text-gray-700">Status</h4>
                    <p class="text-gray-600">${status.state} ${status.running ? '(Running)' : ''}</p>
                    ${status.port ? `<p class="text-sm text-gray-500">Port: ${status.port}</p>` : ''}
                </div>
                
                <div>
                    <h4 class="font-medium text-gray-700">Description</h4>
                    <p class="text-gray-600">${agent.description || 'No description'}</p>
                </div>
                
                <div>
                    <h4 class="font-medium text-gray-700">Configuration</h4>
                    <p class="text-sm text-gray-600">Model: ${agent.model}</p>
                    <p class="text-sm text-gray-600">Temperature: ${agent.temperature}</p>
                    <p class="text-sm text-gray-600">Session: ${agent.whatsapp_session}</p>
                </div>
                
                <div>
                    <h4 class="font-medium text-gray-700">Triggers (${agent.triggers.length})</h4>
                    <div class="flex flex-wrap gap-2 mt-2">
                        ${agent.triggers.map(t => `
                            <span class="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">${t}</span>
                        `).join('')}
                    </div>
                </div>
                
                <div>
                    <h4 class="font-medium text-gray-700">Instructions</h4>
                    <pre class="text-sm bg-gray-100 p-3 rounded mt-2 whitespace-pre-wrap">${agent.root_instruction || 'No instructions'}</pre>
                </div>
                
                <div class="flex gap-2 pt-4">
                    <button onclick="viewAgentLogs('${id}')" class="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600">
                        <i class="fas fa-file-alt mr-2"></i>View Logs
                    </button>
                    <button onclick="editAgent('${id}')" class="bg-gray-500 text-white px-4 py-2 rounded-lg hover:bg-gray-600">
                        <i class="fas fa-edit mr-2"></i>Edit
                    </button>
                </div>
            </div>
        `;
        
        document.getElementById('agent-modal').classList.remove('hidden');
    } catch (error) {
        console.error('Failed to load agent details:', error);
    }
}

// Close modal
function closeModal() {
    document.getElementById('agent-modal').classList.add('hidden');
}

// View agent logs
async function viewAgentLogs(id) {
    closeModal();
    
    // Switch to logs tab
    document.querySelector('[data-tab="logs"]').click();
    
    // Select agent and fetch logs
    document.getElementById('log-agent-select').value = id;
    fetchLogs();
}

// Fetch logs
async function fetchLogs() {
    const agentId = document.getElementById('log-agent-select').value;
    if (!agentId) return;
    
    try {
        const result = await api.getAgentLogs(agentId);
        const viewer = document.getElementById('log-viewer');
        
        if (result.logs && result.logs.length > 0) {
            viewer.innerHTML = result.logs.map(line => 
                `<div class="whitespace-pre-wrap">${escapeHtml(line)}</div>`
            ).join('');
        } else {
            viewer.innerHTML = '<p class="text-gray-500">No logs available</p>';
        }
        
        // Scroll to bottom
        viewer.scrollTop = viewer.scrollHeight;
    } catch (error) {
        console.error('Failed to fetch logs:', error);
    }
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Refresh agents
function refreshAgents() {
    loadAgents();
}

// Edit agent
async function editAgent(id) {
    try {
        const agent = await api.fetchAgent(id);
        currentAgent = agent;
        
        // Fill form
        document.querySelector('[name="name"]').value = agent.name;
        document.querySelector('[name="description"]').value = agent.description || '';
        document.querySelector('[name="model"]').value = agent.model;
        document.querySelector('[name="temperature"]').value = agent.temperature;
        document.querySelector('[name="root_instruction"]').value = agent.root_instruction || '';
        
        updateTemperatureValue(document.querySelector('[name="temperature"]'));
        
        // Set session value after sessions are loaded
        setTimeout(() => {
            document.querySelector('[name="whatsapp_session"]').value = agent.whatsapp_session;
        }, 200);
        
        // Clear and set selections
        selectedTriggers.clear();
        selectedTools.waha.clear();
        selectedTools.builtin.clear();
        
        agent.triggers.forEach(t => selectedTriggers.add(t));
        agent.waha_tools?.forEach(t => selectedTools.waha.add(t));
        agent.builtin_tools?.forEach(t => selectedTools.builtin.add(t));
        
        // Switch to create tab
        document.querySelector('[data-tab="create"]').click();
        
        // Reload form elements
        await loadTriggers();
        await loadToolsForForm();
        await loadSessions();
        
        // Check selected items
        selectedTriggers.forEach(t => {
            const el = document.getElementById(`trigger-${t}`);
            if (el) el.checked = true;
            addTriggerInstructionField(t);
            const instructionEl = document.getElementById(`trigger-instruction-${t}`);
            if (instructionEl && agent.trigger_instructions[t]) {
                instructionEl.value = agent.trigger_instructions[t];
            }
        });
        
        selectedTools.waha.forEach(t => {
            const el = document.getElementById(`waha-${t}`);
            if (el) el.checked = true;
        });
        
        selectedTools.builtin.forEach(t => {
            const el = document.getElementById(`builtin-${t}`);
            if (el) el.checked = true;
        });
        
        closeModal();
    } catch (error) {
        console.error('Failed to edit agent:', error);
    }
}

// Load WhatsApp sessions
async function loadSessions() {
    try {
        const sessions = await api.fetchSessions();
        const select = document.getElementById('whatsapp-session-select');
        
        if (sessions && sessions.length > 0) {
            select.innerHTML = sessions.map(session => 
                `<option value="${session.name}" ${session.status === 'WORKING' ? 'selected' : ''}>
                    ${session.name} (${session.status})
                </option>`
            ).join('');
        } else {
            select.innerHTML = '<option value="default">default</option>';
        }
    } catch (error) {
        console.error('Failed to load sessions:', error);
        // Fallback to default
        document.getElementById('whatsapp-session-select').innerHTML = '<option value="default">default</option>';
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Load initial data
    loadAgents();
    loadTriggers();
    loadToolsForForm();
    loadSessions();
    
    // Populate log agent select
    try {
        const agents = await api.fetchAgents();
        const select = document.getElementById('log-agent-select');
        select.innerHTML = '<option value="">Select an agent...</option>' + 
            agents.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
    } catch (error) {
        console.error('Failed to load agents for logs:', error);
    }
    
    // Auto-refresh agents every 30 seconds
    setInterval(loadAgents, 30000);
});