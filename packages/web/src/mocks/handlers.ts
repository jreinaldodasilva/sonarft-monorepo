import { http, HttpResponse } from "msw";
import { mockBotIds, mockOrder, mockTrade, mockParameters, mockIndicators } from "./fixtures";

const API = "http://localhost:8000/api/v1";

export const handlers = [
    // WS ticket — returns null so useBots falls back to bare WS URL
    http.post(`${API}/ws/ticket`, () => HttpResponse.json({}, { status: 404 })),
    // Canonical bot endpoints
    http.get(`${API}/clients/:clientId/bots`, () => HttpResponse.json({ botids: mockBotIds })),
    http.get(`${API}/clients/:clientId/bots/:botId/orders`, () => HttpResponse.json([mockOrder])),
    http.get(`${API}/clients/:clientId/bots/:botId/trades`, () => HttpResponse.json([mockTrade])),
    // Default parameter/indicator endpoints (no client_id — unchanged)
    http.get(`${API}/parameters/defaults`, () => HttpResponse.json(mockParameters)),
    http.get(`${API}/indicators/defaults`, () => HttpResponse.json(mockIndicators)),
    // Canonical config endpoints
    http.get(`${API}/clients/:clientId/parameters`, () => HttpResponse.json(mockParameters)),
    http.put(`${API}/clients/:clientId/parameters`, () => HttpResponse.json({ message: "ok" })),
    http.get(`${API}/clients/:clientId/indicators`, () => HttpResponse.json(mockIndicators)),
    http.put(`${API}/clients/:clientId/indicators`, () => HttpResponse.json({ message: "ok" })),
];
