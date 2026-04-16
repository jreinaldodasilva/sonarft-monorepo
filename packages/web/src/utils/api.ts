import netlifyIdentity from "netlify-identity-widget";
import { HTTP } from "./constants.js";
import parameterOptions from "./parameterOptions.json";
import indicatorOptions from "./indicatorOptions.json";

// ### Types ###

export interface ParametersConfig {
    exchanges: Record<string, boolean>;
    symbols: Record<string, boolean>;
}

export interface IndicatorsConfig {
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
    buy_exchange: string;
    buy_price: number;
    buy_value: number;
    sell_exchange: string;
    sell_price: number;
    sell_value: number;
    profit: number;
    profit_percentage: number;
}

// ### Auth helpers ###

export const getAuthToken = (): string | null => {
    const user = netlifyIdentity.currentUser() as { token?: { access_token?: string } } | null;
    return user?.token?.access_token ?? null;
};

const getAuthHeaders = (): Record<string, string> => {
    const token = getAuthToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
};

const baseHeaders: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
};

// ### Bot endpoints ###

export const getBotIds = async (clientId: string): Promise<string[]> => {
    try {
        const response = await fetch(HTTP + `/botids/${clientId}`, {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        return data.botids as string[];
    } catch (e) {
        throw e;
    }
};

export const getOrders = async (botId: string): Promise<TradeRecord[] | null> => {
    try {
        const response = await fetch(HTTP + `/bot/${botId}/orders`, {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        });
        if (!response.ok) return null;
        return await response.json() as TradeRecord[];
    } catch {
        return null;
    }
};

export const getTrades = async (botId: string): Promise<TradeRecord[] | null> => {
    try {
        const response = await fetch(HTTP + `/bot/${botId}/trades`, {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        });
        if (!response.ok) return null;
        return await response.json() as TradeRecord[];
    } catch {
        return null;
    }
};

// ### Parameters ###

export const getDefaultParameters = async (): Promise<ParametersConfig> => {
    try {
        const response = await fetch(HTTP + `/default_parameters`, {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json() as ParametersConfig;
    } catch {
        return parameterOptions as ParametersConfig;
    }
};

export const getParameters = async (clientId: string): Promise<ParametersConfig> => {
    try {
        const response = await fetch(HTTP + `/bot/get_parameters/${clientId}`, {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json() as ParametersConfig;
    } catch (e) {
        throw e;
    }
};

export const updateParameters = async (
    clientId: string,
    newParameters: ParametersConfig
): Promise<{ message: string }> => {
    try {
        const response = await fetch(HTTP + `/bot/set_parameters/${clientId}`, {
            method: "POST",
            headers: { ...baseHeaders, ...getAuthHeaders() },
            body: JSON.stringify(newParameters),
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (e) {
        throw e;
    }
};

// ### Indicators ###

export const getDefaultIndicators = async (): Promise<IndicatorsConfig> => {
    try {
        const response = await fetch(HTTP + `/default_indicators`, {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json() as IndicatorsConfig;
    } catch {
        return indicatorOptions as IndicatorsConfig;
    }
};

export const getIndicators = async (clientId: string): Promise<IndicatorsConfig> => {
    try {
        const response = await fetch(HTTP + `/bot/get_indicators/${clientId}`, {
            method: "GET",
            headers: { ...baseHeaders, ...getAuthHeaders() },
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json() as IndicatorsConfig;
    } catch (e) {
        throw e;
    }
};

export const updateIndicators = async (
    clientId: string,
    newIndicators: IndicatorsConfig
): Promise<{ message: string }> => {
    try {
        const response = await fetch(HTTP + `/bot/set_indicators/${clientId}`, {
            method: "POST",
            headers: { ...baseHeaders, ...getAuthHeaders() },
            body: JSON.stringify(newIndicators),
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (e) {
        throw e;
    }
};
