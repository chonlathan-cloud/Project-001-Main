FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY contracts ./contracts

RUN groupadd --system --gid 10001 mcp \
    && useradd --system --uid 10001 --gid mcp --no-create-home mcp

USER mcp

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.server.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
