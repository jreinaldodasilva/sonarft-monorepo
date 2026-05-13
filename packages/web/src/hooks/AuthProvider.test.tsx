import React from "react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { AuthProvider, AuthContext } from "./AuthProvider";

const TestConsumer: React.FC = () => {
    const ctx = React.useContext(AuthContext);
    return (
        <div>
            <span data-testid="user-id">{ctx.user?.id ?? "null"}</span>
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
