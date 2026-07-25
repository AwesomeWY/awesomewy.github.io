# 한눈·주식 백엔드 — 어디서나 실행 가능한 컨테이너 (Render / Railway / Fly.io / 자체서버)
FROM python:3.11-slim

# ta/pandas 빌드 대비 최소 빌드 도구
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# PaaS는 $PORT 를 주입한다(없으면 8000).
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
