import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";
import Parameters from "../components/Parameters/Parameters";
import Indicators from "../components/Indicators/Indicators";
import PrivateRoute from "../components/PrivateRoute/PrivateRoute";
import { mockUser } from "../mocks/fixtures";

// ### Parameters workflow ###

describe("Parameters — integration", () => {
    it("loads parameters from server on mount", async () => {
        render(<Parameters clientId={mockUser.id} />);
        await waitFor(() =>
            expect(screen.getByText("Binance")).toBeInTheDocument()
        );
    });

    it("shows save feedback on successful POST", async () => {
        render(<Parameters clientId={mockUser.id} />);
        await waitFor(() => screen.getByText("Binance"));
        fireEvent.click(screen.getByText("Set bot parameters"));
        await waitFor(() =>
            expect(screen.getByText("✓ Saved")).toBeInTheDocument()
        );
    });

    it("shows error feedback when POST fails", async () => {
        server.use(
            http.post("http://localhost:5000/bot/set_parameters/:clientId", () =>
                HttpResponse.json({ error: "Server error" }, { status: 500 })
            )
        );
        render(<Parameters clientId={mockUser.id} />);
        await waitFor(() => screen.getByText("Binance"));
        fireEvent.click(screen.getByText("Set bot parameters"));
        await waitFor(() =>
            expect(screen.getByText("✗ Error — try again")).toBeInTheDocument()
        );
    });

    it("falls back gracefully when server returns 500", async () => {
        server.use(
            http.get("http://localhost:5000/bot/get_parameters/:clientId", () =>
                HttpResponse.json({}, { status: 500 })
            )
        );
        render(<Parameters clientId={mockUser.id} />);
        await waitFor(() =>
            expect(screen.getByText("Parameters")).toBeInTheDocument()
        );
    });
});

// ### Indicators workflow ###

describe("Indicators — integration", () => {
    it("loads indicators from server on mount", async () => {
        render(<Indicators clientId={mockUser.id} />);
        await waitFor(() =>
            expect(screen.getByText("5min")).toBeInTheDocument()
        );
    });

    it("shows save feedback on successful POST", async () => {
        render(<Indicators clientId={mockUser.id} />);
        await waitFor(() => screen.getByText("5min"));
        fireEvent.click(screen.getByText("Set bot indicators"));
        await waitFor(() =>
            expect(screen.getByText("✓ Saved")).toBeInTheDocument()
        );
    });
});

// ### PrivateRoute auth gate ###

describe("PrivateRoute — auth gate", () => {
    it("renders children when user is authenticated", () => {
        render(
            <MemoryRouter>
                <PrivateRoute value={mockUser}>
                    <div>Trading Interface</div>
                </PrivateRoute>
            </MemoryRouter>
        );
        expect(screen.getByText("Trading Interface")).toBeInTheDocument();
    });

    it("redirects to / when user is null", () => {
        render(
            <MemoryRouter initialEntries={["/crypto"]}>
                <PrivateRoute value={null}>
                    <div>Trading Interface</div>
                </PrivateRoute>
            </MemoryRouter>
        );
        expect(screen.queryByText("Trading Interface")).not.toBeInTheDocument();
    });
});
