-- WhatsApp Agent Database Schema
-- SQLite database schema for campaign management and message tracking

-- Enable foreign keys in SQLite
PRAGMA foreign_keys = ON;

-- Campaigns table: Main campaign management
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Basic information
    name VARCHAR(255) NOT NULL,
    session_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'created',  -- created, running, paused, completed, failed
    
    -- File information
    file_path VARCHAR(500),
    column_mapping TEXT,                        -- JSON string for column mapping
    start_row INTEGER DEFAULT 1,
    end_row INTEGER,
    
    -- Message configuration with samples
    message_mode VARCHAR(20) DEFAULT 'single',  -- 'single' or 'multiple'
    message_samples TEXT,                       -- JSON array of message samples
    use_csv_samples BOOLEAN DEFAULT FALSE,
    
    -- Processing configuration
    delay_seconds INTEGER DEFAULT 5,
    retry_attempts INTEGER DEFAULT 3,
    max_daily_messages INTEGER DEFAULT 1000,
    
    -- Condition filters
    exclude_my_contacts BOOLEAN DEFAULT 0,
    exclude_previous_conversations BOOLEAN DEFAULT 0,
    
    -- Progress tracking
    total_rows INTEGER DEFAULT 0,
    processed_rows INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    error_details TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Deliveries table: Individual message delivery tracking
CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Foreign key and row reference
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    
    -- Contact information
    phone_number VARCHAR(20) NOT NULL,
    recipient_name VARCHAR(255),
    
    -- Sample selection tracking
    selected_sample_index INTEGER,
    selected_sample_text TEXT,
    final_message_content TEXT,
    
    -- Variable data (JSON)
    variable_data TEXT,
    
    -- Delivery status and tracking
    status VARCHAR(50) DEFAULT 'pending',  -- pending, sending, sent, delivered, failed
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    error_message TEXT,
    whatsapp_message_id VARCHAR(255),
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Campaign analytics table: Performance tracking per sample
CREATE TABLE IF NOT EXISTS campaign_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Foreign key
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    
    -- Sample tracking
    sample_index INTEGER,
    sample_text TEXT,
    
    -- Usage statistics
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    delivery_count INTEGER DEFAULT 0,
    response_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    
    -- Performance metrics
    avg_delivery_time REAL,           -- Average delivery time in seconds
    response_rate REAL,               -- Response rate percentage
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_campaigns_name ON campaigns(name);
CREATE INDEX IF NOT EXISTS idx_campaigns_session ON campaigns(session_name);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_created ON campaigns(created_at);

CREATE INDEX IF NOT EXISTS idx_deliveries_campaign ON deliveries(campaign_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_phone ON deliveries(phone_number);
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries(status);
CREATE INDEX IF NOT EXISTS idx_deliveries_sent ON deliveries(sent_at);

CREATE INDEX IF NOT EXISTS idx_analytics_campaign ON campaign_analytics(campaign_id);
CREATE INDEX IF NOT EXISTS idx_analytics_sample ON campaign_analytics(sample_index);

-- Create triggers to update timestamps automatically
CREATE TRIGGER IF NOT EXISTS update_campaigns_timestamp 
AFTER UPDATE ON campaigns
BEGIN
    UPDATE campaigns SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_deliveries_timestamp 
AFTER UPDATE ON deliveries
BEGIN
    UPDATE deliveries SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_analytics_timestamp 
AFTER UPDATE ON campaign_analytics
BEGIN
    UPDATE campaign_analytics SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Create views for common queries
CREATE VIEW IF NOT EXISTS campaign_summary AS
SELECT 
    c.id,
    c.name,
    c.session_name,
    c.status,
    c.total_rows,
    c.processed_rows,
    c.success_count,
    c.error_count,
    ROUND((CAST(c.processed_rows AS REAL) / CAST(c.total_rows AS REAL)) * 100, 2) as progress_percentage,
    CASE 
        WHEN c.processed_rows > 0 THEN ROUND((CAST(c.success_count AS REAL) / CAST(c.processed_rows AS REAL)) * 100, 2)
        ELSE 0 
    END as success_rate,
    c.created_at,
    c.started_at,
    c.completed_at
FROM campaigns c;

CREATE VIEW IF NOT EXISTS delivery_summary AS
SELECT 
    d.campaign_id,
    COUNT(*) as total_deliveries,
    COUNT(CASE WHEN d.status = 'sent' THEN 1 END) as sent_count,
    COUNT(CASE WHEN d.status = 'delivered' THEN 1 END) as delivered_count,
    COUNT(CASE WHEN d.status = 'failed' THEN 1 END) as failed_count,
    AVG(CASE WHEN d.sent_at IS NOT NULL AND d.created_at IS NOT NULL 
        THEN (julianday(d.sent_at) - julianday(d.created_at)) * 86400 END) as avg_processing_time
FROM deliveries d
GROUP BY d.campaign_id;

-- WhatsApp Warmer tables
CREATE TABLE IF NOT EXISTS warmer_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    orchestrator_session VARCHAR(100) NOT NULL,
    participant_sessions TEXT NOT NULL,  -- JSON array of session names
    status VARCHAR(50) DEFAULT 'inactive',  -- inactive, warming, paused, stopped
    
    -- Configuration
    group_message_delay_min INTEGER DEFAULT 30,  -- seconds
    group_message_delay_max INTEGER DEFAULT 1800,  -- 30 minutes
    direct_message_delay_min INTEGER DEFAULT 120,  -- 2 minutes
    direct_message_delay_max INTEGER DEFAULT 1800,  -- 30 minutes
    
    -- Statistics
    total_groups_created INTEGER DEFAULT 0,
    total_messages_sent INTEGER DEFAULT 0,
    total_group_messages INTEGER DEFAULT 0,
    total_direct_messages INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    stopped_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS warmer_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warmer_session_id INTEGER NOT NULL REFERENCES warmer_sessions(id) ON DELETE CASCADE,
    group_id VARCHAR(255) NOT NULL,  -- WhatsApp group ID
    group_name VARCHAR(255),
    members TEXT NOT NULL,  -- JSON array of member phone numbers
    
    -- Activity tracking
    last_message_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    last_speaker VARCHAR(100),
    
    -- Status
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS warmer_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warmer_session_id INTEGER NOT NULL REFERENCES warmer_sessions(id) ON DELETE CASCADE,
    
    -- Message details
    message_id VARCHAR(255),
    sender_session VARCHAR(100) NOT NULL,
    recipient_session VARCHAR(100),  -- NULL for group messages
    group_id VARCHAR(255),  -- NULL for direct messages
    message_type VARCHAR(20) NOT NULL,  -- group, direct
    
    -- Content
    message_content TEXT NOT NULL,
    context_summary TEXT,  -- Previous conversation context for LLM
    
    -- Timestamps
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_warmer_conversations_session (warmer_session_id),
    INDEX idx_warmer_conversations_type (message_type),
    INDEX idx_warmer_conversations_sent (sent_at)
);

CREATE TABLE IF NOT EXISTS warmer_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warmer_session_id INTEGER NOT NULL REFERENCES warmer_sessions(id) ON DELETE CASCADE,
    session_name VARCHAR(100) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    contact_name VARCHAR(255),
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(warmer_session_id, session_name, contact_phone)
);

-- Indexes for warmer tables
CREATE INDEX IF NOT EXISTS idx_warmer_sessions_status ON warmer_sessions(status);
CREATE INDEX IF NOT EXISTS idx_warmer_groups_session ON warmer_groups(warmer_session_id);
CREATE INDEX IF NOT EXISTS idx_warmer_groups_active ON warmer_groups(is_active);
CREATE INDEX IF NOT EXISTS idx_warmer_contacts_session ON warmer_contacts(warmer_session_id);

-- Sample data for testing (optional)
-- INSERT INTO campaigns (name, session_name, message_mode, message_samples) VALUES 
-- ('Test Campaign', 'default', 'multiple', '["Hi {name}! Welcome to our service.", "Hello {name}! Thanks for joining us.", "Hey {name}! Great to have you with us."]');
