FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements file first
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Set the entrypoint or default command
CMD ["python", "cpu_usage_logger.py"]