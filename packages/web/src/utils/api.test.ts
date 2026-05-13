import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import {
    getBotIds,
    getOrders,
    getTrades,
    getDefaultParameters,
    getParameters,
    updateParameters,
    getDefaultIndicators,
    getIndicators,
    updateIndicators,
    getAuthToken,
} from "./api";
import {
    mockBotIds,
    mockOrder,
    mockTrade,
    mockParameters,
    mockIndicators,
    mockResponse,
} from "../mocks/fixtures";

vi.mock("./parameterOptions.json", () => ({
    default: { exchanges: { Binance: true }, symbols: { "BTC/USDT": true } },
}));
vi.mock("./indicatorOptions.json", () => ({
    default: { periods: { "5min": true }, oscillators: {}, movingaverages: {} },
}));

beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
    vi.unstubAllGlobals();
});

// ### getAuthToken ###

describe("getAuthToken", () => {
    it("returns null when no token in sessionStorage", () => {
        sessionStorage.clear();
        expect(getAuthToken()).toBeNull();
    });

    it("returns token from sessionStorage when set", () => {
        sessionStorage.setItem("sonarft_token", "test-jwt");
        expect(getAuthToken()).toBe("test-jwt");
        sessionStorage.clear();
    });
});

// ### getBotIds ###

describe("getBotIds", () => {
    it("returns bot IDs on success", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(
            mockResponse({ botids: mockBotIds }) as unknown as Response
        );
        const result = await getBotIds("client_123");
        expect(result).toEqual(mockBotIds);
        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining("/clients/client_123/bots"),
            expect.objectContaining({ method: "GET" })
        );
    });

    it("includes Authorization header when token is in sessionStorage", async () => {
        sessionStorage.setItem("sonarft_token", "test-jwt");
        vi.mocked(fetch).mockResolvedValueOnce(
            mockResponse({ botids: mockBotIds }) as unknown as Response
        );
        await getBotIds("client_123");
        expect(fetch).toHaveBeenCalledWith(
            expect.any(String),
            expect.objectContaining({
                headers: expect.objectContaining({ Authorization: "Bearer test-jwt" }),
            })
        );
        sessionStorage.clear();
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
    it("sends PUT with parameters body and returns response", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(
            mockResponse({ message: "ok" }) as unknown as Response
        );
        const result = await updateParameters("client_123", mockParameters);
        expect(result).toEqual({ message: "ok" });
        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining("/clients/client_123/parameters"),
            expect.objectContaining({ method: "PUT", body: JSON.stringify(mockParameters) })
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
    it("sends PUT with indicators body and returns response", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(
            mockResponse({ message: "ok" }) as unknown as Response
        );
        const result = await updateIndicators("client_123", mockIndicators);
        expect(result).toEqual({ message: "ok" });
        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining("/clients/client_123/indicators"),
            expect.objectContaining({ method: "PUT", body: JSON.stringify(mockIndicators) })
        );
    });

    it("throws on HTTP error", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}, false, 500) as unknown as Response);
        await expect(updateIndicators("client_123", mockIndicators)).rejects.toThrow();
    });
});

// ### fetchWsTicket ###

import { fetchWsTicket } from "./api";

describe("fetchWsTicket", () => {
    it("returns ticket string on success", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(
            mockResponse({ ticket: "abc-ticket-123" }) as unknown as Response
        );
        expect(await fetchWsTicket()).toBe("abc-ticket-123");
        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining("/ws/ticket"),
            expect.objectContaining({ method: "POST" })
        );
    });

    it("returns null when response is not ok (e.g. 404 in dev mode)", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}, false, 404) as unknown as Response);
        expect(await fetchWsTicket()).toBeNull();
    });

    it("returns null on network failure", async () => {
        vi.mocked(fetch).mockRejectedValueOnce(new Error("Network error"));
        expect(await fetchWsTicket()).toBeNull();
    });

    it("returns null when ticket field is missing from response", async () => {
        vi.mocked(fetch).mockResolvedValueOnce(mockResponse({}) as unknown as Response);
        expect(await fetchWsTicket()).toBeNull();
    });
});
