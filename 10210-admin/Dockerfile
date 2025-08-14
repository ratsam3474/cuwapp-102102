# Admin Dashboard Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY admin_requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r admin_requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8001

# Start the application
CMD ["uvicorn", "admin_dashboard:app", "--host", "0.0.0.0", "--port", "8001"]