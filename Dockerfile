# Use a lightweight Python image
FROM python:3.12-slim

# Create a non-root user for security
RUN groupadd -r botuser && useradd -r -g botuser botuser

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY TSDMD.py .

# Create required directories with correct permissions
RUN mkdir -p /app/sessions /app/Media && \
    chown -R botuser:botuser /app

USER botuser

CMD ["python", "-u", "TSDMD.py"]