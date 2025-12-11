FROM python:3.10-slim

WORKDIR /app

# Install build dependencies for some python packages if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Expose the API port
EXPOSE 8123

# Entrypoint runs fetch, ingest, then server
ENTRYPOINT ["/app/entrypoint.sh"]

