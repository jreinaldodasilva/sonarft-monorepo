import React from "react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { axe, toHaveNoViolations } from "jest-axe";
import { server } from "../mocks/server";
import Parameters from "../components/Parameters/Parameters";
import Indicators from "../components/Indicators/Indicators";
import PrivateRoute from "../components/PrivateRoute/PrivateRoute";
import Bots from "../components/Bots/Bots";
import type { AppUser } from "../hooks/AuthProvider";
import { mockUser } from "../mocks/fixtures";

expect.extend(toHaveNoViolations);

// ### Parameters workflow ###

describe("Parameters — integration", () => {
    it("loads parameters from server on mount", async () => {
        render(<Parameters clientId={mockUser.id} />);
        await waitFor(() => expect(screen.getByText("Binance")).toBeInTheDocument());
    });

    it("shows save feedback on successful POST", async () => {
        render(<Parameters clientId={mockUser.id} />);
        await waitFor(() => screen.getByText("Binance"));
        fireEvent.click(screen.getByText("Set bot parameters"));
        await waitFor(() => expect(screen.getByText("✓ Saved")).toBeInTheDocument());
    });

    it("shows error feedback when POST fails", async () => {
        server.use(
            http.put(`http://localhost:8000/api/v1/clients/:clientId/parameters`, () =>
                HttpResponse.json({ detail: "Server error" }, { status: 500 })
            )
        );
        render(<Parameters clientId={mockUser.id} />);
        await waitFor(() => screen.getByText("Binance"));
        fireEvent.click(screen.getByText("Set bot parameters"));
        await waitFor(() => expect(screen.getByText("✗ Error — try again")).toBeInTheDocument());
    });

    it("falls back gracefully when server returns 500", async () => {
        server.use(
            http.get(`http://localhost:8000/api/v1/clients/:clientId/parameters`, () =>
                HttpResponse.json({}, { status: 500 })
            )
        );
        render(<Parameters clientId={mockUser.id} />);
        await waitFor(() => expect(screen.getByText("Parameters")).toBeInTheDocument());
    });
});

// ### Indicators workflow ###

describe("Indicators — integration", () => {
    it("loads indicators from server on mount", async () => {
        render(<Indicators clientId={mockUser.id} />);
        await waitFor(() => expect(screen.getByText("5min")).toBeInTheDocument());
    });

    it("shows save feedback on successful POST", async () => {
        render(<Indicators clientId={mockUser.id} />);
        await waitFor(() => screen.getByText("5min"));
        fireEvent.click(screen.getByText("Set bot indicators"));
        await waitFor(() => expect(screen.getByText("✓ Saved")).toBeInTheDocument());
    });
});

// ### PrivateRoute auth gate ###

describe("PrivateRoute — auth gate", () => {
    it("renders children when user is authenticated", () => {
        render(
            <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
                <PrivateRoute value={mockUser}>
                    <div>Trading Interface</div>
                </PrivateRoute>
            </MemoryRouter>
        );
        expect(screen.getByText("Trading Interface")).toBeInTheDocument();
    });

    it("redirects to / when user is null", () => {
        render(
            <MemoryRouter
                initialEntries={["/crypto"]}
                future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
            >
                <PrivateRoute value={null}>
                    <div>Trading Interface</div>
                </PrivateRoute>
            </MemoryRouter>
        );
        expect(screen.queryByText("Trading Interface")).not.toBeInTheDocument();
    });
});

// ### Bot workflow integration tests ###
//
// Strategy: render Bots with a real useBots hook; stub WebSocket globally so
// the hook can open a connection without a real server; drive state changes by
// firing onmessage events on the stub socket.

interface MockWs {
    send: ReturnType<typeof vi.fn>;
    close: ReturnType<typeof vi.fn>;
    onopen: (() => void) | null;
    onclose: (() => void) | null;
    onerror: (() => void) | null;
    onmessage: ((e: MessageEvent) => void) | null;
    readyState: number;
    addEventListener: ReturnType<typeof vi.fn>;
    dispatchEvent: ReturnType<typeof vi.fn>;
}

const createMockWs = (): MockWs => ({
    send: vi.fn(),
    close: vi.fn(),
    onopen: null,
    onclose: null,
    onerror: null,
    onmessage: null,
    readyState: 1,
    addEventListener: vi.fn(),
    dispatchEvent: vi.fn(() => true),
});

const botUser: AppUser = { id: "workflow_client", email: "wf@test.com" };

let mockWs: MockWs;

const openWs = () => mockWs.onopen?.();

const sendWsEvent = (type: string, extra: Record<string, unknown> = {}) => {
    const event = new MessageEvent("message", {
        data: JSON.stringify({ type, ts: Date.now(), ...extra }),
    });
    mockWs.onmessage?.(event);
};

describe("Bot workflow — create flow", () => {
    beforeEach(() => {
        mockWs = createMockWs();
        vi.stubGlobal(
            "WebSocket",
            vi.fn(() => mockWs)
        );
        server.use(
            http.get("http://localhost:8000/api/v1/clients/:clientId/bots", () =>
                HttpResponse.json({ botids: [] })
            )
        );
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.clearAllMocks();
    });

    it("shows Running status after bot_created WS event", async () => {
        render(<Bots user={botUser} />);

        await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("● Idle"));

        await act(async () => {
            openWs();
        });

        server.use(
            http.get("http://localhost:8000/api/v1/clients/:clientId/bots", () =>
                HttpResponse.json({ botids: ["bot_new"] })
            )
        );

        await act(async () => {
            sendWsEvent("bot_created", { botid: "bot_new" });
        });

        await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("● Running"));
    });
});

describe("Bot workflow — remove flow", () => {
    beforeEach(() => {
        mockWs = createMockWs();
        vi.stubGlobal(
            "WebSocket",
            vi.fn(() => mockWs)
        );
        server.use(
            http.get("http://localhost:8000/api/v1/clients/:clientId/bots", () =>
                HttpResponse.json({ botids: ["bot_existing"] })
            )
        );
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.clearAllMocks();
    });

    it("shows Idle status after bot_removed WS event", async () => {
        render(<Bots user={botUser} />);

        await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("● Running"));

        await act(async () => {
            openWs();
        });
        await act(async () => {
            sendWsEvent("bot_removed", { botid: "bot_existing" });
        });

        await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("● Idle"));
    });
});

describe("Bot workflow — live trading toggle", () => {
    beforeEach(() => {
        mockWs = createMockWs();
        vi.stubGlobal(
            "WebSocket",
            vi.fn(() => mockWs)
        );
        server.use(
            http.get("http://localhost:8000/api/v1/clients/:clientId/bots", () =>
                HttpResponse.json({ botids: ["bot_live"] })
            )
        );
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.clearAllMocks();
    });

    it("shows live mode button after confirming live trading", async () => {
        render(<Bots user={botUser} />);

        await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("● Running"));
        await act(async () => {
            openWs();
        });

        fireEvent.click(screen.getByLabelText("Switch to live trading"));
        expect(screen.getByText("⚠ Enable Live Trading?")).toBeInTheDocument();

        await act(async () => {
            fireEvent.click(screen.getByText("⚡ Confirm Live Trading"));
        });

        expect(screen.queryByText("⚠ Enable Live Trading?")).not.toBeInTheDocument();
        expect(screen.getByLabelText("Switch to paper trading")).toBeInTheDocument();
    });

    it("stays in paper mode when user cancels live confirm", async () => {
        render(<Bots user={botUser} />);

        await waitFor(() =>
            expect(screen.getByLabelText("Switch to live trading")).toBeInTheDocument()
        );

        fireEvent.click(screen.getByLabelText("Switch to live trading"));
        fireEvent.click(screen.getByText("Cancel"));

        expect(screen.queryByText("⚠ Enable Live Trading?")).not.toBeInTheDocument();
        expect(screen.getByLabelText("Switch to live trading")).toBeInTheDocument();
    });
});

// ### Accessibility checks ###

describe("Parameters — accessibility", () => {
    it("has no accessibility violations", async () => {
        const { container } = render(<Parameters clientId={mockUser.id} />);
        await waitFor(() => screen.getByText("Binance"));
        expect(await axe(container)).toHaveNoViolations();
    });
});

describe("Indicators — accessibility", () => {
    it("has no accessibility violations", async () => {
        const { container } = render(<Indicators clientId={mockUser.id} />);
        await waitFor(() => screen.getByText("5min"));
        expect(await axe(container)).toHaveNoViolations();
    });
});
