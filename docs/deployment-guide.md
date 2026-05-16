# Deployment Guide

This guide covers Docker Compose deployment for both development and production, environment configuration, scaling, monitoring, and security hardening.

---

## Docker Architecture

The production stack runs three containers:

```
┌─────────────────────────────────────────────────────────────┐
│  external network                                           │
│  ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │   web (:3000)    │    │       api (:8000)            │  │
│  │   nginx + React  │    │   FastAPI + uvicorn          │  │
│  └──────────────────┘    └──────────────┬───────────────┘  │
└─────────────────────────────────────────┼───────────────────┘
                                          │ internal network
                              ┌───────────▼───────────┐
                              │   bot (no ports)      │
                              │   Trading engine      │
                              └───────────────────────┘
                                          │
                              ┌───────────▼───────────┐
                              │   bot-data (volume)   │
                              │   sonarftdata/        │
                              └───────────────────────┘
```

The `bot` container has no exposed ports — it is only accessible from the `api` container on the internal network. The `bot-data` named volume is shared between `bot` and `api` so both can read/write trade history and configuration.

---

## Development Deployment

### Start with hot reload

```bash
make dev
# equivalent to:
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up
```

The dev override (`infra/docker-compose.dev.yml`) mounts source directories as volumes and enables hot reload:

- API: `uvicorn --reload` watches `packages/api/src/`
- Web: `vite --host` watches `packages/web/src/`

Changes to Python or TypeScript source files are reflected immediately without rebuilding images.

### Rebuild after dependency changes

```bash
make build
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up
```

Rebuild is required when `requirements.txt` or `package.json` changes.

---

## Production Deployment

### Step 1: Configure environment

```bash
# API configuration
cp packages/api/.env.example packages/api/.env
```

Edit `packages/api/.env`:

```env
# Choose one auth method:
NETLIFY_SITE_URL=https://your-site.netlify.app
# or:
# SONARFT_API_TOKEN=your-long-random-secret-token

# Set your frontend origin
CORS_ORIGINS=https://your-frontend.com

# Bot limits
MAX_BOTS_PER_CLIENT=5

# Data directory (inside container)
DATA_DIR=/app/sonarftdata

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/sonarft.log
```

For live trading, set exchange API keys as environment variables (not in `.env` — use your deployment platform's secrets management):

```bash
export OKX_API_KEY=your-key
export OKX_SECRET=your-secret
export OKX_PASSWORD=your-passphrase
export BINANCE_API_KEY=your-key
export BINANCE_SECRET=your-secret
export SONARFT_ALLOW_LIVE=true
```

### Step 2: Build images

```bash
make build
# equivalent to:
docker-compose -f infra/docker-compose.yml build
```

### Step 3: Start services

```bash
docker-compose -f infra/docker-compose.yml up -d
```

### Step 4: Verify health

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok","version":"1.0.0"}

docker-compose -f infra/docker-compose.yml ps
# All services should show "Up (healthy)"
```

---

## Docker Compose Reference

### `infra/docker-compose.yml` (Production)

```yaml
services:
  bot:
    build: ./packages/bot
    volumes:
      - bot-data:/app/sonarftdata
    networks: [internal]
    restart: unless-stopped

  api:
    build: ./packages/api
    ports: ["8000:8000"]
    volumes:
      - bot-data:/app/sonarftdata
    environment:
      - NETLIFY_SITE_URL
      - SONARFT_API_TOKEN
      - CORS_ORIGINS
      - MAX_BOTS_PER_CLIENT
      - DATA_DIR=/app/sonarftdata
    depends_on: [bot]
    networks: [internal, external]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  web:
    build:
      context: ./packages/web
      args:
        - VITE_API_URL
        - VITE_WS_URL
    ports: ["3000:80"]
    depends_on: [api]
    networks: [external]
    restart: unless-stopped

volumes:
  bot-data:

networks:
  internal:
  external:
```

### `infra/docker-compose.dev.yml` (Development overrides)

```yaml
services:
  api:
    volumes:
      - ./packages/api/src:/app/src
      - ./packages/bot:/app/bot
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

  web:
    ports: ["5173:5173"]
    volumes:
      - ./packages/web/src:/app/src
    command: npm run dev -- --host
```

---

## Reverse Proxy with TLS

For production, place a reverse proxy (nginx or Traefik) in front of the API and web containers.

### nginx Example

```nginx
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;  # keep WebSocket connections alive
    }
}
```

### Traefik Example

Add labels to the `api` service in `docker-compose.yml`:

```yaml
api:
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.api.rule=Host(`api.your-domain.com`)"
    - "traefik.http.routers.api.tls.certresolver=letsencrypt"
    - "traefik.http.services.api.loadbalancer.server.port=8000"
```

---

## Persistent Volumes

The `bot-data` named volume persists:

```
/app/sonarftdata/
├── config/           # per-client parameters and indicators
├── bots/             # bot registry files
├── history/          # trade and order history JSON + SQLite
└── backups/          # SQLite database backups
```

**Backup strategy:**

The bot automatically backs up the SQLite database daily to `sonarftdata/backups/sonarft_backup_{YYYYMMDD}.db`. Configure the backup directory to be outside the primary data volume:

```bash
export SONARFT_BACKUP_DIR=/mnt/backup/sonarft
```

For the JSON history files, use a volume backup tool or mount the volume to a backup container:

```bash
# Manual backup
docker run --rm \
    -v sonarft_bot-data:/data \
    -v /backup:/backup \
    alpine tar czf /backup/sonarft-data-$(date +%Y%m%d).tar.gz /data
```

---

## Scaling Multiple Bots

Multiple bot instances are managed within a single `api` container via `BotManager`. The `MAX_BOTS_PER_CLIENT` environment variable controls the per-client limit (default: 5).

To support more concurrent bots, increase `MAX_BOTS_PER_CLIENT` and ensure the host has sufficient CPU and memory. Each bot runs as an asyncio task — they share the event loop and do not require separate processes.

For multi-tenant deployments with many clients, consider:

1. Increasing `MAX_BOTS_PER_CLIENT` per deployment
2. Running multiple API instances behind a load balancer (note: `TicketStore` is in-memory and not shared across instances — use sticky sessions or a shared Redis store for WebSocket tickets)
3. Separating the `bot-data` volume per tenant

---

## Logging

### Log Files

| File | Content | Rotation |
|---|---|---|
| `logs/sonarft.log` | Human-readable application log | 10 MB, 7 backups |
| `logs/sonarft.jsonl` | Structured JSON log (optional) | 10 MB, 7 backups |
| `logs/sonarft_metrics.jsonl` | Raw metrics JSON lines | 50 MB, 14 backups |

Enable structured JSON logging:
```env
JSON_LOG_FILE=logs/sonarft.jsonl
```

### Viewing Logs

```bash
# Docker Compose logs (all services)
make logs

# Specific service
docker-compose -f infra/docker-compose.yml logs -f api

# Application log file
docker exec sonarft-api-1 tail -f /app/logs/sonarft.log

# Metrics stream
docker exec sonarft-api-1 tail -f /app/logs/sonarft_metrics.jsonl | jq .
```

### Log Aggregation

The structured JSON log (`sonarft.jsonl`) is compatible with:

- **Loki + Grafana:** Use the Loki Docker driver or a Promtail agent
- **CloudWatch:** Use the `awslogs` Docker log driver
- **Datadog:** Use the Datadog Agent with Docker log collection

---

## Monitoring

### Health Check

The API exposes a health endpoint used by Docker Compose and load balancers:

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok","version":"1.0.0"}
```

### Metrics

The metrics log (`sonarft_metrics.jsonl`) contains JSON lines for each trade, order, and cycle. Parse with `jq` for quick analysis:

```bash
# Count trades per bot
cat logs/sonarft_metrics.jsonl | jq -r 'select(.event=="trade") | .botid' | sort | uniq -c

# Average profit per trade
cat logs/sonarft_metrics.jsonl | jq -r 'select(.event=="trade") | .profit' | awk '{sum+=$1; n++} END {print sum/n}'
```

### Circuit Breaker Alerts

Configure `SONARFT_ALERT_WEBHOOK` to receive alerts when the circuit breaker trips:

```bash
# Slack incoming webhook
export SONARFT_ALERT_WEBHOOK=https://hooks.slack.com/services/T.../B.../...

# Discord webhook
export SONARFT_ALERT_WEBHOOK=https://discord.com/api/webhooks/...
```

The alert payload:
```json
{ "text": "SonarFT Bot abc123: circuit breaker tripped after 5 consecutive failures. Last error: ..." }
```

---

## Security Hardening

### API Security

1. **Always set auth in production.** Set either `NETLIFY_SITE_URL` or `SONARFT_API_TOKEN`. The API logs a warning at startup if auth is disabled.

2. **Use HTTPS.** Never expose the API over plain HTTP in production. Use a reverse proxy with TLS termination.

3. **Restrict CORS origins.** Set `CORS_ORIGINS` to your exact frontend domain:
   ```env
   CORS_ORIGINS=https://your-frontend.com
   ```

4. **Rate limiting.** The API includes slowapi rate limiting. Tune limits for your expected traffic.

5. **Security headers.** The `SecurityHeadersMiddleware` adds:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `Content-Security-Policy: default-src 'none'`
   - `Cache-Control: no-store, no-cache, must-revalidate`

### Live Trading Security

1. **Never set `SONARFT_ALLOW_LIVE=true` in development.** Use simulation mode for all development and testing.

2. **Store exchange API keys as secrets.** Use your deployment platform's secrets management (AWS Secrets Manager, Docker secrets, Kubernetes secrets) — never commit API keys to source control.

3. **Use read-only API keys where possible.** For monitoring-only bots, use exchange API keys with read-only permissions.

4. **Set `max_daily_loss` and `max_trade_amount`.** These limits prevent runaway losses from bugs or market anomalies.

5. **Monitor the circuit breaker.** Configure `SONARFT_ALERT_WEBHOOK` so you are notified immediately if a bot stops due to repeated failures.

### Container Security

1. **Run containers as non-root.** The Dockerfiles should use a non-root user. Verify with:
   ```bash
   docker exec sonarft-api-1 whoami
   ```

2. **Use read-only filesystems where possible.** Mount only the `sonarftdata` volume as writable; the rest of the container filesystem can be read-only.

3. **Scan images for vulnerabilities.** Run `docker scout` or `trivy` on built images before deployment:
   ```bash
   trivy image sonarft-api:latest
   ```

4. **Keep dependencies updated.** The CI pipeline runs `pip-audit` and `npm audit` on every push. Address High and Critical CVEs promptly.
