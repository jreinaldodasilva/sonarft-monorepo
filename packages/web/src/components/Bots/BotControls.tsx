import React from "react";
import { BotState } from "../../hooks/useBots";

interface BotControlsProps {
    botIds: string[];
    botState: number;
    selectedBotId: string | null;
    wsOpen: boolean;
    onSelectBot: (id: string) => void;
    onCreate: () => void;
    onStop: () => void;
    onRemove: () => void;
}

const BotControls: React.FC<BotControlsProps> = ({
    botIds,
    botState,
    selectedBotId,
    wsOpen,
    onSelectBot,
    onCreate,
    onStop,
    onRemove,
}) => {
    const hasBots = botState === BotState.CREATED;
    const canAct = hasBots && selectedBotId !== null && wsOpen;

    return (
        <div className="bot-controls">
            <button
                onClick={onCreate}
                disabled={hasBots || !wsOpen}
                className={hasBots || !wsOpen ? "btn-disabled" : ""}
            >
                + Create Bot
            </button>

            <select
                onChange={(e) => onSelectBot(e.target.value)}
                value={selectedBotId ?? ""}
                aria-label="Active Bot"
                disabled={botIds.length === 0}
            >
                {botIds.length === 0 ? (
                    <option value="">No bots</option>
                ) : (
                    botIds.map((botId) => (
                        <option key={botId} value={botId} title={botId}>
                            {botId.slice(0, 8)}…
                        </option>
                    ))
                )}
            </select>

            <button
                className={`bot-stop-btn${!canAct ? " btn-disabled" : ""}`}
                onClick={onStop}
                disabled={!canAct}
                title={selectedBotId ? `Stop bot ${selectedBotId}` : "No bot selected"}
            >
                ■ Stop
            </button>

            <button
                className={`bot-remove-btn${!canAct ? " btn-disabled" : ""}`}
                onClick={onRemove}
                disabled={!canAct}
                title={selectedBotId ? `Remove bot ${selectedBotId}` : "No bot selected"}
            >
                ✕ Remove
            </button>
        </div>
    );
};

export default React.memo(BotControls);
