import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock netlify-identity-widget — required for any test that renders App or AuthProvider
vi.mock("netlify-identity-widget", () => ({
    default: {
        init: vi.fn(),
        on: vi.fn(),
        off: vi.fn(),
        open: vi.fn(),
        logout: vi.fn(),
        currentUser: vi.fn(() => null),
    },
}));

// MSW server — intercepts fetch calls for integration tests
import { server } from "./mocks/server";
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
