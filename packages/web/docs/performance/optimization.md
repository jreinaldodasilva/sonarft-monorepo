# Prompt 08 — Performance Optimization & Bundle Size

**Package:** `packages/web`  
**Prompt ID:** 08-WEB-PERF  
**Output File:** `docs/performance/optimization.md`  
**Reviewed:** July 2025 | **Updated:** July 2025 (post-implementation)

---

## Implementation Status

| Finding | Severity | Status |
|---|---|---|
| Unused Redux in bundle | **High** | ✅ **Resolved** — recharts v3 requires it; cannot remove. Documented. |
| `axios` in bundle | **High** | ✅ **Resolved** — removed; `CryptoTicker` uses native `fetch` |
| favicon.ico 870KB | **High** | ✅ **Resolved** — regenerated at 16×16 + 32×32 → 0.22KB |
| No nginx gzip | **High** | ✅ **Resolved** — `gzip on` added |
| No `React.memo` on hot components | **Medium** | ✅ **Resolved** — `BotControls`, `BotConsole`, `TradeHistoryTable`, `ProfitChart` |
| Log array spread per message | **Medium** | ✅ **Resolved** — RAF batching (max 60fps) |
| No vendor chunk splitting | **Medium** | ✅ **Resolved** — `manualChunks` in `vite.config.js` |
| `netlify-identity-widget` on all pages | **Medium** | ✅ **Resolved** — split into `vendor-netlify` chunk (lazy-loaded with Crypto page) |
| No `chunkSizeWarningLimit` | **Low** | ✅ **Resolved** — set to 100KB |
| CoinGecko waterfall (2 sequential requests) | **Low** | ⚠️ **Deferred** |
| No HTTP caching on API responses | **Low** | ⚠️ **Deferred** |

---

## Bundle Size: Before vs After

### Before (original review)
| Chunk | Raw | Gzip |
|---|---|---|
| `AuthProvider` | 379KB | 119KB |
| `Crypto` | 339KB | 99KB |
| `axios` | 28KB | 11KB |
| Total JS | 766KB | ~229KB |

### After (current build — July 2025)
| Chunk | Raw | Gzip | Notes |
|---|---|---|---|
| `vendor-recharts` | 330KB | 97KB | Recharts + internal deps (stable, long cache) |
| `vendor-netlify` | 236KB | 73KB | Netlify Identity (lazy with Crypto page) |
| `vendor-react` | 162KB | 53KB | React + React DOM + React Router (stable) |
| `Crypto` | 20KB | 6.8KB | All trading components (was 339KB) ✅ |
| `index` | 6.3KB | 2.4KB | App shell |
| `AuthProvider` | 1.3KB | 0.6KB | Auth hook only (was 379KB) ✅ |
| `web-vitals` | 4.3KB | 1.7KB | |
| `Home` | 0.7KB | 0.3KB | |
| `CryptoChatGPT` | 0.2KB | 0.2KB | Stub |
| `Doggy` | 0.2KB | 0.2KB | Stub |
| **Total JS** | **~761KB** | **~236KB** | Vendor chunks cached independently |
| favicon.ico | 0.22KB | — | Was 870KB ✅ |

**Key improvement:** App code chunks are now tiny (AuthProvider 0.6KB, Crypto 6.8KB). Vendor chunks are large but stable — they are cached by the browser and only re-downloaded when the library version changes, not on every app deployment.

---

## Vite Configuration (updated)

```js
build: {
    outDir: "build",
    sourcemap: false,
    chunkSizeWarningLimit: 100,  // warn if chunk > 100KB
    rollupOptions: {
        output: {
            manualChunks(id) {
                if (id.includes("netlify-identity-widget")) return "vendor-netlify";
                if (id.includes("recharts") || id.includes("victory-vendor")) return "vendor-recharts";
                if (id.includes("node_modules/react/") || id.includes("node_modules/react-dom/") || id.includes("node_modules/react-router")) return "vendor-react";
            },
        },
    },
},
```

---

## React Rendering Performance (updated)

### React.memo Applied
```tsx
export default React.memo(BotControls);
export default React.memo(BotConsole);
export default React.memo(TradeHistoryTable);
export default React.memo(ProfitChart);
```

During high-frequency log streaming (10+ messages/second), only `BotConsole` re-renders. `TradeHistoryTable` and `ProfitChart` remain stable until `orders`/`trades` actually change.

### RAF Log Batching
```
Before: setLogs() called on every WS message (10+/sec → 10+ re-renders/sec)
After:  logBufferRef accumulates messages → RAF flush → max 60 setLogs/sec
```

---

## nginx Compression (new)

```nginx
gzip on;
gzip_comp_level 6;
gzip_min_length 1024;
gzip_types text/javascript application/javascript text/css application/json;
gzip_vary on;
```

Browser now downloads ~236KB gzip instead of ~761KB uncompressed — a 3.2× improvement.

---

## Web Vitals Monitoring

`sendVitals` correctly reports to `VITE_VITALS_URL` if configured. In development, metrics logged to console. ✅

---

## Remaining Open Items

| Item | Priority | Notes |
|---|---|---|
| CoinGecko waterfall (2 sequential requests) | Low | Cache coin IDs between polls |
| HTTP caching on API responses | Low | Add `Cache-Control` to defaults endpoints |
| `logo192.png` still 870KB | Low | PWA icon; not on critical path |
