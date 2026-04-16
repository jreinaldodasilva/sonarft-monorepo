import { vi, describe, it, expect, beforeEach } from "vitest";
import { fetchAllOrders, fetchAllTrades } from "./helpers";
import { getOrders, getTrades } from "./api";
import { mockOrder, mockTrade } from "../mocks/fixtures";

vi.mock("./api");

beforeEach(() => {
    vi.clearAllMocks();
});

// ### fetchAllOrders ###

describe("fetchAllOrders", () => {
    it("aggregates orders from all bot IDs", async () => {
        vi.mocked(getOrders)
            .mockResolvedValueOnce([mockOrder])
            .mockResolvedValueOnce([{ ...mockOrder, buy_exchange: "okx" }]);

        const result = await fetchAllOrders(["bot_001", "bot_002"]);
        expect(result).toHaveLength(2);
        expect(getOrders).toHaveBeenCalledTimes(2);
        expect(getOrders).toHaveBeenCalledWith("bot_001");
        expect(getOrders).toHaveBeenCalledWith("bot_002");
    });

    it("fetches all bots in parallel (Promise.all)", async () => {
        const callOrder: string[] = [];
        vi.mocked(getOrders).mockImplementation((id: string) => {
            callOrder.push(id);
            return Promise.resolve([mockOrder]);
        });
        await fetchAllOrders(["bot_001", "bot_002", "bot_003"]);
        expect(callOrder).toHaveLength(3);
        expect(getOrders).toHaveBeenCalledTimes(3);
    });

    it("skips null responses (failed fetches)", async () => {
        vi.mocked(getOrders)
            .mockResolvedValueOnce([mockOrder])
            .mockResolvedValueOnce(null);

        const result = await fetchAllOrders(["bot_001", "bot_002"]);
        expect(result).toHaveLength(1);
    });

    it("returns empty array for empty botIds", async () => {
        const result = await fetchAllOrders([]);
        expect(result).toEqual([]);
        expect(getOrders).not.toHaveBeenCalled();
    });

    it("returns empty array when all fetches return null", async () => {
        vi.mocked(getOrders).mockResolvedValue(null);
        const result = await fetchAllOrders(["bot_001", "bot_002"]);
        expect(result).toEqual([]);
    });
});

// ### fetchAllTrades ###

describe("fetchAllTrades", () => {
    it("aggregates trades from all bot IDs", async () => {
        vi.mocked(getTrades)
            .mockResolvedValueOnce([mockTrade])
            .mockResolvedValueOnce([{ ...mockTrade, buy_exchange: "okx" }]);

        const result = await fetchAllTrades(["bot_001", "bot_002"]);
        expect(result).toHaveLength(2);
        expect(getTrades).toHaveBeenCalledTimes(2);
    });

    it("fetches all bots in parallel (Promise.all)", async () => {
        vi.mocked(getTrades).mockResolvedValue([mockTrade]);
        await fetchAllTrades(["bot_001", "bot_002", "bot_003"]);
        expect(getTrades).toHaveBeenCalledTimes(3);
    });

    it("skips null responses", async () => {
        vi.mocked(getTrades)
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce([mockTrade]);

        const result = await fetchAllTrades(["bot_001", "bot_002"]);
        expect(result).toHaveLength(1);
    });

    it("returns empty array for empty botIds", async () => {
        const result = await fetchAllTrades([]);
        expect(result).toEqual([]);
        expect(getTrades).not.toHaveBeenCalled();
    });
});
