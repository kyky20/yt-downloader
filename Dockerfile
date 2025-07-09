FROM python:3.10-slim

# Install ffmpeg and other dependencies
RUN apt update && apt install -y ffmpeg git && apt clean

# Set working directory
WORKDIR /app

# Copy files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Set env vars
ENV PORT=8080

# Start app
CMD ["python", "app.py"]
