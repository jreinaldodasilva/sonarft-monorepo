import React from "react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Bots from "./Bots";
import type { AppUser } from "../../hooks/AuthProvider";

// ### Mock useBots — control all returned state from outside ###

const mockHandleCreate = vi.fn();
const mockHandleStop = vi.fn();
const mockHandleRemove = vi.fn();
const mockHandleToggleSim = vi.fn();
const mockSetSelectedBotId = vi.fn();

const defaultUseBots = {
    logs: [],
    botIds: [],
    botState: 1, // BotState.REMOVED
    botStatus: "idle" as const,
    lifecycle: "idle" as const,
    isSimulating: true,
    orders: [],
    trades: [],
    selectedBotId: null,
    setSelectedBotId: mockSetSelectedBotId,
    isLoading: false,
    fetchError: null,
    wsOpen: true,
    wsError: null,
    handleCreate: mockHandleCreate,
    handleStop: mockHandleStop,
    handleRemove: mockHandleRemove,
    handleToggleSimulation: mockHandleToggleSim,
};

vi.mock("../../hooks/useBots", () => ({
    default: vi.fn(),
    BotState: { CREATED: 0, REMOVED: 1 },
    BotStatus: { IDLE: "idle", RUNNING: "running", ERROR: "error" },
}));

import useBots from "../../hooks/useBots";

const mockUser: AppUser = { id: "test_client", email: "test@example.com" };

const renderBots = (overrides: Partial<typeof defaultUseBots> = {}) => {
    vi.mocked(useBots).mockReturnValue({ ...defaultUseBots, ...overrides } as ReturnType<
        typeof useBots
    >);
    return render(<Bots user={mockUser} />);
};

beforeEach(() => {
    vi.clearAllMocks();
});

// ### Status badges ###

describe("Bots — status badge", () => {
    it("shows Idle badge when lifecycle is idle", () => {
        renderBots({ lifecycle: "idle" });
        expect(screen.getByRole("status")).toHaveTextContent("● Idle");
    });

    it("shows Running badge when lifecycle is running", () => {
        renderBots({ lifecycle: "running" });
        expect(screen.getByRole("status")).toHaveTextContent("● Running");
    });

    it("shows Stopped badge when lifecycle is stopped", () => {
        renderBots({ lifecycle: "stopped" });
        expect(screen.getByRole("status")).toHaveTextContent("● Stopped");
    });

    it("shows Stopping badge when lifecycle is stopping", () => {
        renderBots({ lifecycle: "stopping" });
        expect(screen.getByRole("status")).toHaveTextContent("● Stopping");
    });

    it("shows Error badge when lifecycle is error", () => {
        renderBots({ lifecycle: "error" });
        expect(screen.getByRole("status")).toHaveTextContent("● Error");
    });
});

// ### Connection state ###

describe("Bots — WebSocket connection indicator", () => {
    it("shows Connected when wsOpen is true", () => {
        renderBots({ wsOpen: true });
        expect(screen.getByLabelText("WebSocket connected")).toBeInTheDocument();
    });

    it("shows Disconnected when wsOpen is false", () => {
        renderBots({ wsOpen: false });
        expect(screen.getByLabelText("WebSocket disconnected")).toBeInTheDocument();
    });
});

// ### Error banners ###

describe("Bots — error banners", () => {
    it("shows fetchError alert banner when fetchError is set", () => {
        renderBots({ fetchError: "Could not load bots — is the server running?" });
        const alerts = screen.getAllByRole("alert");
        expect(alerts.some((a) => a.textContent?.includes("Could not load bots"))).toBe(true);
    });

    it("shows wsError alert banner when wsError is set", () => {
        renderBots({ wsError: "WebSocket connection error — check server status" });
        const alerts = screen.getAllByRole("alert");
        expect(alerts.some((a) => a.textContent?.includes("WebSocket connection error"))).toBe(
            true
        );
    });

    it("shows loading indicator when isLoading is true", () => {
        renderBots({ isLoading: true });
        expect(screen.getByText("Loading...")).toBeInTheDocument();
    });
});

// ### Live trading modal ###

describe("Bots — live trading modal", () => {
    it("shows live confirm modal when switching paper → live", () => {
        renderBots({ isSimulating: true });
        fireEvent.click(screen.getByLabelText("Switch to live trading"));
        expect(screen.getByRole("dialog")).toBeInTheDocument();
        expect(screen.getByText("⚠ Enable Live Trading?")).toBeInTheDocument();
    });

    it("calls handleToggleSimulation after confirming live mode", () => {
        renderBots({ isSimulating: true });
        fireEvent.click(screen.getByLabelText("Switch to live trading"));
        fireEvent.click(screen.getByText("⚡ Confirm Live Trading"));
        expect(mockHandleToggleSim).toHaveBeenCalledTimes(1);
    });

    it("does not call handleToggleSimulation when user cancels live confirm", () => {
        renderBots({ isSimulating: true });
        fireEvent.click(screen.getByLabelText("Switch to live trading"));
        fireEvent.click(screen.getByText("Cancel"));
        expect(mockHandleToggleSim).not.toHaveBeenCalled();
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("switches live → paper immediately without modal", () => {
        renderBots({ isSimulating: false });
        fireEvent.click(screen.getByLabelText("Switch to paper trading"));
        expect(mockHandleToggleSim).toHaveBeenCalledTimes(1);
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
});

// ### Remove bot modal ###

describe("Bots — remove bot modal", () => {
    it("shows remove confirm modal when clicking Remove", () => {
        renderBots({
            lifecycle: "running",
            botState: 0, // BotState.CREATED
            botIds: ["bot_abc123"],
            selectedBotId: "bot_abc123",
            wsOpen: true,
        });
        fireEvent.click(screen.getByTitle("Remove bot bot_abc123"));
        expect(screen.getByRole("dialog")).toBeInTheDocument();
        expect(screen.getByText("Remove Bot?")).toBeInTheDocument();
    });

    it("calls handleRemove after confirming removal", () => {
        renderBots({
            lifecycle: "running",
            botState: 0,
            botIds: ["bot_abc123"],
            selectedBotId: "bot_abc123",
            wsOpen: true,
        });
        fireEvent.click(screen.getByTitle("Remove bot bot_abc123"));
        fireEvent.click(screen.getByText("✕ Remove Bot"));
        expect(mockHandleRemove).toHaveBeenCalledTimes(1);
    });

    it("does not call handleRemove when user cancels", () => {
        renderBots({
            lifecycle: "running",
            botState: 0,
            botIds: ["bot_abc123"],
            selectedBotId: "bot_abc123",
            wsOpen: true,
        });
        fireEvent.click(screen.getByTitle("Remove bot bot_abc123"));
        fireEvent.click(screen.getByText("Cancel"));
        expect(mockHandleRemove).not.toHaveBeenCalled();
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
});
