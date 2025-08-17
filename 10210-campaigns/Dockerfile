FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*

# Copy main API requirements
COPY ../10210-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy campaign service files
COPY . .
# Copy shared modules from main API
COPY ../10210-api/database ./database
COPY ../10210-api/waha_functions.py .
COPY ../10210-api/jobs ./jobs
COPY ../10210-api/utils ./utils

# Expose campaigns port
EXPOSE 8002

# Run campaigns service
CMD ["gunicorn", "main:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8002", "--timeout", "300"]