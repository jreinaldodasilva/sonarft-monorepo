import React from "react";
import type { TradeRecord } from "../../utils/api";

interface TradeHistoryTableProps {
    rows: TradeRecord[];
}

const TradeHistoryTable: React.FC<TradeHistoryTableProps> = ({ rows = [] }) => (
    <div className="tables-container">
        <table className="tradehistory-table">
            <thead>
                <tr>
                    <th>Index</th><th>Time</th><th>Position</th><th>Symbol</th>
                    <th>Amount</th><th>Buy Exchange</th><th>Price</th><th>Value</th>
                    <th>Sell Exchange</th><th>Price</th><th>Value</th>
                    <th>Profit</th><th>Profit Perc</th>
                </tr>
            </thead>
            <tbody>
                {rows.map((row, index) => (
                    <tr key={`${row.timestamp}-${row.buy_exchange}-${index}`}>
                        <td>{index}</td>
                        <td>{row.timestamp}</td>
                        <td>{row.position}</td>
                        <td>{row.base}/{row.quote}</td>
                        <td>{row.buy_trade_amount}</td>
                        <td>{row.buy_exchange}</td>
                        <td>{row.buy_price}</td>
                        <td>{row.buy_value}</td>
                        <td>{row.sell_exchange}</td>
                        <td>{row.sell_price}</td>
                        <td>{row.sell_value}</td>
                        <td>{row.profit}</td>
                        <td>{row.profit_percentage}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    </div>
);

export default TradeHistoryTable;
