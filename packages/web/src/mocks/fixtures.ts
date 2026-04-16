import type { TradeRecord, ParametersConfig, IndicatorsConfig } from "../utils/api";

export interface MockUser {
    id: string;
    email: string;
    token: { access_token: string };
}

export const mockUser: MockUser = {
    id: "user_abc123",
    email: "test@example.com",
    token: { access_token: "mock-jwt-token" },
};

export const mockBotIds: string[] = ["bot_001", "bot_002"];

export const mockOrder: TradeRecord = {
    timestamp: "2025-01-01T00:00:00Z",
    position: "LONG",
    base: "BTC",
    quote: "USDT",
    buy_trade_amount: 1,
    buy_exchange: "binance",
    buy_price: 43000,
    buy_value: 43000,
    sell_exchange: "okx",
    sell_price: 43050,
    sell_value: 43050,
    profit: 50,
    profit_percentage: 0.00116,
};

export const mockTrade: TradeRecord = {
    timestamp: "2025-01-01T00:01:00Z",
    position: "SHORT",
    base: "ETH",
    quote: "USDT",
    buy_trade_amount: 1,
    buy_exchange: "binance",
    buy_price: 2200,
    buy_value: 2200,
    sell_exchange: "okx",
    sell_price: 2210,
    sell_value: 2210,
    profit: 10,
    profit_percentage: 0.00454,
};

export const mockParameters: ParametersConfig = {
    exchanges: { Binance: true, Okx: false, Kraken: false },
    symbols: { "BTC/USDT": true, "ETH/USDT": false },
};

export const mockIndicators: IndicatorsConfig = {
    periods: { "5min": true, "15min": false },
    oscillators: {
        "Relative Strength Index (14)": true,
        "MACD Level (12, 26)": true,
    },
    movingaverages: {
        "Exponential Moving Average (10)": true,
        "Simple Moving Average (10)": false,
    },
};

export const mockResponse = (
    body: unknown,
    ok = true,
    status = 200
): { ok: boolean; status: number; json: () => Promise<unknown> } => ({
    ok,
    status,
    json: async () => body,
});
