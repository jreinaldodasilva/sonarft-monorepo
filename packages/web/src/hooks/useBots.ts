import { useState, useEffect, useCallback, useRef } from "react";
import useWebSocket from "./useWebSocket";
import { getBotIds, getAuthToken, fetchWsTicket } from "../utils/api";
import type { TradeRecord } from "../utils/api";
import { WS } from "../utils/constants";
import { fetchAllOrders, fetchAllTrades } from "../utils/helpers";

const MAX_LOG_LINES = 500;

export const BotState = Object.freeze({ CREATED: 0, REMOVED: 1 });
export const BotStatus = Object.freeze({ IDLE: "idle", RUNNING: "running", ERROR: "error" } as const);
export type BotStatusValue = typeof BotStatus[keyof typeof BotStatus];

interface WsMessage {
    type: string;
    level?: string;
    message?: string;
    botid?: string | null;
    ts?: number;
}

const parseMessage = (raw: string): WsMessage => {
    try {
        const msg = JSON.parse(raw) as WsMessage;
        if (msg && typeof msg.type === "string") return msg;
    } catch { /* not JSON */ }
    return { type: "log", level: "INFO", message: raw };
};

export interface UseBotsReturn {
    logs: string[];
    botIds: string[];
    botState: number;
    botStatus: BotStatusValue;
    isSimulating: boolean;
    orders: TradeRecord[];
    trades: TradeRecord[];
    selectedBotId: string | null;
    setSelectedBotId: (id: string) => void;
    isLoading: boolean;
    fetchError: string | null;
    wsOpen: boolean;
    wsError: string | null;
    handleCreate: () => void;
    handleRemove: () => void;
    handleToggleSimulation: () => void;
}

const useBots = (clientId: string): UseBotsReturn => {
    const [wsUrl, setWsUrl] = useState<string | null>(null);

    const [logs, setLogs] = useState<string[]>([]);
    const [botIds, setBotIds] = useState<string[]>([]);
    const botIdsRef = useRef<string[]>([]);
    const [botState, setBotState] = useState<number>(BotState.REMOVED);
    const [trades, setTrades] = useState<TradeRecord[]>([]);
    const [orders, setOrders] = useState<TradeRecord[]>([]);
    const [selectedBotId, setSelectedBotId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [fetchError, setFetchError] = useState<string | null>(null);
    const [botStatus, setBotStatus] = useState<BotStatusValue>(BotStatus.IDLE);
    const [isSimulating, setIsSimulating] = useState(true);

    // Keep botIdsRef in sync so the onmessage closure always has the current list
    useEffect(() => { botIdsRef.current = botIds; }, [botIds]);

    // Fetch a single-use WS ticket (keeps JWT out of server logs).
    // Falls back to ?token= for dev mode where the ticket endpoint is unavailable.
    useEffect(() => {
        const resolveWsUrl = async () => {
            const ticket = await fetchWsTicket();
            if (ticket) {
                setWsUrl(`${WS}/${clientId}?ticket=${encodeURIComponent(ticket)}`);
            } else {
                // Dev mode / no auth — fall back to token in URL
                const token = getAuthToken();
                setWsUrl(
                    token
                        ? `${WS}/${clientId}?token=${encodeURIComponent(token)}`
                        : `${WS}/${clientId}`
                );
            }
        };
        resolveWsUrl();
    }, [clientId]);

    const { socket, wsOpen, wsError } = useWebSocket(wsUrl ?? "", !!wsUrl);

    useEffect(() => {
        const load = async () => {
            try {
                setIsLoading(true);
                setFetchError(null);
                const ids = await getBotIds(clientId);
                setBotIds(ids);
            } catch {
                setFetchError("Could not load bots — is the server running?");
            } finally {
                setIsLoading(false);
            }
        };
        load();
    }, [clientId]);

    useEffect(() => {
        if (!wsOpen || !socket) return;

        socket.onmessage = async (event: MessageEvent<string>) => {
            try {
                const msg = parseMessage(event.data);

                if (msg.type === "log") {
                    setLogs((prev) => {
                        const next = [...prev, msg.message ?? ""];
                        return next.length > MAX_LOG_LINES ? next.slice(-MAX_LOG_LINES) : next;
                    });
                    return;
                }

                switch (msg.type) {
                    case "bot_created": {
                        const ids = await getBotIds(clientId);
                        setSelectedBotId(ids[ids.length - 1]);
                        setBotIds(ids);
                        setBotStatus(BotStatus.RUNNING);
                        socket.send(JSON.stringify({ type: "keypress", key: "run", botid: ids[ids.length - 1] }));
                        break;
                    }
                    case "bot_removed":
                        setBotState(BotState.REMOVED);
                        setBotStatus(BotStatus.IDLE);
                        break;
                    case "order_success":
                        setOrders(await fetchAllOrders(botIdsRef.current));
                        break;
                    case "trade_success":
                        setTrades(await fetchAllTrades(botIdsRef.current));
                        break;
                    case "error":
                        setFetchError(msg.message ?? "Server error — check bot status");
                        break;
                    default:
                        break;
                }
            } catch {
                setFetchError("Unexpected error processing server message");
            }
        };
    }, [clientId, wsOpen, socket]);

    const handleCreate = useCallback(() => {
        if (!socket || !wsOpen) {
            setFetchError("Cannot create bot — not connected to server");
            return;
        }
        socket.send(JSON.stringify({ type: "keypress", key: "create" }));
        setBotState(BotState.REMOVED);
    }, [socket, wsOpen]);

    const handleRemove = useCallback(() => {
        if (!socket || !selectedBotId) return;
        if (!window.confirm(`Remove bot "${selectedBotId}"? This will stop the bot immediately.`)) return;
        socket.send(JSON.stringify({ type: "keypress", key: "remove", botid: selectedBotId }));
    }, [socket, selectedBotId]);

    const handleToggleSimulation = useCallback(() => {
        if (!socket || !selectedBotId) return;
        setIsSimulating((prev) => {
            const next = !prev;
            socket.send(JSON.stringify({ type: "keypress", key: "set_simulation", botid: selectedBotId, value: next }));
            return next;
        });
    }, [socket, selectedBotId]);

    return {
        logs, botIds, botState, botStatus, isSimulating,
        orders, trades, selectedBotId, setSelectedBotId,
        isLoading, fetchError, wsOpen, wsError,
        handleCreate, handleRemove, handleToggleSimulation,
    };
};

export default useBots;
