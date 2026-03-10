FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y     build-essential     libpq-dev     curl     && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser (Chromium)
# NOTE: This increases image size but is required for scraper/publisher.
RUN python -m playwright install --with-deps chromium

# Copy app code
COPY . .

# Expose backend port
EXPOSE 5050

# Start app
CMD ["python", "run.py"]
