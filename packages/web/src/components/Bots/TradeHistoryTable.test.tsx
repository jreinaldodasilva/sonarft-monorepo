import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TradeHistoryTable from "./TradeHistoryTable";
import { mockOrder } from "../../mocks/fixtures";
import type { TradeRecord } from "../../utils/api";

describe("TradeHistoryTable", () => {
    it("renders table headers", () => {
        render(<TradeHistoryTable rows={[]} />);
        expect(screen.getByText("Buy Exchange")).toBeInTheDocument();
        expect(screen.getByText("Sell Exchange")).toBeInTheDocument();
        expect(screen.getByText("Profit")).toBeInTheDocument();
    });

    it("renders a row for each entry", () => {
        const rows: TradeRecord[] = [mockOrder, { ...mockOrder, buy_exchange: "okx" }];
        render(<TradeHistoryTable rows={rows} />);
        expect(screen.getAllByText("binance").length).toBeGreaterThanOrEqual(1);
    });

    it("renders empty tbody when rows is empty", () => {
        const { container } = render(<TradeHistoryTable rows={[]} />);
        expect(container.querySelectorAll("tbody tr")).toHaveLength(0);
    });

    it("renders empty tbody when rows defaults", () => {
        const { container } = render(<TradeHistoryTable rows={[]} />);
        expect(container.querySelectorAll("tbody tr")).toHaveLength(0);
    });

    it("renders symbol as base/quote", () => {
        render(<TradeHistoryTable rows={[mockOrder]} />);
        expect(screen.getByText("BTC/USDT")).toBeInTheDocument();
    });
});
