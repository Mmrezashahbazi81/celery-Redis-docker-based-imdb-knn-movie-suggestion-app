FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

    
COPY requirements.txt .

# به خط پایینی --no-cache-dir رو اضافه کن واسه پروداکشن
RUN pip install  --default-timeout=1000 -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY app/ .

EXPOSE 5000
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]
