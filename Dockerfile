FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install system dependencies (wajib untuk pandas + openpyxl)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Vercel exposes $PORT automatically → gunakan itu
ENV PORT=8000

EXPOSE 8000

# Jalankan Streamlit dengan alamat yang benar
CMD streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT
