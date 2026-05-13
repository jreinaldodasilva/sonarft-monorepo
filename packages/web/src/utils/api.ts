import { HTTP } from "./constants.js";
import parameterOptions from "./parameterOptions.json";
import indicatorOptions from "./indicatorOptions.json";

// ### Types ###

export interface ParametersConfig {
    version?: number;
    exchanges: Record<string, boolean>;
    symbols: Record<string, boolean>;
    strategy: "arbitrage" | "market_making";
}

export interface IndicatorsConfig {
    version?: number;
    [key: string]: Record<string, boolean> | number | undefined;
    periods: Record<string, boolean>;
    oscillators: Record<string, boolean>;
    movingaverages: Record<string, boolean>;
}

export interface TradeRecord {
    timestamp: string;
    position: string;
    base: string;
    quote: string;
    buy_trade_amount: number;
    sell_trade_amount: number;
    executed_amount: number;
    buy_exchange: string;
    buy_price: number;
    buy_value: number;
    buy_fee_rate: number;
    buy_fee_base: number;
    buy_fee_quote: number;
    sell_exchange: string;
    sell_price: number;
    sell_value: number;
    sell_fee_rate: number;
    sell_fee_quote: number;
    profit: number;
    profit_percentage: number;
}

// ### Auth helpers ###

/** Returns the Bearer token from sessionStorage if set, otherwise null. */
export const getAuthToken = (): string | null => sessionStorage.getItem("sonarft_token");

const getAuthHeaders = (): Record<string, string> => {
    const token = getAuthToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
};

const baseHeaders: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
};

/**
 * Register a callback invoked whenever any API call receives a 401.
 * Used by AuthProvider to trigger logout and show a session-expired message.
 */
let _onUnauthorized: (() => void) | null = null;
export const setUnauthorizedHandler = (handler: () => void): void => {
    _onUnauthorized = handler;
};

// ### Fetch with timeout ###

const FETCH_TIMEOUT_MS = 15_000;

/**
 * Wraps fetch with a 15-second AbortController timeout.
 * Throws a plain Error with a user-readable message on timeout so callers
 * can surface it in the UI without special-casing DOMException.
 * Invokes the registered unauthorized handler on 401 responses.
 */
const fetchWithTimeout = (url: string, options: RequestInit): Promise<Response> => {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    return fetch(url, { ...options, signal: controller.signal })
        .then((response) => {
            if (response.status === 401) {
                _onUnauthorized?.();
            }
            return response;
        })
        .catch((err: unknown) => {
            if (err instanceof DOMException && err.name === "AbortError") {
                throw new Error("Request timed out — check server status");
            }
            throw err;
        })
        .finally(() => clearTimeout(id));
};

// ### WebSocket ticket ###

/**
 * Exchange a valid Bearer token for a short-lived single-use WebSocket ticket.
 * The ticket is passed as ?ticket= on the WS URL, keeping the JWT out of
 * server access logs and browser history.
 * @returns The ticket string, or null if the endpoint is unavailable (dev mode / no auth).
 */
export const fetchWsTicket = async (): Promise<string | null> => {
    try {
        const response = await fetchWithTimeout(HTTP + "/ws/ticket", {
            method: "POST",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        });
        if (!response.ok) return null;
        const data = (await response.json()) as { ticket: string };
        return data.ticket ?? null;
    } catch {
        return null;
    }
};

// ### Bot endpoints ###

/**
 * List all bot IDs for a client.
 * @param clientId - The authenticated client identifier.
 * @returns Array of bot ID strings.
 * @throws Error on HTTP error or network failure.
 */
export const getBotIds = async (clientId: string): Promise<string[]> => {
    const response = await fetchWithTimeout(
        HTTP + `/clients/${encodeURIComponent(clientId)}/bots`,
        {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        }
    );
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    return data.botids as string[];
};

/**
 * Get order history for a bot.
 * @param botId - The bot identifier.
 * @param clientId - The authenticated client identifier.
 * @returns Array of TradeRecord, or null on HTTP error or network failure.
 */
export const getOrders = async (botId: string, clientId: string): Promise<TradeRecord[] | null> => {
    try {
        const response = await fetchWithTimeout(
            HTTP + `/clients/${encodeURIComponent(clientId)}/bots/${botId}/orders`,
            {
                method: "GET",
                headers: { ...baseHeaders, ...getAuthHeaders() },
            }
        );
        if (!response.ok) return null;
        return (await response.json()) as TradeRecord[];
    } catch {
        return null;
    }
};

/**
 * Get trade history for a bot.
 * @param botId - The bot identifier.
 * @param clientId - The authenticated client identifier.
 * @returns Array of TradeRecord, or null on HTTP error or network failure.
 */
export const getTrades = async (botId: string, clientId: string): Promise<TradeRecord[] | null> => {
    try {
        const response = await fetchWithTimeout(
            HTTP + `/clients/${encodeURIComponent(clientId)}/bots/${botId}/trades`,
            {
                method: "GET",
                headers: { ...baseHeaders, ...getAuthHeaders() },
            }
        );
        if (!response.ok) return null;
        return (await response.json()) as TradeRecord[];
    } catch {
        return null;
    }
};

// ### Parameters ###

/**
 * Get the default trading parameters (server-side defaults).
 * Falls back to bundled parameterOptions.json on HTTP error or network failure.
 * @returns ParametersConfig with default exchange/symbol/strategy selections.
 */
export const getDefaultParameters = async (): Promise<ParametersConfig> => {
    try {
        const response = await fetchWithTimeout(HTTP + `/parameters/defaults`, {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return (await response.json()) as ParametersConfig;
    } catch {
        return parameterOptions as ParametersConfig;
    }
};

/**
 * Get per-client trading parameters.
 * @param clientId - The authenticated client identifier.
 * @returns ParametersConfig for the client.
 * @throws Error on HTTP error or network failure.
 */
export const getParameters = async (clientId: string): Promise<ParametersConfig> => {
    const response = await fetchWithTimeout(
        HTTP + `/clients/${encodeURIComponent(clientId)}/parameters`,
        {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        }
    );
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return (await response.json()) as ParametersConfig;
};

/**
 * Update per-client trading parameters.
 * @param clientId - The authenticated client identifier.
 * @param newParameters - The full ParametersConfig to persist.
 * @returns Server confirmation message.
 * @throws Error on HTTP error or network failure.
 */
export const updateParameters = async (
    clientId: string,
    newParameters: ParametersConfig
): Promise<{ message: string }> => {
    const response = await fetchWithTimeout(
        HTTP + `/clients/${encodeURIComponent(clientId)}/parameters`,
        {
            method: "PUT",
            headers: { ...baseHeaders, ...getAuthHeaders() },
            body: JSON.stringify(newParameters),
        }
    );
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
};

// ### Indicators ###

/**
 * Get the default indicator settings (server-side defaults).
 * Falls back to bundled indicatorOptions.json on HTTP error or network failure.
 * @returns IndicatorsConfig with default period/oscillator/MA selections.
 */
export const getDefaultIndicators = async (): Promise<IndicatorsConfig> => {
    try {
        const response = await fetchWithTimeout(HTTP + `/indicators/defaults`, {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return (await response.json()) as IndicatorsConfig;
    } catch {
        return indicatorOptions as IndicatorsConfig;
    }
};

/**
 * Get per-client indicator settings.
 * @param clientId - The authenticated client identifier.
 * @returns IndicatorsConfig for the client.
 * @throws Error on HTTP error or network failure.
 */
export const getIndicators = async (clientId: string): Promise<IndicatorsConfig> => {
    const response = await fetchWithTimeout(
        HTTP + `/clients/${encodeURIComponent(clientId)}/indicators`,
        {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        }
    );
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return (await response.json()) as IndicatorsConfig;
};

/**
 * Update per-client indicator settings.
 * @param clientId - The authenticated client identifier.
 * @param newIndicators - The full IndicatorsConfig to persist.
 * @returns Server confirmation message.
 * @throws Error on HTTP error or network failure.
 */
export const updateIndicators = async (
    clientId: string,
    newIndicators: IndicatorsConfig
): Promise<{ message: string }> => {
    const response = await fetchWithTimeout(
        HTTP + `/clients/${encodeURIComponent(clientId)}/indicators`,
        {
            method: "PUT",
            headers: { ...baseHeaders, ...getAuthHeaders() },
            body: JSON.stringify(newIndicators),
        }
    );
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
};
