import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import useIdleTimeout from "./useIdleTimeout";

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); vi.clearAllMocks(); });

describe("useIdleTimeout", () => {
    it("fires onIdle after the timeout when enabled", () => {
        const onIdle = vi.fn();
        renderHook(() => useIdleTimeout(onIdle, 5000, true));
        act(() => { vi.advanceTimersByTime(5000); });
        expect(onIdle).toHaveBeenCalledTimes(1);
    });

    it("does NOT fire onIdle when disabled", () => {
        const onIdle = vi.fn();
        renderHook(() => useIdleTimeout(onIdle, 5000, false));
        act(() => { vi.advanceTimersByTime(10000); });
        expect(onIdle).not.toHaveBeenCalled();
    });

    it("resets the timer on user activity", () => {
        const onIdle = vi.fn();
        renderHook(() => useIdleTimeout(onIdle, 5000, true));

        act(() => { vi.advanceTimersByTime(4000); });
        expect(onIdle).not.toHaveBeenCalled();

        act(() => { window.dispatchEvent(new Event("mousemove")); });

        act(() => { vi.advanceTimersByTime(4000); });
        expect(onIdle).not.toHaveBeenCalled();

        act(() => { vi.advanceTimersByTime(1000); });
        expect(onIdle).toHaveBeenCalledTimes(1);
    });

    it("clears the timer when disabled mid-session", () => {
        const onIdle = vi.fn();
        const { rerender } = renderHook(
            ({ enabled }: { enabled: boolean }) => useIdleTimeout(onIdle, 5000, enabled),
            { initialProps: { enabled: true } }
        );

        act(() => { vi.advanceTimersByTime(3000); });
        rerender({ enabled: false });
        act(() => { vi.advanceTimersByTime(5000); });
        expect(onIdle).not.toHaveBeenCalled();
    });

    it("clears event listeners and timer on unmount", () => {
        const onIdle = vi.fn();
        const spy = vi.spyOn(window, "removeEventListener");

        const { unmount } = renderHook(() => useIdleTimeout(onIdle, 5000, true));
        unmount();

        expect(spy).toHaveBeenCalled();
        act(() => { vi.advanceTimersByTime(10000); });
        expect(onIdle).not.toHaveBeenCalled();

        spy.mockRestore();
    });
});
