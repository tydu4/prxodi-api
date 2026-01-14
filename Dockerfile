FROM public.ecr.aws/docker/library/python:3.11-slim

# Set working directory
WORKDIR /app

# Set env variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files to disc
# PYTHONUNBUFFERED: Prevents Python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (needed for pgvector/asyncpg usually not much, but good practice)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (just for documentation, compose handles mapping)
EXPOSE 8000

# Run the application
# Host 0.0.0.0 is crucial for Docker containers
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
