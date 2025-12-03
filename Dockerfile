FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua source code
COPY . .

# Vercel akan forward trafik ke port 8000 (konvensi umum)
ENV PORT=8000

# Jalankan streamlit pada 0.0.0.0 dan port dari $PORT
CMD ["sh", "-c", "streamlit run app.py --server.port $PORT --server.address 0.0.0.0"]
