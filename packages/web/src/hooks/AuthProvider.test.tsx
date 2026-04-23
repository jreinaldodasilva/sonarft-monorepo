import React from "react";
import { describe, it, expect } from "vitest";
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
        act(() => { screen.getByText("logout").click(); });
        expect(screen.getByTestId("user-id").textContent).toBe("null");
    });
});

describe("AuthProvider — handleLogin", () => {
    it("restores default user on login after logout", () => {
        renderWithAuth();
        act(() => { screen.getByText("logout").click(); });
        expect(screen.getByTestId("user-id").textContent).toBe("null");
        act(() => { screen.getByText("login").click(); });
        expect(screen.getByTestId("user-id").textContent).toBe("dev_user");
    });
});
