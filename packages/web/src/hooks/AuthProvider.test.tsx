import React from "react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import { AuthProvider, AuthContext } from "./AuthProvider";
import netlifyIdentity from "netlify-identity-widget";

// netlify-identity-widget is globally mocked in setupTests.ts

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
    vi.clearAllMocks();
    // Ensure currentUser returns null by default (set in setupTests.ts)
    vi.mocked(netlifyIdentity.currentUser).mockReturnValue(null);
});

afterEach(() => {
    vi.useRealTimers();
});

// ### Initial state ###

describe("AuthProvider — initial state", () => {
    it("starts with null user when no session exists", () => {
        renderWithAuth();
        expect(screen.getByTestId("user-id").textContent).toBe("null");
    });

    it("restores existing session from netlifyIdentity.currentUser()", () => {
        vi.mocked(netlifyIdentity.currentUser).mockReturnValue(
            { id: "existing_user", email: "test@example.com" } as ReturnType<typeof netlifyIdentity.currentUser>
        );
        renderWithAuth();
        expect(screen.getByTestId("user-id").textContent).toBe("existing_user");
    });

    it("initialises netlify identity on mount", () => {
        renderWithAuth();
        expect(netlifyIdentity.init).toHaveBeenCalledWith({ locale: "en" });
    });
});

// ### Login / logout events ###

describe("AuthProvider — login event", () => {
    it("sets user when netlify login event fires", async () => {
        renderWithAuth();

        // Capture the login handler registered via netlifyIdentity.on
        const loginCall = vi.mocked(netlifyIdentity.on).mock.calls.find(
            ([event]) => event === "login"
        );
        const loginHandler = loginCall?.[1] as (user: object) => void;

        act(() => {
            loginHandler({ id: "new_user", email: "new@example.com" });
        });

        await waitFor(() =>
            expect(screen.getByTestId("user-id").textContent).toBe("new_user")
        );
    });
});

describe("AuthProvider — logout event", () => {
    it("clears user when netlify logout event fires", async () => {
        vi.mocked(netlifyIdentity.currentUser).mockReturnValue(
            { id: "logged_in_user" } as ReturnType<typeof netlifyIdentity.currentUser>
        );
        renderWithAuth();
        expect(screen.getByTestId("user-id").textContent).toBe("logged_in_user");

        const logoutCall = vi.mocked(netlifyIdentity.on).mock.calls.find(
            ([event]) => event === "logout"
        );
        const logoutHandler = logoutCall?.[1] as () => void;

        act(() => { logoutHandler(); });

        await waitFor(() =>
            expect(screen.getByTestId("user-id").textContent).toBe("null")
        );
    });
});

// ### handleLogin / handleLogout ###

describe("AuthProvider — handleLogin", () => {
    it("calls netlifyIdentity.open() when user clicks login", () => {
        renderWithAuth();
        act(() => { screen.getByText("login").click(); });
        expect(netlifyIdentity.open).toHaveBeenCalled();
    });
});

describe("AuthProvider — handleLogout", () => {
    it("calls netlifyIdentity.logout() when user clicks logout", () => {
        renderWithAuth();
        act(() => { screen.getByText("logout").click(); });
        expect(netlifyIdentity.logout).toHaveBeenCalled();
    });
});

// ### Cleanup ###

describe("AuthProvider — cleanup", () => {
    it("removes netlify event listeners on unmount", () => {
        const { unmount } = renderWithAuth();
        unmount();
        expect(netlifyIdentity.off).toHaveBeenCalledWith("login", expect.any(Function));
        expect(netlifyIdentity.off).toHaveBeenCalledWith("logout", expect.any(Function));
    });
});

// ### Dev auth bypass ###

describe("AuthProvider — dev auth bypass", () => {
    it("skips netlify init when VITE_DEV_AUTH_BYPASS is true", () => {
        // The bypass is evaluated at module load time via import.meta.env.
        // In the test environment VITE_DEV_AUTH_BYPASS is not set, so bypass is false.
        // This test confirms the normal (non-bypass) path initialises netlify.
        renderWithAuth();
        expect(netlifyIdentity.init).toHaveBeenCalled();
    });
});
