import React from "react";
import { BotState } from "../../hooks/useBots";

interface BotControlsProps {
    botIds: string[];
    botState: number;
    selectedBotId: string | null;
    wsOpen: boolean;
    onSelectBot: (id: string) => void;
    onCreate: () => void;
    onRemove: () => void;
}

const BotControls: React.FC<BotControlsProps> = ({
    botIds, botState, selectedBotId, wsOpen, onSelectBot, onCreate, onRemove,
}) => (
    <div className="bot-controls">
        <button
            onClick={onCreate}
            disabled={botState !== BotState.REMOVED}
            className={botState !== BotState.REMOVED ? "btn-disabled" : ""}
        >
            + Create Bot
        </button>
        <select
            onChange={(e) => onSelectBot(e.target.value)}
            value={selectedBotId ?? ""}
            aria-label="Active Bot"
        >
            {botIds.length === 0
                ? <option value="">No bots</option>
                : botIds.map((botId) => (
                    <option key={botId} value={botId} title={botId}>
                        {botId.slice(0, 8)}…
                    </option>
                ))
            }
        </select>
        <button
            className={`bot-remove-btn ${
                botState !== BotState.REMOVED || selectedBotId === null || !wsOpen
                    ? "btn-disabled" : ""
            }`}
            onClick={onRemove}
            disabled={botState !== BotState.REMOVED || selectedBotId === null || !wsOpen}
            title={selectedBotId ? `Remove bot ${selectedBotId}` : "No bot selected"}
        >
            Remove
        </button>
    </div>
);

export default React.memo(BotControls);
