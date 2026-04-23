import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import App from "./App";

describe("App", () => {
    it("renders without crashing", async () => {
        render(<App />);
        await waitFor(() => expect(document.body).toBeTruthy());
    });

    it("renders the SonarFT logo", async () => {
        render(<App />);
        await waitFor(() =>
            expect(screen.getByAltText("SonarFT")).toBeInTheDocument()
        );
    });

    it("renders the Dashboard navigation link", () => {
        render(<App />);
        expect(screen.getAllByRole("link").some(l => l.textContent?.includes("Dashboard"))).toBe(true);
    });
});
