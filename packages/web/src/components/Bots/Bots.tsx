import React from "react";
import useBots, { BotStatus } from "../../hooks/useBots";
import type { AuthContextValue } from "../../hooks/AuthProvider";
import BotControls from "./BotControls";
import BotConsole from "./BotConsole";
import TradeHistoryTable from "./TradeHistoryTable";
import ProfitChart from "../Charts/ProfitChart";
import "./bots.css";

interface BotsProps {
    user: AuthContextValue["user"] & { id: string };
}

const STATUS_LABELS: Record<string, { text: string; cls: string }> = {
    [BotStatus.IDLE]:    { text: "● Idle",    cls: "bot-status--idle" },
    [BotStatus.RUNNING]: { text: "● Running", cls: "bot-status--running" },
    [BotStatus.ERROR]:   { text: "● Error",   cls: "bot-status--error" },
};

const Bots: React.FC<BotsProps> = ({ user }) => {
    const {
        logs, botIds, botState, botStatus, isSimulating,
        orders, trades, selectedBotId, setSelectedBotId,
        isLoading, fetchError, wsOpen, wsError,
        handleCreate, handleRemove, handleToggleSimulation,
    } = useBots(user.id);

    const statusLabel = STATUS_LABELS[botStatus];

    return (
        <div className="bots-container">
            {isLoading && <div className="bots-loading">Loading...</div>}
            {fetchError && <div className="bots-ws-error">⚠ {fetchError}</div>}
            {wsError && <div className="bots-ws-error">⚠ {wsError} — reconnecting...</div>}

            <div className="bots">
                <h2>
                    Bots
                    <button
                        className={`mode-toggle ${isSimulating ? "mode-toggle--paper" : "mode-toggle--live"}`}
                        onClick={handleToggleSimulation}
                        title={isSimulating ? "Switch to live trading" : "Switch to paper trading"}
                    >
                        {isSimulating ? "📝 Paper" : "⚡ Live"}
                    </button>
                    <span className={`ws-status ${wsOpen ? "ws-status--open" : "ws-status--closed"}`}>
                        {wsOpen ? "● Connected" : "○ Disconnected"}
                    </span>
                    <span className={`bot-status ${statusLabel.cls}`}>
                        {statusLabel.text}
                    </span>
                </h2>
                <BotControls
                    botIds={botIds}
                    botState={botState}
                    selectedBotId={selectedBotId}
                    wsOpen={wsOpen}
                    onSelectBot={setSelectedBotId}
                    onCreate={handleCreate}
                    onRemove={handleRemove}
                />
                <BotConsole logs={logs} />
            </div>

            <div className="history">
                <h2>Order History</h2>
                <TradeHistoryTable rows={orders} />
                <h2>Trade History</h2>
                <ProfitChart trades={trades} />
                <TradeHistoryTable rows={trades} />
            </div>
        </div>
    );
};

export default Bots;
