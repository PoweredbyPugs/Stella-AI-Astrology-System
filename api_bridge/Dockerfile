FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STELLA_API_HOST=0.0.0.0 \
    STELLA_API_PORT=3010 \
    STELLA_MCP_PYTHON=/usr/local/bin/python \
    STELLA_MCP_SERVER=/app/stella/stella_server.py

WORKDIR /app/stella

COPY requirements.txt /tmp/stella-requirements.txt
COPY api_bridge/requirements.txt /tmp/bridge-requirements.txt
RUN apt-get update \
    && apt-get install --no-install-recommends --yes build-essential \
    && pip install --no-cache-dir \
      -r /tmp/stella-requirements.txt \
      -r /tmp/bridge-requirements.txt \
    && apt-get purge --auto-remove --yes build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 stella

# Build from the Stella directory. Copy only code and public reference data;
# charts/, memories, credentials, local venvs, and other runtime state are excluded.
COPY *.py ./
COPY graph/*.py ./graph/
COPY zodiac_data.json planets_data.json houses_data.json aspects_data.json ./
COPY traditional_astrology_data.json hexagrams.json tao_te_ching.json ./
COPY data/777-correspondences.json ./data/777-correspondences.json
COPY api_bridge/app.py ./api_bridge/app.py

RUN mkdir -p charts/memory autopoietic/sessions \
    && chown -R stella:stella /app/stella
USER stella

EXPOSE 3010
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3010/health', timeout=2)" || exit 1

WORKDIR /app/stella/api_bridge
CMD ["python", "app.py"]
