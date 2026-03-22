# 빌드: docker compose build
# - PyTorch 는 CPU 인덱스에서만 설치 (CUDA + nvidia-* 휠 제외 → 용량·시간 대폭 감소)
# - RUN --mount 는 BuildKit 전용이라 GCP Cloud Build 등에서 BuildKit 미사용 시 실패할 수 있어 일반 RUN 사용

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    graphviz \
    libgraphviz-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 1) CPU 전용 torch 선설치
RUN pip install --no-cache-dir torch==2.8.0 \
    --index-url https://download.pytorch.org/whl/cpu

# 2) 나머지 의존성 — torch 는 위에서 이미 만족되면 재설치하지 않음
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

# Cloud Run 은 PORT(기본 8080)에서 수신해야 함. 로컬: docker run -e PORT=8000 -p 8000:8000 ...
ENV PORT=8080
EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
