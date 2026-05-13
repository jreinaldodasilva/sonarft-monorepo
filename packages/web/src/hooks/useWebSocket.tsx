import { useState, useEffect, useRef } from "react";

const BACKOFF_BASE_MS = 1000;
const BACKOFF_MAX_MS = 30000;

/** Close the socket if no message is received within this window (2× server ping interval). */
const PING_TIMEOUT_MS = 60_000;
/** How often to check whether the ping timeout has elapsed. */
const PING_CHECK_INTERVAL_MS = 15_000;

interface UseWebSocketReturn {
    socket: WebSocket | null;
    wsOpen: boolean;
    wsError: string | null;
}

const useWebSocket = (url: string, autoReconnect = true): UseWebSocketReturn => {
    const [socket, setSocket] = useState<WebSocket | null>(null);
    const [wsOpen, setWsOpen] = useState(false);
    const [wsError, setWsError] = useState<string | null>(null);

    const shouldReconnect = useRef(true);
    const attemptRef = useRef(0);
    const socketRef = useRef<WebSocket | null>(null);
    // Initialized inside the effect so fake timers in tests see the correct value
    const lastMessageRef = useRef<number>(0);

    useEffect(() => {
        shouldReconnect.current = true;
        attemptRef.current = 0;
        lastMessageRef.current = Date.now();

        const connect = (): void => {
            if (!shouldReconnect.current) return;

            const ws = new WebSocket(url);

            ws.onopen = () => {
                attemptRef.current = 0;
                lastMessageRef.current = Date.now();
                setWsError(null);
                setWsOpen(true);
                socketRef.current = ws;
                setSocket(ws);
            };

            // Use addEventListener so useBots can also set onmessage without
            // overwriting this ping-reset listener.
            ws.addEventListener("message", () => {
                lastMessageRef.current = Date.now();
            });

            ws.onerror = () => {
                setWsError("WebSocket connection error — check server status");
            };

            ws.onclose = () => {
                setWsOpen(false);
                socketRef.current = null;
                setSocket(null);

                if (autoReconnect && shouldReconnect.current) {
                    const delay = Math.min(
                        BACKOFF_BASE_MS * Math.pow(2, attemptRef.current),
                        BACKOFF_MAX_MS
                    );
                    attemptRef.current += 1;
                    setTimeout(connect, delay);
                }
            };
        };

        connect();

        // Ping timeout watchdog — closes a silently dropped connection so the
        // reconnect loop can re-establish it. Fires every PING_CHECK_INTERVAL_MS;
        // closes the socket if no message has been received in PING_TIMEOUT_MS.
        const watchdog = setInterval(() => {
            const ws = socketRef.current;
            if (ws && ws.readyState === 1 /* WebSocket.OPEN */) {
                if (Date.now() - lastMessageRef.current > PING_TIMEOUT_MS) {
                    ws.close();
                }
            }
        }, PING_CHECK_INTERVAL_MS);

        return () => {
            clearInterval(watchdog);
            shouldReconnect.current = false;
            if (socketRef.current) {
                socketRef.current.close();
                socketRef.current = null;
            }
            setSocket(null);
            setWsOpen(false);
        };
    }, [url, autoReconnect]);

    return { socket, wsOpen, wsError };
};

export default useWebSocket;
