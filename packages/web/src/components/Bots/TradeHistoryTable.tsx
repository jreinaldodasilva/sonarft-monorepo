import React from "react";
import type { TradeRecord } from "../../utils/api";

interface TradeHistoryTableProps {
    rows: TradeRecord[];
    caption: string;
}

const formatDate = (ts: string): string => {
    if (!ts) return "";
    // Handle legacy MM-DD-YYYY HH:MM:SS format stored before ISO 8601 fix
    const normalized = /^\d{2}-\d{2}-\d{4}/.test(ts)
        ? ts.replace(/^(\d{2})-(\d{2})-(\d{4})/, "$3-$1-$2")
        : ts;
    const d = new Date(normalized);
    if (isNaN(d.getTime())) return ts;
    return new Intl.DateTimeFormat(undefined, {
        month: "numeric",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(d);
};

const formatCurrency = (value: number): string =>
    new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 }).format(
        value
    );

const formatPercent = (value: number): string =>
    new Intl.NumberFormat(undefined, {
        style: "percent",
        minimumFractionDigits: 3,
        maximumFractionDigits: 5,
    }).format(value);

const TradeHistoryTable: React.FC<TradeHistoryTableProps> = ({ rows = [], caption }) => (
    <div className="tables-container" aria-live="polite" aria-relevant="additions">
        <table className="tradehistory-table">
            <caption className="sr-only">{caption}</caption>
            <thead>
                <tr>
                    <th scope="col">#</th>
                    <th scope="col">Time</th>
                    <th scope="col">Position</th>
                    <th scope="col">Symbol</th>
                    <th scope="col">Amount</th>
                    <th scope="col">Buy Exchange</th>
                    <th scope="col">Price</th>
                    <th scope="col">Value</th>
                    <th scope="col">Sell Exchange</th>
                    <th scope="col">Price</th>
                    <th scope="col">Value</th>
                    <th scope="col">Profit</th>
                    <th scope="col">Profit %</th>
                </tr>
            </thead>
            <tbody>
                {rows.length === 0 ? (
                    <tr>
                        <td colSpan={13} className="tradehistory-empty">
                            No records yet
                        </td>
                    </tr>
                ) : (
                    rows.map((row, index) => (
                        <tr key={`${row.timestamp}-${row.buy_exchange}-${index}`}>
                            <td>{index + 1}</td>
                            <td>{formatDate(row.timestamp)}</td>
                            <td>{row.position}</td>
                            <td>
                                {row.base}/{row.quote}
                            </td>
                            <td>{formatCurrency(row.buy_trade_amount)}</td>
                            <td>{row.buy_exchange}</td>
                            <td>{formatCurrency(row.buy_price)}</td>
                            <td>{formatCurrency(row.buy_value)}</td>
                            <td>{row.sell_exchange}</td>
                            <td>{formatCurrency(row.sell_price)}</td>
                            <td>{formatCurrency(row.sell_value)}</td>
                            <td className={row.profit >= 0 ? "profit-positive" : "profit-negative"}>
                                {row.profit >= 0 ? "+" : ""}
                                {formatCurrency(row.profit)}
                            </td>
                            <td
                                className={
                                    row.profit_percentage >= 0
                                        ? "profit-positive"
                                        : "profit-negative"
                                }
                            >
                                {row.profit_percentage >= 0 ? "+" : ""}
                                {formatPercent(row.profit_percentage)}
                            </td>
                        </tr>
                    ))
                )}
            </tbody>
        </table>
    </div>
);

export default React.memo(TradeHistoryTable);
