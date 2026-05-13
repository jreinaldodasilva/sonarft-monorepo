import { http, HttpResponse } from "msw";
import {
    mockBotIds,
    mockOrder,
    mockTrade,
    mockParameters,
    mockIndicators,
} from "./fixtures";

const API = "http://localhost:8000/api/v1";

export const handlers = [
    // WS ticket — returns null so useBots falls back to bare WS URL
    http.post(`${API}/ws/ticket`, () =>
        HttpResponse.json({}, { status: 404 })
    ),
    http.get(`${API}/bots`, () =>
        HttpResponse.json({ botids: mockBotIds })
    ),
    http.get(`${API}/bots/:botId/orders`, () =>
        HttpResponse.json([mockOrder])
    ),
    http.get(`${API}/bots/:botId/trades`, () =>
        HttpResponse.json([mockTrade])
    ),
    http.get(`${API}/parameters/defaults`, () =>
        HttpResponse.json(mockParameters)
    ),
    http.get(`${API}/parameters`, () =>
        HttpResponse.json(mockParameters)
    ),
    http.put(`${API}/parameters`, () =>
        HttpResponse.json({ message: "ok" })
    ),
    http.get(`${API}/indicators/defaults`, () =>
        HttpResponse.json(mockIndicators)
    ),
    http.get(`${API}/indicators`, () =>
        HttpResponse.json(mockIndicators)
    ),
    http.put(`${API}/indicators`, () =>
        HttpResponse.json({ message: "ok" })
    ),
];
