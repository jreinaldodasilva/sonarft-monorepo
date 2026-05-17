# Frontend Guide

The web frontend (`packages/web`) is a React 18 + TypeScript 5 + Vite 8 application. It communicates exclusively with `packages/api` over REST and WebSocket.

---

## Project Structure

```
packages/web/src/
├── components/         # Reusable UI components
├── hooks/              # Custom React hooks
│   ├── AuthProvider.tsx        # Netlify Identity auth context
│   ├── useBots.ts              # Bot state machine + WebSocket + REST
│   ├── useConfigCheckboxes.ts  # Config panel checkbox state
│   ├── useIdleTimeout.ts       # Session idle timeout
│   └── useWebSocket.tsx        # WebSocket connection lifecycle
├── integration/        # API client functions (REST calls)
├── pages/              # Page-level components
├── utils/              # Utility functions and constants
│   ├── api.ts          # REST API call functions
│   ├── constants.ts    # API URLs, timeouts
│   └── helpers.ts      # Shared helper functions
├── mocks/              # MSW v2 mock handlers for tests
└── App.tsx             # Root component, routing
```

---

## Authentication

`AuthProvider` wraps the application and provides the auth context. It manages a simple token stored in `sessionStorage` and exposes the current user, session state, and login/logout handlers:

```typescript
// AuthProvider.tsx
export interface AuthContextValue {
    user: AppUser | null;
    sessionExpired: boolean;
    handleLogin: () => void;
    handleLogout: () => void;
}

export const AuthContext = createContext<AuthContextValue>({
    user: null,
    sessionExpired: false,
    handleLogin: () => {},
    handleLogout: () => {},
});
```

On mount, `AuthProvider` auto-injects a `DEFAULT_USER` (configured via `VITE_DEFAULT_USER_ID` / `VITE_DEFAULT_USER_EMAIL` env vars, defaulting to `dev_user` / `user@sonarft.local`). The full trading interface is available immediately without any external auth setup.

The API layer uses Bearer tokens stored in `sessionStorage` under `sonarft_token`. The API server validates these via Netlify Identity JWT (when `NETLIFY_SITE_URL` is set) or a static token (`SONARFT_API_TOKEN`). The frontend is auth-provider-agnostic — it only reads/writes the token from `sessionStorage`.

A 401 response from any API call triggers the registered unauthorized handler, which sets `sessionExpired: true` and calls `handleLogout()`, clearing the token and showing a session-expired banner.

---

## Hooks

### useWebSocket

Manages the WebSocket connection lifecycle with exponential backoff reconnection and a ping watchdog.

**Interface:**
```typescript
const { wsOpen, wsError } = useWebSocket(url, onMessage);
```

**Reconnect strategy:**
- Backoff: `min(1000ms × 2^attempt, 30000ms)` — 1s, 2s, 4s, 8s, 16s, 30s, 30s, ...
- Reconnect is triggered by `onclose` — covers both clean closes and network drops
- `shouldReconnect` ref prevents reconnect after intentional unmount

**Ping watchdog:**
- Checks every 15 seconds whether a message has been received in the last 60 seconds
- If not, closes the socket — this triggers `onclose` and the reconnect loop
- Handles silently dropped connections that don't fire `onclose`

**Why refs instead of state for connection tracking:**
`socketRef` and `attemptRef` use `useRef` rather than `useState` because they are used inside closures (the `connect` function and the watchdog interval) that capture the ref object, not the value. State updates would require re-creating these closures.

### useBots

The primary hook for the trading interface. Combines bot state management, WebSocket message handling, REST API calls, and RAF log batching.

**Interface:**
```typescript
const {
    logs, botIds, lifecycle, isSimulating,
    orders, trades, selectedBotId,
    wsOpen, wsError, isLoading, fetchError,
    handleCreate, handleStop, handleRemove, handleToggleSimulation
} = useBots(clientId);
```

**Initialization sequence:**
1. `fetchWsTicket()` — exchange JWT for a single-use WebSocket ticket
2. `useWebSocket(wsUrl)` — establish WebSocket connection with the ticket
3. `getBotIds(clientId)` — load existing bots on mount
4. If bots exist: `fetchAllOrders` + `fetchAllTrades` — restore history

**WebSocket message handling:**

| Message type | Action |
|---|---|
| `log` | Push to `logBufferRef` (flushed via RAF) |
| `bot_created` | Refresh bot list, dispatch `BOT_CREATED` to state machine |
| `bot_stopped` | Dispatch `BOT_STOPPED` |
| `bot_removed` | Dispatch `BOT_REMOVED`, clear bot list |
| `order_success` | Refresh order history |
| `trade_success` | Refresh trade history |
| `error` | Set `fetchError` |

### Bot State Machine

Bot lifecycle is managed with `useReducer`. The state machine prevents impossible transitions:

```
idle ──CREATE_REQUESTED──► creating ──BOT_CREATED──► running
                                                        │
                                              STOP_REQUESTED
                                                        │
                                                        ▼
                                                    stopping ──BOT_STOPPED──► stopped
                                                                                  │
                                                                        REMOVE_REQUESTED
                                                                                  │
                                                                                  ▼
idle ◄──BOT_REMOVED──────────────────────────────────────────────────────── removing
```

The `canRemove` flag in the state prevents the remove button from being enabled when no bot exists.

### RAF Log Batching

Log messages from the WebSocket arrive at high frequency during active trading. Calling `setState` on every message would cause excessive re-renders and GC pressure.

The solution: accumulate messages in a `useRef` buffer and flush to state at most 60 times/second via `requestAnimationFrame`:

```typescript
// Accumulate — no re-render
logBufferRef.current.push(msg.message ?? "");

// Flush on animation frame
const flush = () => {
    if (logBufferRef.current.length > 0) {
        const incoming = logBufferRef.current.splice(0);
        setLogs(prev => {
            const next = [...prev, ...incoming];
            return next.length > MAX_LOG_LINES ? next.slice(-MAX_LOG_LINES) : next;
        });
    }
    rafRef.current = requestAnimationFrame(flush);
};
```

`MAX_LOG_LINES = 500` caps the log buffer to prevent unbounded memory growth.

### useConfigCheckboxes

Manages the checkbox state for the parameters and indicators configuration panels. Handles loading from the API, local toggle state, and saving back to the API.

### useIdleTimeout

Detects user inactivity and triggers a logout after `VITE_IDLE_TIMEOUT_MS` (default: 30 minutes). Listens to `mousemove`, `keydown`, `click`, and `scroll` events to reset the timer.

---

## API Integration

REST API calls are centralised in `src/utils/api.ts`. All functions:

- Accept typed parameters
- Return typed responses
- Include the Authorization header from the auth context
- Throw on non-2xx responses

```typescript
export async function getBotIds(clientId: string): Promise<string[]> {
    const res = await fetch(`${API}/clients/${clientId}/bots`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` }
    });
    if (!res.ok) throw new Error(`Failed to fetch bots: ${res.status}`);
    const data: BotListResponse = await res.json();
    return data.botids;
}
```

The `fetchWsTicket` function exchanges the JWT for a WebSocket ticket before connecting:

```typescript
export async function fetchWsTicket(): Promise<string | null> {
    try {
        const res = await fetch(`${API}/ws/ticket`, {
            method: "POST",
            headers: { Authorization: `Bearer ${getAuthToken()}` }
        });
        if (!res.ok) return null;
        const data: WsTicketResponse = await res.json();
        return data.ticket;
    } catch {
        return null;  // fall back to token-in-URL for dev mode
    }
}
```

---

## State Management

The application uses a combination of local state (hooks), `useReducer` (bot state machine), and React context (auth). Redux is available as a dependency but the primary state management is hook-based.

**State ownership:**

| State | Owner | Mechanism |
|---|---|---|
| Auth user/token | `AuthProvider` | React context |
| Bot lifecycle | `useBots` | `useReducer` (state machine) |
| Bot IDs | `useBots` | `useState` |
| Log messages | `useBots` | `useState` + RAF buffer |
| Trade/order history | `useBots` | `useState` |
| Config checkboxes | `useConfigCheckboxes` | `useState` |
| WebSocket connection | `useWebSocket` | `useState` + `useRef` |

---

## Chart Rendering

The P&L chart uses Recharts. Trade history data is transformed into chart-compatible format before rendering. The chart is only rendered when trade data is available, preventing empty chart renders on initial load.

---

## Build Configuration

### Vite

`vite.config.js` configures:

- **Vendor chunk splitting:** Recharts and React are split into separate cached chunks. This means a code change in the app does not invalidate the vendor cache.
- **Environment variables:** `VITE_*` variables are injected at build time via `import.meta.env`

### TypeScript

`tsconfig.json` enables strict mode:
- `strict: true` — enables all strict type checks
- `noUnusedLocals: true` — errors on unused variables
- `noUnusedParameters: true` — errors on unused function parameters

### ESLint

`eslint.config.js` uses the v9 flat config format with:
- `@typescript-eslint` — TypeScript-specific rules
- `eslint-plugin-react-hooks` — enforces Rules of Hooks
- `eslint-plugin-jsx-a11y` — accessibility rules

---

## Production Build

```bash
make build-web
# or
cd packages/web && npm run build
```

Output goes to `packages/web/dist/`. The nginx configuration (`packages/web/nginx.conf`) serves the built files with:

- `gzip` compression (3× smaller downloads)
- `X-Frame-Options: DENY` (clickjacking protection)
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy` as an HTTP header
- `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`

---

## Mock Testing with MSW

Tests use Mock Service Worker v2 (MSW) to intercept HTTP requests and WebSocket connections. Mock handlers are defined in `src/mocks/`.

**HTTP mock example:**
```typescript
import { http, HttpResponse } from "msw";

export const handlers = [
    http.get("/api/v1/clients/:clientId/bots", () => {
        return HttpResponse.json({ botids: ["test-bot-id"] });
    }),
    http.post("/api/v1/clients/:clientId/bots", () => {
        return HttpResponse.json({ botid: "new-bot-id" });
    }),
];
```

**WebSocket mock example:**
```typescript
import { ws } from "msw";

export const wsHandlers = [
    ws.link("ws://localhost:8000/api/v1/ws/:clientId").addEventListener("connection", ({ client }) => {
        client.send(JSON.stringify({ type: "connected", client_id: "test-client", ts: 0 }));
    }),
];
```

MSW intercepts at the network level, so components under test make real `fetch` and `WebSocket` calls — the mocks are transparent to the component code.
