FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm
RUN python -c "from fastembed import TextEmbedding; list(TextEmbedding(model_name='BAAI/bge-small-en-v1.5').embed(['warmup']))"
RUN python -c "from fastembed.rerank.cross_encoder import TextCrossEncoder; list(TextCrossEncoder(model_name='Xenova/ms-marco-MiniLM-L-6-v2').rerank('warmup', ['warmup document']))"

COPY app ./app
COPY import_kg.py .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]