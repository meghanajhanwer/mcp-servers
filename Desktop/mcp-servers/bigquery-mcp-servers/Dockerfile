FROM python:3.12-slim

WORKDIR /app

# Install deps first for better build caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

ENV PORT=8080
EXPOSE 8080

# FastAPI entrypoint (we'll create src/main.py later)
CMD ["python", "-m", "uvicorn", "src.main:app", "--host=0.0.0.0", "--port=8080"]