# Use an official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies required to build some Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy the code
COPY . .

# Set environment variables from .env manually
ENV PYTHONUNBUFFERED=1

WORKDIR /app/src

# Default command to run the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]