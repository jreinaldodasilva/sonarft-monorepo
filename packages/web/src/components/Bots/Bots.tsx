import React, { useState } from "react";
import useBots, { BotStatus } from "../../hooks/useBots";
import type { AppUser } from "../../hooks/AuthProvider";
import BotControls from "./BotControls";
import BotConsole from "./BotConsole";
import TradeHistoryTable from "./TradeHistoryTable";
import ProfitChart from "../Charts/ProfitChart";
import "./bots.css";

interface BotsProps {
    user: AppUser;
}

const STATUS_LABELS: Record<string, { text: string; cls: string }> = {
    [BotStatus.IDLE]:    { text: "● Idle",    cls: "bot-status--idle" },
    [BotStatus.RUNNING]: { text: "● Running", cls: "bot-status--running" },
    [BotStatus.ERROR]:   { text: "● Error",   cls: "bot-status--error" },
};

const LIFECYCLE_LABELS: Record<string, { text: string; cls: string }> = {
    idle:     { text: "● Idle",     cls: "bot-status--idle" },
    creating: { text: "● Creating", cls: "bot-status--running" },
    running:  { text: "● Running",  cls: "bot-status--running" },
    stopping: { text: "● Stopping", cls: "bot-status--stopped" },
    stopped:  { text: "● Stopped",  cls: "bot-status--stopped" },
    removing: { text: "● Removing", cls: "bot-status--idle" },
    error:    { text: "● Error",    cls: "bot-status--error" },
};

const Bots: React.FC<BotsProps> = ({ user }) => {
    const {
        logs, botIds, botState, botStatus, lifecycle, isSimulating,
        orders, trades, selectedBotId, setSelectedBotId,
        isLoading, fetchError, wsOpen, wsError,
        handleCreate, handleStop, handleRemove, handleToggleSimulation,
    } = useBots(user.id);

    const [showLiveConfirm, setShowLiveConfirm] = useState(false);
    const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);

    const statusLabel = LIFECYCLE_LABELS[lifecycle] ?? STATUS_LABELS[botStatus];

    const handleModeToggleClick = () => {
        if (isSimulating) {
            // Switching paper → live: require explicit confirmation
            setShowLiveConfirm(true);
        } else {
            // Switching live → paper: safe, no confirmation needed
            handleToggleSimulation();
        }
    };

    const handleConfirmLive = () => {
        setShowLiveConfirm(false);
        handleToggleSimulation();
    };

    return (
        <div>
            {isLoading && <div className="bots-loading">Loading...</div>}
            {fetchError && <div className="bots-ws-error" role="alert">⚠ {fetchError}</div>}
            {wsError && <div className="bots-ws-error" role="alert">⚠ {wsError} — reconnecting...</div>}

            {/* Live trading confirmation modal */}
            {showLiveConfirm && (
                <div className="live-confirm-overlay" role="dialog" aria-modal="true" aria-labelledby="live-confirm-title">
                    <div className="live-confirm-box">
                        <h2 id="live-confirm-title">⚠ Enable Live Trading?</h2>
                        <p>
                            You are switching to <strong>live trading mode</strong>.
                            Real orders will be placed on exchanges using real funds.
                        </p>
                        <p className="live-confirm-warning">
                            Make sure your exchange API keys are configured and your
                            parameters are correct before proceeding.
                        </p>
                        <div className="live-confirm-actions">
                            <button className="live-confirm-cancel" onClick={() => setShowLiveConfirm(false)}>Cancel</button>
                            <button className="live-confirm-proceed" onClick={handleConfirmLive}>⚡ Confirm Live Trading</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Remove bot confirmation modal */}
            {showRemoveConfirm && (
                <div className="live-confirm-overlay" role="dialog" aria-modal="true" aria-labelledby="remove-confirm-title">
                    <div className="live-confirm-box">
                        <h2 id="remove-confirm-title">Remove Bot?</h2>
                        <p>This will stop and permanently remove bot <strong>{selectedBotId?.slice(0, 8)}…</strong></p>
                        <p className="live-confirm-warning">Any in-flight orders will be cancelled. Trade history is preserved.</p>
                        <div className="live-confirm-actions">
                            <button className="live-confirm-cancel" onClick={() => setShowRemoveConfirm(false)}>Cancel</button>
                            <button className="live-confirm-proceed" onClick={() => { setShowRemoveConfirm(false); handleRemove(); }}>✕ Remove Bot</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Bot controls card */}
            <div className="bots-panel">
                <div className="bots-panel-header">
                    <h2>Bots</h2>
                    <span
                        className={`bot-status ${statusLabel.cls}`}
                        role="status"
                        aria-live="polite"
                    >
                        {statusLabel.text}
                    </span>
                    <span
                        className={`ws-status ${wsOpen ? "ws-status--open" : "ws-status--closed"}`}
                        aria-label={wsOpen ? "WebSocket connected" : "WebSocket disconnected"}
                    >
                        {wsOpen ? "● Connected" : "○ Disconnected"}
                    </span>
                    <button
                        className={`mode-toggle ${isSimulating ? "mode-toggle--paper" : "mode-toggle--live"}`}
                        onClick={handleModeToggleClick}
                        aria-label={isSimulating ? "Switch to live trading" : "Switch to paper trading"}
                        title={isSimulating ? "Switch to live trading" : "Switch to paper trading"}
                    >
                        {isSimulating ? "📝 Paper" : "⚡ Live"}
                    </button>
                </div>
                <BotControls
                    botIds={botIds}
                    botState={botState}
                    selectedBotId={selectedBotId}
                    wsOpen={wsOpen}
                    onSelectBot={setSelectedBotId}
                    onCreate={handleCreate}
                    onStop={handleStop}
                    onRemove={() => setShowRemoveConfirm(true)}
                />
                <BotConsole logs={logs} />
            </div>

            {/* History card */}
            <div className="bots-panel history">
                <h2>Order History</h2>
                <TradeHistoryTable rows={orders} caption="Order History" />
                <h2 style={{ marginTop: 12 }}>Trade History</h2>
                <ProfitChart trades={trades} />
                <TradeHistoryTable rows={trades} caption="Trade History" />
            </div>
        </div>
    );
};

export default Bots;
