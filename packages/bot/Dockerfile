FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .

COPY . .

# Create runtime data directories so they exist even without a volume mount.
# These directories hold trade history, bot registry, and backups — they
# must be on a persistent volume in production to survive container replacement.
RUN mkdir -p sonarftdata/history sonarftdata/bots sonarftdata/backups sonarftdata/config

RUN adduser --disabled-password --gecos '' --uid 1000 sonarft \
    && chown -R sonarft:sonarft /app
USER sonarft

# Declare runtime data directories as volume mount points.
# Mount these on a named Docker volume or host path in production:
#   docker run -v sonarft-history:/app/sonarftdata/history \
#              -v sonarft-bots:/app/sonarftdata/bots \
#              -v sonarft-backups:/app/sonarftdata/backups ...
# See infra/docker-compose.yml for the production volume configuration.
VOLUME ["/app/sonarftdata/history", "/app/sonarftdata/bots", "/app/sonarftdata/backups"]

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import sonarft_bot; print('ok')" || exit 1

CMD ["python", "-m", "sonarft_bot"]
