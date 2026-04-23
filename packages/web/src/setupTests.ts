import "@testing-library/jest-dom";

// MSW server — intercepts fetch calls for integration tests
import { server } from "./mocks/server";
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
