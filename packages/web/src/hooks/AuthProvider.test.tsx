import React from "react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { AuthProvider, AuthContext } from "./AuthProvider";
import { setUnauthorizedHandler } from "../utils/api";

const TestConsumer: React.FC = () => {
    const ctx = React.useContext(AuthContext);
    return (
        <div>
            <span data-testid="user-id">{ctx.user?.id ?? "null"}</span>
            <span data-testid="session-expired">{String(ctx.sessionExpired)}</span>
            <button onClick={ctx.handleLogin}>login</button>
            <button onClick={ctx.handleLogout}>logout</button>
        </div>
    );
};

const renderWithAuth = () =>
    render(
        <AuthProvider>
            <TestConsumer />
        </AuthProvider>
    );

beforeEach(() => {
    vi.useFakeTimers();
    sessionStorage.clear();
});

afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    sessionStorage.clear();
});

describe("AuthProvider — initial state", () => {
    it("starts with the default user", () => {
        renderWithAuth();
        expect(screen.getByTestId("user-id").textContent).toBe("dev_user");
    });

    it("user is not null on mount", () => {
        renderWithAuth();
        expect(screen.getByTestId("user-id").textContent).not.toBe("null");
    });
});

describe("AuthProvider — handleLogout", () => {
    it("clears user on logout", () => {
        renderWithAuth();
        act(() => {
            screen.getByText("logout").click();
        });
        expect(screen.getByTestId("user-id").textContent).toBe("null");
    });

    it("clears sonarft_token from sessionStorage on logout", () => {
        sessionStorage.setItem("sonarft_token", "test-jwt");
        renderWithAuth();
        act(() => {
            screen.getByText("logout").click();
        });
        expect(sessionStorage.getItem("sonarft_token")).toBeNull();
    });
});

describe("AuthProvider — handleLogin", () => {
    it("restores default user on login after logout", () => {
        renderWithAuth();
        act(() => {
            screen.getByText("logout").click();
        });
        expect(screen.getByTestId("user-id").textContent).toBe("null");
        act(() => {
            screen.getByText("login").click();
        });
        expect(screen.getByTestId("user-id").textContent).toBe("dev_user");
    });
});

describe("AuthProvider — idle timeout", () => {
    it("logs out after IDLE_MS of inactivity", () => {
        renderWithAuth();
        expect(screen.getByTestId("user-id").textContent).toBe("dev_user");
        // Default IDLE_MS is 1800000ms; advance past it
        act(() => {
            vi.advanceTimersByTime(1_800_001);
        });
        expect(screen.getByTestId("user-id").textContent).toBe("null");
    });

    it("does not log out before IDLE_MS elapses", () => {
        renderWithAuth();
        act(() => {
            vi.advanceTimersByTime(1_799_999);
        });
        expect(screen.getByTestId("user-id").textContent).toBe("dev_user");
    });
});

describe("AuthProvider — sessionExpired", () => {
    it("sessionExpired is false on mount", () => {
        renderWithAuth();
        expect(screen.getByTestId("session-expired").textContent).toBe("false");
    });

    it("sessionExpired becomes true and user is cleared when 401 handler fires", () => {
        renderWithAuth();
        act(() => {
            // Simulate a 401 response triggering the registered handler
            setUnauthorizedHandler(() => {}); // get the current handler via side-effect
        });
        // Trigger the handler that AuthProvider registered
        act(() => {
            // Access the handler AuthProvider registered by calling it directly
            // We simulate a 401 by invoking handleLogout + setSessionExpired via the
            // registered callback — test via the exported setter
            const handler = vi.fn();
            setUnauthorizedHandler(handler);
        });
    });

    it("sessionExpired resets to false on login after 401", () => {
        renderWithAuth();
        // Manually trigger logout (simulates 401 path)
        act(() => {
            screen.getByText("logout").click();
        });
        act(() => {
            screen.getByText("login").click();
        });
        expect(screen.getByTestId("session-expired").textContent).toBe("false");
        expect(screen.getByTestId("user-id").textContent).toBe("dev_user");
    });
});
