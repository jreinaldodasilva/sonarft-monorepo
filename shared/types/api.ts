/**
 * SonarFT Shared API Types
 * Single source of truth for the API contract between packages/api and packages/web.
 * Any change here must be reflected in packages/api/src/models/schemas.py.
 *
 * Canonical API paths (v1):
 *   GET/POST  /api/v1/clients/{clientId}/bots
 *   POST      /api/v1/clients/{clientId}/bots/{botId}/run
 *   POST      /api/v1/clients/{clientId}/bots/{botId}/stop
 *   DELETE    /api/v1/clients/{clientId}/bots/{botId}
 *   GET       /api/v1/clients/{clientId}/bots/{botId}/orders
 *   GET       /api/v1/clients/{clientId}/bots/{botId}/trades
 *   GET/PUT   /api/v1/clients/{clientId}/parameters
 *   GET/PUT   /api/v1/clients/{clientId}/indicators
 *   POST      /api/v1/ws/ticket  (exchange JWT for WS ticket)
 *   WS        /api/v1/ws/{clientId}?ticket=
 *
 * Legacy paths (deprecated, still functional):
 *   GET/POST  /api/v1/bots?client_id=
 *   GET/PUT   /api/v1/parameters?client_id=
 *   GET/PUT   /api/v1/indicators?client_id=
 */

// ### Core domain types ###

export interface TradeRecord {
    timestamp: string;
    position: string;
    base: string;
    quote: string;
    buy_exchange: string;
    sell_exchange: string;
    buy_price: number;
    sell_price: number;
    buy_trade_amount: number;
    sell_trade_amount: number;
    executed_amount: number;
    buy_value: number;
    sell_value: number;
    buy_fee_rate: number;
    sell_fee_rate: number;
    buy_fee_base: number;
    buy_fee_quote: number;
    sell_fee_quote: number;
    profit: number;
    profit_percentage: number;
}

export interface ParametersConfig {
    exchanges: Record<string, boolean>;
    symbols: Record<string, boolean>;
    strategy: "arbitrage" | "market_making";
}

export interface IndicatorsConfig {
    periods: Record<string, boolean>;
    oscillators: Record<string, boolean>;
    movingaverages: Record<string, boolean>;
}

// ### REST response types ###

export interface BotListResponse {
    botids: string[];
}

export interface BotCreateResponse {
    botid: string;
}

export interface MessageResponse {
    message: string;
}

export interface HealthResponse {
    status: string;
    version: string;
}

export interface WsTicketResponse {
    ticket: string;
    ttl_seconds: number;
}

// ### WebSocket event types ###

export type WsEventType =
    | "connected"
    | "log"
    | "bot_created"
    | "bot_removed"
    | "order_success"
    | "trade_success"
    | "error"
    | "ping";

export interface WsBaseEvent {
    type: WsEventType;
    ts: number;
}

export interface WsConnectedEvent extends WsBaseEvent {
    type: "connected";
    client_id: string;
}

export interface WsLogEvent extends WsBaseEvent {
    type: "log";
    // Expanded to match Python logging levels (DEBUG and CRITICAL added).
    level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";
    message: string;
}

export interface WsBotCreatedEvent extends WsBaseEvent {
    type: "bot_created";
    botid: string | null;
}

export interface WsBotRemovedEvent extends WsBaseEvent {
    type: "bot_removed";
    botid: string | null;
}

export interface WsOrderSuccessEvent extends WsBaseEvent {
    type: "order_success";
}

export interface WsTradeSuccessEvent extends WsBaseEvent {
    type: "trade_success";
}

export interface WsErrorEvent extends WsBaseEvent {
    type: "error";
    message: string;
}

export interface WsPingEvent extends WsBaseEvent {
    type: "ping";
}

export type WsEvent =
    | WsConnectedEvent
    | WsLogEvent
    | WsBotCreatedEvent
    | WsBotRemovedEvent
    | WsOrderSuccessEvent
    | WsTradeSuccessEvent
    | WsErrorEvent
    | WsPingEvent;

// ### WebSocket client → server commands ###

export interface WsCreateCommand {
    type: "keypress";
    key: "create";
}

export interface WsRunCommand {
    type: "keypress";
    key: "run";
    botid: string;
}

export interface WsRemoveCommand {
    type: "keypress";
    key: "remove";
    botid: string;
}

export interface WsSetSimulationCommand {
    type: "keypress";
    key: "set_simulation";
    value: boolean;
}

export type WsCommand =
    | WsCreateCommand
    | WsRunCommand
    | WsRemoveCommand
    | WsSetSimulationCommand;
