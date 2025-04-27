# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /code

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Default command (handled in docker-compose)
