import React from "react";
import type { TradeRecord } from "../../utils/api";

interface TradeHistoryTableProps {
    rows: TradeRecord[];
    caption: string;
}

const formatDate = (ts: string): string => {
    if (!ts) return "";
    return new Intl.DateTimeFormat(undefined, {
        month: "numeric", day: "numeric",
        hour: "2-digit", minute: "2-digit",
    }).format(new Date(ts));
};

const formatCurrency = (value: number): string =>
    new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 }).format(value);

const formatPercent = (value: number): string =>
    new Intl.NumberFormat(undefined, { style: "percent", minimumFractionDigits: 3, maximumFractionDigits: 5 }).format(value);

const TradeHistoryTable: React.FC<TradeHistoryTableProps> = ({ rows = [], caption }) => (
    <div className="tables-container" aria-live="polite" aria-relevant="additions">
        <table className="tradehistory-table">
            <caption className="sr-only">{caption}</caption>
            <thead>
                <tr>
                    <th scope="col">#</th><th scope="col">Time</th><th scope="col">Position</th><th scope="col">Symbol</th>
                    <th scope="col">Amount</th><th scope="col">Buy Exchange</th><th scope="col">Price</th><th scope="col">Value</th>
                    <th scope="col">Sell Exchange</th><th scope="col">Price</th><th scope="col">Value</th>
                    <th scope="col">Profit</th><th scope="col">Profit %</th>
                </tr>
            </thead>
            <tbody>
                {rows.map((row, index) => (
                    <tr key={`${row.timestamp}-${row.buy_exchange}-${index}`}>
                        <td>{index + 1}</td>
                        <td>{formatDate(row.timestamp)}</td>
                        <td>{row.position}</td>
                        <td>{row.base}/{row.quote}</td>
                        <td>{formatCurrency(row.buy_trade_amount)}</td>
                        <td>{row.buy_exchange}</td>
                        <td>{formatCurrency(row.buy_price)}</td>
                        <td>{formatCurrency(row.buy_value)}</td>
                        <td>{row.sell_exchange}</td>
                        <td>{formatCurrency(row.sell_price)}</td>
                        <td>{formatCurrency(row.sell_value)}</td>
                        <td>{formatCurrency(row.profit)}</td>
                        <td>{formatPercent(row.profit_percentage)}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    </div>
);

export default React.memo(TradeHistoryTable);
