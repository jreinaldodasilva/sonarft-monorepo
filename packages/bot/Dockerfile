FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .

COPY . .

RUN adduser --disabled-password --gecos '' --uid 1000 sonarft \
    && chown -R sonarft:sonarft /app
USER sonarft

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "print('ok')" || exit 1

CMD ["python", "-m", "sonarft_bot"]
