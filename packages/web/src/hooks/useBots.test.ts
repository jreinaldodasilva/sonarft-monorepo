import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import useBots, { BotState, BotStatus } from "./useBots";
import * as api from "../utils/api";
import * as helpers from "../utils/helpers";

// ### Mocks ###

vi.mock("./useWebSocket", () => ({
    default: vi.fn(),
}));

vi.mock("../utils/api", () => ({
    getBotIds: vi.fn(),
    getAuthToken: vi.fn(() => null),
    fetchWsTicket: vi.fn(() => Promise.resolve(null)),
}));

vi.mock("../utils/helpers", () => ({
    fetchAllOrders: vi.fn(),
    fetchAllTrades: vi.fn(),
}));

import useWebSocket from "./useWebSocket";

interface MockSocket {
    send: ReturnType<typeof vi.fn>;
    onmessage: ((e: MessageEvent) => void) | null;
}

const createMockSocket = (): MockSocket => ({
    send: vi.fn(),
    onmessage: null,
});

let mockSocket: MockSocket;

const setupWebSocketMock = (open = true, error: string | null = null) => {
    mockSocket = createMockSocket();
    vi.mocked(useWebSocket).mockReturnValue({
        socket: open ? (mockSocket as unknown as WebSocket) : null,
        wsOpen: open,
        wsError: error,
    });
};

const sendWsMessage = (type: string, extra: Record<string, unknown> = {}) => {
    const event = { data: JSON.stringify({ type, ...extra }) } as MessageEvent<string>;
    mockSocket.onmessage?.(event);
};

beforeEach(() => {
    vi.clearAllMocks();
    setupWebSocketMock();
    vi.mocked(api.getBotIds).mockResolvedValue(["bot_001"]);
    vi.mocked(helpers.fetchAllOrders).mockResolvedValue([]);
    vi.mocked(helpers.fetchAllTrades).mockResolvedValue([]);
    window.confirm = vi.fn(() => true);
});

afterEach(() => {
    vi.restoreAllMocks();
});

// ### Initial load ###

describe("useBots — initial load", () => {
    it("fetches bot IDs on mount", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.isLoading).toBe(false));
        expect(api.getBotIds).toHaveBeenCalledWith("client_123");
        expect(result.current.botIds).toEqual(["bot_001"]);
    });

    it("sets fetchError when getBotIds fails", async () => {
        vi.mocked(api.getBotIds).mockRejectedValueOnce(new Error("Network error"));
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.fetchError).toBeTruthy());
        expect(result.current.fetchError).toContain("Could not load bots");
    });

    it("resolves WS URL via ticket when fetchWsTicket succeeds", async () => {
        vi.mocked(api.fetchWsTicket).mockResolvedValueOnce("test-ticket-abc");
        renderHook(() => useBots("client_123"));
        await waitFor(() =>
            expect(useWebSocket).toHaveBeenCalledWith(
                expect.stringContaining("?ticket=test-ticket-abc"),
                true
            )
        );
    });

    it("falls back to token URL when fetchWsTicket returns null", async () => {
        vi.mocked(api.fetchWsTicket).mockResolvedValueOnce(null);
        vi.mocked(api.getAuthToken).mockReturnValueOnce(null);
        renderHook(() => useBots("client_123"));
        await waitFor(() =>
            expect(useWebSocket).toHaveBeenCalledWith(
                expect.stringContaining("client_123"),
                true
            )
        );
    });
});

// ### WebSocket events ###

describe("useBots — bot_created event", () => {
    it("fetches updated bot list on bot_created", async () => {
        vi.mocked(api.getBotIds).mockResolvedValue(["bot_001", "bot_002"]);
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.wsOpen).toBe(true));

        await act(async () => {
            sendWsMessage("bot_created", { botid: "bot_002" });
            await Promise.resolve();
        });

        await waitFor(() => expect(result.current.botStatus).toBe(BotStatus.RUNNING));
        expect(result.current.selectedBotId).toBe("bot_002");
        // Server now auto-runs the bot — client no longer sends a run keypress
        expect(mockSocket.send).not.toHaveBeenCalledWith(
            JSON.stringify({ type: "keypress", key: "run", botid: "bot_002" })
        );
    });
});

describe("useBots — bot_removed event", () => {
    it("resets botState and botStatus", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.wsOpen).toBe(true));

        act(() => { sendWsMessage("bot_removed"); });

        expect(result.current.botState).toBe(BotState.REMOVED);
        expect(result.current.botStatus).toBe(BotStatus.IDLE);
    });
});

describe("useBots — order_success event", () => {
    it("calls fetchAllOrders with current botIds", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.botIds).toEqual(["bot_001"]));

        await act(async () => {
            sendWsMessage("order_success");
            await Promise.resolve();
        });

        await waitFor(() => expect(helpers.fetchAllOrders).toHaveBeenCalledWith(["bot_001"]));
    });
});

describe("useBots — trade_success event", () => {
    it("calls fetchAllTrades with current botIds", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.botIds).toEqual(["bot_001"]));

        await act(async () => {
            sendWsMessage("trade_success");
            await Promise.resolve();
        });

        await waitFor(() => expect(helpers.fetchAllTrades).toHaveBeenCalledWith(["bot_001"]));
    });
});

describe("useBots — error event", () => {
    it("sets fetchError from server error message", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.wsOpen).toBe(true));

        act(() => { sendWsMessage("error", { message: "Bot limit reached (5)" }); });

        expect(result.current.fetchError).toBe("Bot limit reached (5)");
    });

    it("uses fallback message when error event has no message", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.wsOpen).toBe(true));

        act(() => { sendWsMessage("error"); });

        expect(result.current.fetchError).toBeTruthy();
    });
});

describe("useBots — log event", () => {
    it("appends log messages to logs array", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.wsOpen).toBe(true));

        act(() => { sendWsMessage("log", { message: "INFO: bot started" }); });

        // RAF doesn't fire in jsdom — advance timers to trigger the flush
        await act(async () => { await new Promise((r) => setTimeout(r, 50)); });

        expect(result.current.logs).toContain("INFO: bot started");
    });

    it("caps logs at MAX_LOG_LINES (500)", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.wsOpen).toBe(true));

        act(() => {
            for (let i = 0; i < 510; i++) {
                sendWsMessage("log", { message: `line ${i}` });
            }
        });

        await act(async () => { await new Promise((r) => setTimeout(r, 50)); });

        expect(result.current.logs.length).toBeLessThanOrEqual(500);
    });

    it("handles non-JSON raw log strings", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.wsOpen).toBe(true));

        act(() => {
            const event = { data: "plain text log line" } as MessageEvent<string>;
            mockSocket.onmessage?.(event);
        });

        await act(async () => { await new Promise((r) => setTimeout(r, 50)); });

        expect(result.current.logs).toContain("plain text log line");
    });
});

// ### handleCreate ###

describe("useBots — handleCreate", () => {
    it("sends create command when connected", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.wsOpen).toBe(true));

        act(() => { result.current.handleCreate(); });

        expect(mockSocket.send).toHaveBeenCalledWith(
            JSON.stringify({ type: "keypress", key: "create" })
        );
    });

    it("sets fetchError when not connected", async () => {
        setupWebSocketMock(false);
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.isLoading).toBe(false));

        act(() => { result.current.handleCreate(); });

        expect(result.current.fetchError).toContain("not connected");
        expect(mockSocket.send).not.toHaveBeenCalled();
    });
});

// ### handleRemove ###

describe("useBots — handleRemove", () => {
    it("sends remove command after confirmation", async () => {
        vi.mocked(api.getBotIds).mockResolvedValue(["bot_001"]);
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.botIds).toEqual(["bot_001"]));

        act(() => { result.current.setSelectedBotId("bot_001"); });
        act(() => { result.current.handleRemove(); });

        expect(window.confirm).toHaveBeenCalled();
        expect(mockSocket.send).toHaveBeenCalledWith(
            JSON.stringify({ type: "keypress", key: "remove", botid: "bot_001" })
        );
    });

    it("does not send if user cancels confirmation", async () => {
        window.confirm = vi.fn(() => false);
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.isLoading).toBe(false));

        act(() => { result.current.setSelectedBotId("bot_001"); });
        act(() => { result.current.handleRemove(); });

        expect(mockSocket.send).not.toHaveBeenCalled();
    });
});

// ### handleToggleSimulation ###

describe("useBots — handleToggleSimulation", () => {
    it("sends set_simulation with botid and new value", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.wsOpen).toBe(true));

        act(() => { result.current.setSelectedBotId("bot_001"); });
        act(() => { result.current.handleToggleSimulation(); });

        expect(mockSocket.send).toHaveBeenCalledWith(
            JSON.stringify({ type: "keypress", key: "set_simulation", botid: "bot_001", value: false })
        );
        expect(result.current.isSimulating).toBe(false);
    });

    it("does nothing when no bot is selected", async () => {
        const { result } = renderHook(() => useBots("client_123"));
        await waitFor(() => expect(result.current.wsOpen).toBe(true));

        act(() => { result.current.handleToggleSimulation(); });

        expect(mockSocket.send).not.toHaveBeenCalled();
    });
});
