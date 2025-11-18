# Use official Python image as base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy dependency file first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Run the app with uvicorn
CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8080"]
