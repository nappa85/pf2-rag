FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir torch==2.13.0+rocm7.2 --index-url https://download.pytorch.org/whl/rocm7.2

RUN pip install --no-cache-dir \
    PyMuPDF \
    marker-pdf \
    requests \
    sentence-transformers \
    faiss-cpu \
    rank_bm25 \
    tqdm \
    numpy

WORKDIR /app

COPY rag/ /app/rag/

CMD ["bash"]
