export const BOT_CREATED_MESSAGE = "Bot CREATED!";
export const BOT_REMOVED_MESSAGE = "Bot REMOVED!";
export const ORDER_SUCCESS = "Order: Success";
export const TRADE_SUCCESS = "Trade: Success";

// Vite exposes env vars as import.meta.env.VITE_*
// Falls back to localhost for development without a .env file
export const HTTP: string =
    (import.meta.env.VITE_API_URL as string) ?? "http://localhost:8000/api/v1";

export const WS: string =
    (import.meta.env.VITE_WS_URL as string) ?? "ws://localhost:8000/api/v1/ws";
