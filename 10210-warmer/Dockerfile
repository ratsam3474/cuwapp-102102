FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*

# Copy main API requirements (warmer uses same dependencies)
COPY ../10210-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy warmer service files
COPY . .
# Copy shared modules from main API
COPY ../10210-api/database ./database
COPY ../10210-api/waha_functions.py .
COPY ../10210-api/warmer ./warmer

# Expose warmer port
EXPOSE 8001

# Run warmer service
CMD ["gunicorn", "main:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8001", "--timeout", "600"]