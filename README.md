# vpn-proxy

A single Docker container combining [gluetun](https://github.com/qdm12/gluetun) (NordVPN/WireGuard) with a FastAPI HTTP service that routes requests through the VPN and auto-rotates countries when blocked.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | VPN tunnel status and current IP |
| `POST` | `/switch` | Manually rotate to a different VPN country |
| `POST` | `/request` | Make an HTTP request through the VPN with auto-rotation on block |
| `ANY` | `/proxy/{url}` | Transparent proxy — forward any request directly through the VPN |

## Configuration

Only `WIREGUARD_PRIVATE_KEY` is required — set it in a `.env` file. All other values are pre-configured in `docker-compose.yml`.

| Variable | Default | Description |
|----------|---------|-------------|
| `WIREGUARD_PRIVATE_KEY` | **required** | WireGuard private key (NordLynx) — set in `.env` |
| `VPN_SERVICE_PROVIDER` | `nordvpn` | VPN provider |
| `VPN_TYPE` | `wireguard` | `wireguard` or `openvpn` |
| `SERVER_COUNTRIES` | `Austria,Belgium,Croatia,Denmark,France,Germany,Italy,Netherlands,Spain,Sweden` | Comma-separated list of countries to rotate through |
| `VPN_MAX_RETRIES` | `3` | Number of country switches before giving up |
| `HTTP_CONTROL_SERVER_AUTH_DEFAULT_ROLE` | `{"auth":"none"}` | Allows internal API access without authentication |

## Usage

```bash
# Start
docker-compose up -d

# Health check
curl http://localhost:9090/health

# Make a request through VPN (auto-rotates on 403/429/503)
curl -X POST http://localhost:9090/request \
  -H "Content-Type: application/json" \
  -d '{"url": "https://httpbin.org/ip"}'

# Transparent proxy
curl "http://localhost:9090/proxy/https://httpbin.org/ip"

# Manual country switch
curl -X POST http://localhost:9090/switch
```

## Getting a NordVPN WireGuard key

```bash
curl -s -u token:<your-access-token> \
  https://api.nordvpn.com/v1/users/services/credentials \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['nordlynx_private_key'])"
```

Get your access token at [my.nordvpn.com](https://my.nordvpn.com/) → Account dashboard → Access token.

## Build

```bash
docker-compose build
docker-compose up -d
```
