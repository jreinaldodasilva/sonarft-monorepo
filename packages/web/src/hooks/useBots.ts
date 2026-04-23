import { useState, useEffect, useCallback, useRef, useReducer } from "react";
import useWebSocket from "./useWebSocket";
import { getBotIds, getAuthToken, fetchWsTicket } from "../utils/api";
import type { TradeRecord } from "../utils/api";
import { WS } from "../utils/constants";
import { fetchAllOrders, fetchAllTrades } from "../utils/helpers";

const MAX_LOG_LINES = 500;

// ### Bot state machine ###

type BotLifecycle = "idle" | "creating" | "running" | "removing" | "error";

interface BotMachineState {
    lifecycle: BotLifecycle;
    /** True when a bot exists and can be removed (lifecycle !== idle) */
    canRemove: boolean;
}

type BotMachineAction =
    | { type: "CREATE_REQUESTED" }
    | { type: "BOT_CREATED" }
    | { type: "REMOVE_REQUESTED" }
    | { type: "BOT_REMOVED" }
    | { type: "ERROR" };

const initialMachineState: BotMachineState = { lifecycle: "idle", canRemove: false };

function botMachineReducer(state: BotMachineState, action: BotMachineAction): BotMachineState {
    switch (action.type) {
        case "CREATE_REQUESTED":
            return { lifecycle: "creating", canRemove: false };
        case "BOT_CREATED":
            return { lifecycle: "running", canRemove: true };
        case "REMOVE_REQUESTED":
            return { ...state, lifecycle: "removing" };
        case "BOT_REMOVED":
            return { lifecycle: "idle", canRemove: false };
        case "ERROR":
            return { ...state, lifecycle: "error" };
        default:
            return state;
    }
}

// Legacy exports kept for BotControls / Bots compatibility
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
    lifecycle: BotLifecycle;
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
    handleStop: () => void;
    handleRemove: () => void;
    handleToggleSimulation: () => void;
}

const useBots = (clientId: string): UseBotsReturn => {
    const [wsUrl, setWsUrl] = useState<string | null>(null);

    const [logs, setLogs] = useState<string[]>([]);
    const logBufferRef = useRef<string[]>([]);
    const rafRef = useRef<number | null>(null);
    const [botIds, setBotIds] = useState<string[]>([]);
    const botIdsRef = useRef<string[]>([]);
    const [machine, dispatch] = useReducer(botMachineReducer, initialMachineState);
    const [trades, setTrades] = useState<TradeRecord[]>([]);
    const [orders, setOrders] = useState<TradeRecord[]>([]);
    const [selectedBotId, setSelectedBotId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [fetchError, setFetchError] = useState<string | null>(null);
    const [isSimulating, setIsSimulating] = useState(true);

    // Keep botIdsRef in sync so the onmessage closure always has the current list
    useEffect(() => { botIdsRef.current = botIds; }, [botIds]);

    // Flush log buffer to state on animation frame — caps re-renders at 60fps
    useEffect(() => {
        const flush = () => {
            if (logBufferRef.current.length > 0) {
                const incoming = logBufferRef.current.splice(0);
                setLogs((prev) => {
                    const next = [...prev, ...incoming];
                    return next.length > MAX_LOG_LINES ? next.slice(-MAX_LOG_LINES) : next;
                });
            }
            rafRef.current = requestAnimationFrame(flush);
        };
        rafRef.current = requestAnimationFrame(flush);
        return () => {
            if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
        };
    }, []);

    // Fetch a single-use WS ticket (keeps JWT out of server logs).
    // Falls back to ?token= for dev mode where the ticket endpoint is unavailable.
    useEffect(() => {
        const resolveWsUrl = async () => {
            const ticket = await fetchWsTicket();
            if (ticket) {
                setWsUrl(`${WS}/${clientId}?ticket=${encodeURIComponent(ticket)}`);
            } else {
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
                botIdsRef.current = ids;
                if (ids.length > 0) {
                    setSelectedBotId(ids[ids.length - 1]);
                    dispatch({ type: "BOT_CREATED" });
                    // Load existing history for restored bots
                    const [existingOrders, existingTrades] = await Promise.all([
                        fetchAllOrders(ids),
                        fetchAllTrades(ids),
                    ]);
                    setOrders(existingOrders);
                    setTrades(existingTrades);
                }
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
                    logBufferRef.current.push(msg.message ?? "");
                    return;
                }

                switch (msg.type) {
                    case "bot_created": {
                        const ids = await getBotIds(clientId);
                        setSelectedBotId(ids[ids.length - 1]);
                        setBotIds(ids);
                        botIdsRef.current = ids;
                        dispatch({ type: "BOT_CREATED" });
                        socket.send(JSON.stringify({ type: "keypress", key: "run", botid: ids[ids.length - 1] }));
                        break;
                    }
                    case "bot_removed":
                        dispatch({ type: "BOT_REMOVED" });
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
        dispatch({ type: "CREATE_REQUESTED" });
        socket.send(JSON.stringify({ type: "keypress", key: "create" }));
    }, [socket, wsOpen]);

    const handleStop = useCallback(() => {
        if (!socket || !selectedBotId) return;
        socket.send(JSON.stringify({ type: "keypress", key: "stop", botid: selectedBotId }));
    }, [socket, selectedBotId]);

    const handleRemove = useCallback(() => {
        if (!socket || !selectedBotId) return;
        // TODO S3-13: replace window.confirm with a styled in-app modal (like the live trading modal)
        if (!window.confirm(`Remove bot "${selectedBotId}"? This will stop the bot immediately.`)) return;
        dispatch({ type: "REMOVE_REQUESTED" });
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

    // Derive legacy botState/botStatus from the machine for backward compatibility
    const botState = machine.lifecycle === "idle" ? BotState.REMOVED : BotState.CREATED;
    const botStatus: BotStatusValue =
        machine.lifecycle === "running" ? BotStatus.RUNNING :
        machine.lifecycle === "error"   ? BotStatus.ERROR :
        BotStatus.IDLE;

    return {
        logs, botIds, botState, botStatus, lifecycle: machine.lifecycle, isSimulating,
        orders, trades, selectedBotId, setSelectedBotId,
        isLoading, fetchError, wsOpen, wsError,
        handleCreate, handleStop, handleRemove, handleToggleSimulation,
    };
};

export default useBots;
