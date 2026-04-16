import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import App from "./App";

describe("App", () => {
    it("renders without crashing", async () => {
        render(<App />);
        await waitFor(() => expect(document.body).toBeTruthy());
    });

    it("renders the SonarFT logo link", async () => {
        render(<App />);
        await waitFor(() =>
            expect(screen.getByAltText("SonarFT")).toBeInTheDocument()
        );
    });

    it("renders the Sign In button when user is not authenticated", async () => {
        render(<App />);
        await waitFor(() =>
            expect(screen.getByText("Sign In")).toBeInTheDocument()
        );
    });

    it("renders the Crypto navigation link", async () => {
        render(<App />);
        await waitFor(() =>
            expect(screen.getByRole("link", { name: /crypto/i })).toBeInTheDocument()
        );
    });
});
