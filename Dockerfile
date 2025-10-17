FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-api.txt \
    && python -m spacy download en_core_web_sm

COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
