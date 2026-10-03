FROM python:3.11-slim

WORKDIR /app

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run the app on the assigned PORT
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}