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
    <ul>
        <button
            onClick={onCreate}
            disabled={botState !== BotState.REMOVED}
            className={botState !== BotState.REMOVED ? "btn-disabled" : ""}
        >
            Create New Bot
        </button>
        <select
            onChange={(e) => onSelectBot(e.target.value)}
            value={selectedBotId ?? ""}
            aria-label="Active Bot"
        >
            {botIds.map((botId) => (
                <option key={botId} value={botId}>{botId}</option>
            ))}
        </select>
        <button
            onClick={onRemove}
            disabled={botState !== BotState.REMOVED || selectedBotId === null || !wsOpen}
            className={
                botState !== BotState.REMOVED || selectedBotId === null || !wsOpen
                    ? "btn-disabled" : ""
            }
        >
            Remove Bot {selectedBotId}
        </button>
    </ul>
);

export default BotControls;
