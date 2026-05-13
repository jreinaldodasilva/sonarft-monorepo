import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import useWebSocket from "./useWebSocket";

interface MockWs {
    close: ReturnType<typeof vi.fn>;
    send: ReturnType<typeof vi.fn>;
    onopen: (() => void) | null;
    onclose: (() => void) | null;
    onerror: (() => void) | null;
    readyState: number;
    addEventListener: ReturnType<typeof vi.fn>;
    dispatchEvent: ReturnType<typeof vi.fn>;
}

const createMockWs = (): MockWs => ({
    close: vi.fn(),
    send: vi.fn(),
    onopen: null,
    onclose: null,
    onerror: null,
    readyState: 1, // WebSocket.OPEN
    addEventListener: vi.fn((event: string, handler: EventListenerOrEventListenerObject) => {
        if (event === "message") {
            (mockWsInstance as unknown as Record<string, unknown>)._messageHandler = handler;
        }
    }),
    dispatchEvent: vi.fn((e: Event) => {
        const handler = (mockWsInstance as unknown as Record<string, unknown>)._messageHandler;
        if (typeof handler === "function") handler(e);
        return true;
    }),
});

let mockWsInstance: MockWs;

beforeEach(() => {
    vi.useFakeTimers();
    mockWsInstance = createMockWs();
    vi.stubGlobal(
        "WebSocket",
        vi.fn(() => mockWsInstance)
    );
});

afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
});

describe("useWebSocket — connection", () => {
    it("opens a WebSocket connection on mount", () => {
        renderHook(() => useWebSocket("ws://localhost:5000/ws/test"));
        expect(WebSocket).toHaveBeenCalledWith("ws://localhost:5000/ws/test");
        expect(WebSocket).toHaveBeenCalledTimes(1);
    });

    it("sets wsOpen to true when connection opens", () => {
        const { result } = renderHook(() => useWebSocket("ws://test"));
        act(() => {
            mockWsInstance.onopen?.();
        });
        expect(result.current.wsOpen).toBe(true);
    });

    it("sets wsOpen to false when connection closes", () => {
        const { result } = renderHook(() => useWebSocket("ws://test", false));
        act(() => {
            mockWsInstance.onopen?.();
        });
        expect(result.current.wsOpen).toBe(true);
        act(() => {
            mockWsInstance.onclose?.();
        });
        expect(result.current.wsOpen).toBe(false);
    });

    it("returns socket instance after connection opens", () => {
        const { result } = renderHook(() => useWebSocket("ws://test"));
        act(() => {
            mockWsInstance.onopen?.();
        });
        expect(result.current.socket).toBe(mockWsInstance);
    });
});

describe("useWebSocket — error handling", () => {
    it("sets wsError when onerror fires", () => {
        const { result } = renderHook(() => useWebSocket("ws://test"));
        act(() => {
            mockWsInstance.onerror?.();
        });
        expect(result.current.wsError).toBeTruthy();
        expect(typeof result.current.wsError).toBe("string");
    });

    it("clears wsError when connection successfully opens", () => {
        const { result } = renderHook(() => useWebSocket("ws://test"));
        act(() => {
            mockWsInstance.onerror?.();
        });
        expect(result.current.wsError).toBeTruthy();
        act(() => {
            mockWsInstance.onopen?.();
        });
        expect(result.current.wsError).toBeNull();
    });
});

describe("useWebSocket — memory leak fix", () => {
    it("does NOT create a new WebSocket after unmount", () => {
        const { unmount } = renderHook(() => useWebSocket("ws://test", true));
        act(() => {
            mockWsInstance.onopen?.();
        });
        unmount();
        act(() => {
            mockWsInstance.onclose?.();
        });
        act(() => {
            vi.runAllTimers();
        });
        expect(WebSocket).toHaveBeenCalledTimes(1);
    });

    it("closes the socket on unmount", () => {
        const { unmount } = renderHook(() => useWebSocket("ws://test"));
        act(() => {
            mockWsInstance.onopen?.();
        });
        unmount();
        expect(mockWsInstance.close).toHaveBeenCalled();
    });
});

describe("useWebSocket — reconnect backoff", () => {
    it("reconnects after close when autoReconnect is true", () => {
        renderHook(() => useWebSocket("ws://test", true));
        act(() => {
            mockWsInstance.onopen?.();
        });
        act(() => {
            mockWsInstance.onclose?.();
        });
        act(() => {
            vi.advanceTimersByTime(1000);
        });
        expect(WebSocket).toHaveBeenCalledTimes(2);
    });

    it("does NOT reconnect when autoReconnect is false", () => {
        renderHook(() => useWebSocket("ws://test", false));
        act(() => {
            mockWsInstance.onopen?.();
        });
        act(() => {
            mockWsInstance.onclose?.();
        });
        // Use advanceTimersByTime instead of runAllTimers to avoid infinite loop
        // from the watchdog setInterval
        act(() => {
            vi.advanceTimersByTime(60_000);
        });
        expect(WebSocket).toHaveBeenCalledTimes(1);
    });

    it("uses exponential backoff on repeated failures", () => {
        const secondMockWs = createMockWs();
        vi.mocked(WebSocket)
            .mockImplementationOnce(() => mockWsInstance as unknown as WebSocket)
            .mockImplementationOnce(() => secondMockWs as unknown as WebSocket);

        renderHook(() => useWebSocket("ws://test", true));

        act(() => {
            mockWsInstance.onclose?.();
        });
        act(() => {
            vi.advanceTimersByTime(999);
        });
        expect(WebSocket).toHaveBeenCalledTimes(1);

        act(() => {
            vi.advanceTimersByTime(1);
        });
        expect(WebSocket).toHaveBeenCalledTimes(2);

        act(() => {
            secondMockWs.onclose?.();
        });
        act(() => {
            vi.advanceTimersByTime(1999);
        });
        expect(WebSocket).toHaveBeenCalledTimes(2);

        act(() => {
            vi.advanceTimersByTime(1);
        });
        expect(WebSocket).toHaveBeenCalledTimes(3);
    });
});

describe("useWebSocket — ping timeout watchdog", () => {
    it("closes the socket when no message is received within 60 seconds", () => {
        // Spy on Date.now so we can control the gap without relying on fake timer Date integration
        let fakeNow = 1000;
        const dateSpy = vi.spyOn(Date, "now").mockImplementation(() => fakeNow);

        renderHook(() => useWebSocket("ws://test", true));
        act(() => {
            mockWsInstance.onopen?.();
        });

        // Advance fake time past the 60s threshold
        fakeNow += 61_000;
        act(() => {
            vi.advanceTimersByTime(61_000);
        });

        expect(mockWsInstance.close).toHaveBeenCalled();
        dateSpy.mockRestore();
    });

    it("does NOT close the socket when messages are received within 60 seconds", () => {
        renderHook(() => useWebSocket("ws://test", true));

        act(() => {
            mockWsInstance.onopen?.();
        });

        // Simulate a message arriving at 30s
        act(() => {
            vi.advanceTimersByTime(30_000);
            mockWsInstance.dispatchEvent?.(new MessageEvent("message", { data: "ping" }));
        });

        // Advance another 30s (60s total from open, but only 30s since last message)
        act(() => {
            vi.advanceTimersByTime(30_000);
        });

        expect(mockWsInstance.close).not.toHaveBeenCalled();
    });
});
