import { vi, describe, it, expect, beforeEach } from "vitest";
import {
    getBotIds, getOrders, getTrades,
    getDefaultParameters, getParameters, updateParameters,
    getDefaultIndicators, getIndicators, updateIndicators,
    getAuthToken,
} from "./api";
import {
    mockBotIds, mockOrder, mockTrade,
    mockParameters, mockIndicators, mockResponse,
} from "../mocks/fixtures";

global.fetch = vi.fn() as unknown as typeof fetch;

vi.mock("./parameterOptions.json", () => ({
    default: { exchanges: { Binance: true }, symbols: { "BTC/USDT": true } },
}));
vi.mock("./indicatorOptions.json", () => ({
    default: { periods: { "5min": true }, oscillators: {}, movingaverages: {} },
}));

beforeEach(() => {
    vi.mocked(fetch).mockClear();
});

// ### getAuthToken ###

describe("getAuthToken", () => {
    it("returns null when no user is logged in", () => {
        expect(getAuthToken()).toBeNull();
    });
});

// ### getBotIds ###

describe("getBotIds", () => {
    it("returns bot IDs on success", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({ botids: mockBotIds }) as unknown as Response);
        const result = await getBotIds("client_123");
        expect(result).toEqual(mockBotIds);
        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining("/botids/client_123"),
            expect.objectContaining({ method: "GET" })
        );
    });

    it("includes Authorization header when token is available", async () => {
        const netlifyIdentity = await import("netlify-identity-widget");
        vi.mocked(netlifyIdentity.default.currentUser).mockReturnValueOnce(
            { token: { access_token: "test-jwt" } } as unknown as ReturnType<typeof netlifyIdentity.default.currentUser>
        );
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({ botids: mockBotIds }) as unknown as Response);
        await getBotIds("client_123");
        expect(fetch).toHaveBeenCalledWith(
            expect.any(String),
            expect.objectContaining({
                headers: expect.objectContaining({ Authorization: "Bearer test-jwt" }),
            })
        );
    });

    it("throws on HTTP error", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}, false, 500) as unknown as Response);
        await expect(getBotIds("client_123")).rejects.toThrow("HTTP error! status: 500");
    });

    it("throws on network failure", async () => {
        vi.mocked(fetch).mockRejectedValueOnce(new Error("Network error"));
        await expect(getBotIds("client_123")).rejects.toThrow("Network error");
    });
});

// ### getOrders ###

describe("getOrders", () => {
    it("returns order data on success", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse([mockOrder]) as unknown as Response);
        expect(await getOrders("bot_001")).toEqual([mockOrder]);
    });

    it("returns null when response is not ok", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}, false, 404) as unknown as Response);
        expect(await getOrders("bot_001")).toBeNull();
    });

    it("returns null on network failure", async () => {
        vi.mocked(fetch).mockRejectedValueOnce(new Error("Network error"));
        expect(await getOrders("bot_001")).toBeNull();
    });
});

// ### getTrades ###

describe("getTrades", () => {
    it("returns trade data on success", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse([mockTrade]) as unknown as Response);
        expect(await getTrades("bot_001")).toEqual([mockTrade]);
    });

    it("returns null when response is not ok", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}, false, 404) as unknown as Response);
        expect(await getTrades("bot_001")).toBeNull();
    });

    it("returns null on network failure", async () => {
        vi.mocked(fetch).mockRejectedValueOnce(new Error("Network error"));
        expect(await getTrades("bot_001")).toBeNull();
    });
});

// ### getDefaultParameters ###

describe("getDefaultParameters", () => {
    it("returns server data on success", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse(mockParameters) as unknown as Response);
        expect(await getDefaultParameters()).toEqual(mockParameters);
    });

    it("falls back to local JSON on HTTP error", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}, false, 500) as unknown as Response);
        const result = await getDefaultParameters();
        expect(result).toHaveProperty("exchanges");
        expect(result).toHaveProperty("symbols");
    });

    it("falls back to local JSON on network failure", async () => {
        vi.mocked(fetch).mockRejectedValueOnce(new Error("Network error"));
        expect(await getDefaultParameters()).toHaveProperty("exchanges");
    });
});

// ### getParameters ###

describe("getParameters", () => {
    it("returns parameters on success", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse(mockParameters) as unknown as Response);
        expect(await getParameters("client_123")).toEqual(mockParameters);
    });

    it("throws on HTTP error", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}, false, 404) as unknown as Response);
        await expect(getParameters("client_123")).rejects.toThrow("HTTP error! status: 404");
    });

    it("throws on network failure", async () => {
        vi.mocked(fetch).mockRejectedValueOnce(new Error("Network error"));
        await expect(getParameters("client_123")).rejects.toThrow("Network error");
    });
});

// ### updateParameters ###

describe("updateParameters", () => {
    it("sends POST with parameters body and returns response", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({ message: "ok" }) as unknown as Response);
        const result = await updateParameters("client_123", mockParameters);
        expect(result).toEqual({ message: "ok" });
        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining("/bot/set_parameters/client_123"),
            expect.objectContaining({ method: "POST", body: JSON.stringify(mockParameters) })
        );
    });

    it("throws on HTTP error", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}, false, 500) as unknown as Response);
        await expect(updateParameters("client_123", mockParameters)).rejects.toThrow();
    });
});

// ### getDefaultIndicators ###

describe("getDefaultIndicators", () => {
    it("returns server data on success", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse(mockIndicators) as unknown as Response);
        expect(await getDefaultIndicators()).toEqual(mockIndicators);
    });

    it("falls back to local JSON on HTTP error", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}, false, 500) as unknown as Response);
        expect(await getDefaultIndicators()).toHaveProperty("periods");
    });

    it("falls back to local JSON on network failure", async () => {
        vi.mocked(fetch).mockRejectedValueOnce(new Error("Network error"));
        expect(await getDefaultIndicators()).toHaveProperty("periods");
    });
});

// ### getIndicators ###

describe("getIndicators", () => {
    it("returns indicators on success", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse(mockIndicators) as unknown as Response);
        expect(await getIndicators("client_123")).toEqual(mockIndicators);
    });

    it("throws on HTTP error", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}, false, 404) as unknown as Response);
        await expect(getIndicators("client_123")).rejects.toThrow("HTTP error! status: 404");
    });
});

// ### updateIndicators ###

describe("updateIndicators", () => {
    it("sends POST with indicators body and returns response", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({ message: "ok" }) as unknown as Response);
        const result = await updateIndicators("client_123", mockIndicators);
        expect(result).toEqual({ message: "ok" });
        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining("/bot/set_indicators/client_123"),
            expect.objectContaining({ method: "POST", body: JSON.stringify(mockIndicators) })
        );
    });

    it("throws on HTTP error", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}, false, 500) as unknown as Response);
        await expect(updateIndicators("client_123", mockIndicators)).rejects.toThrow();
    });
});
