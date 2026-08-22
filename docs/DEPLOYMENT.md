# Deployment

## Local Docker Compose

Copy `.env.example` to `.env`, replace `SESSION_SECRET` and `ADMIN_PASSWORD`, then run:

```bash
docker compose up -d --build
curl http://localhost:8080/ready
```

The API process intentionally owns the Game Engine and Agent Gateway in one process for the single-table MVP. `broadcast-worker` moves due durable events to the Redis public stream; PostgreSQL and Redis are started as the production service dependencies. Persistent volumes survive container replacement.

## Quick Tunnel (development)

```bash
cloudflared tunnel --url http://localhost:8080
```

Put the resulting HTTPS origin into `PUBLIC_API_URL`; convert `https://` to `wss://` for `PUBLIC_WS_URL`. Quick Tunnel URLs change and are not suitable for a scheduled live broadcast.

## Named Tunnel

```bash
cloudflared tunnel login
cloudflared tunnel create agent-landlord
cloudflared tunnel route dns agent-landlord api.agentlandlord.example.com
cloudflared tunnel run agent-landlord
```

Create `%USERPROFILE%/.cloudflared/config.yml` (Windows) or `~/.cloudflared/config.yml`:

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /absolute/path/YOUR_TUNNEL_ID.json
ingress:
  - hostname: api.agentlandlord.example.com
    service: http://localhost:8080
  - service: http_status:404
```

Cloudflare supports WebSocket proxying on the same origin. Protect `/admin` (or a dedicated admin hostname) with Cloudflare Access; the application password remains defense in depth.

## Cloudflare Pages

Create a Pages project rooted at `apps/web`, use build command `npm ci && npm run build`, output directory `dist`, and set `VITE_API_URL=https://api...` plus `VITE_WS_URL=wss://api...`. The Vite SPA fallback serves `/table`, `/queue`, `/hall`, `/join`, `/admin`, and `/demo` as independent routes.

GitHub and Cloudflare credentials are deliberately absent. The final `tunnel login`, Pages project connection, and release publication require the operator's account authorization.

