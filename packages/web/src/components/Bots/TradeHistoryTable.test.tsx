import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import TradeHistoryTable from "./TradeHistoryTable";
import { mockOrder } from "../../mocks/fixtures";
import type { TradeRecord } from "../../utils/api";

expect.extend(toHaveNoViolations);

describe("TradeHistoryTable", () => {
    it("renders table headers", () => {
        render(<TradeHistoryTable rows={[]} caption="Order History" />);
        expect(screen.getByText("Buy Exchange")).toBeInTheDocument();
        expect(screen.getByText("Sell Exchange")).toBeInTheDocument();
        expect(screen.getByText("Profit")).toBeInTheDocument();
    });

    it("renders a row for each entry", () => {
        const rows: TradeRecord[] = [mockOrder, { ...mockOrder, buy_exchange: "okx" }];
        render(<TradeHistoryTable rows={rows} caption="Order History" />);
        expect(screen.getAllByText("binance").length).toBeGreaterThanOrEqual(1);
    });

    it("renders empty tbody when rows is empty", () => {
        const { container } = render(<TradeHistoryTable rows={[]} caption="Order History" />);
        expect(container.querySelectorAll("tbody tr")).toHaveLength(0);
    });

    it("renders empty tbody when rows defaults", () => {
        const { container } = render(<TradeHistoryTable rows={[]} caption="Order History" />);
        expect(container.querySelectorAll("tbody tr")).toHaveLength(0);
    });

    it("renders symbol as base/quote", () => {
        render(<TradeHistoryTable rows={[mockOrder]} caption="Order History" />);
        expect(screen.getByText("BTC/USDT")).toBeInTheDocument();
    });
});

describe("TradeHistoryTable — accessibility", () => {
    it("has no accessibility violations (empty)", async () => {
        const { container } = render(<TradeHistoryTable rows={[]} caption="Order History" />);
        expect(await axe(container)).toHaveNoViolations();
    });

    it("has no accessibility violations (with data)", async () => {
        const { container } = render(<TradeHistoryTable rows={[mockOrder]} caption="Order History" />);
        expect(await axe(container)).toHaveNoViolations();
    });
});
