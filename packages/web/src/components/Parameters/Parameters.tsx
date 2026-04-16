import React from "react";
import "./parameters.css";
import { getDefaultParameters, getParameters, updateParameters } from "../../utils/api";
import type { ParametersConfig } from "../../utils/api";
import useConfigCheckboxes from "../../hooks/useConfigCheckboxes";

const SAVE_MESSAGES: Record<string, string> = {
    saving: "Saving...", saved: "✓ Saved", error: "✗ Error — try again",
};

const DEFAULT_STATE: ParametersConfig = { exchanges: {}, symbols: {} };
const STATE_KEYS: (keyof ParametersConfig)[] = ["exchanges", "symbols"];

const TOOLTIPS: Record<string, Record<string, string>> = {
    exchanges: {
        Binance: "Binance — world's largest crypto exchange by volume",
        Okx:     "OKX — major exchange with deep liquidity on most pairs",
        Kraken:  "Kraken — established exchange known for security and EUR pairs",
    },
    symbols: {
        "BTC/USDT": "Bitcoin / Tether — highest liquidity trading pair",
        "ETH/USDT": "Ethereum / Tether — second largest crypto by market cap",
    },
};

interface ParametersProps {
    clientId: string;
}

const Parameters: React.FC<ParametersProps> = ({ clientId }) => {
    const { config, saveStatus, handleCheckboxChange, handleSave } = useConfigCheckboxes({
        storageKey: "parametersState",
        defaultState: DEFAULT_STATE,
        fetchFn: getParameters,
        defaultFn: getDefaultParameters,
        updateFn: updateParameters,
        stateKeys: STATE_KEYS,
        clientId,
    });

    const renderCheckboxes = (category: string): React.ReactNode => {
        const options = (config as Record<string, Record<string, boolean>>)[category];
        if (!options) return <div>Error: Invalid category</div>;
        const tips = TOOLTIPS[category] ?? {};
        return Object.keys(options).map((item) => (
            <li key={item}>
                <label title={tips[item] ?? item}>
                    <input
                        type="checkbox"
                        name={item}
                        checked={options[item] ?? false}
                        onChange={(e) => handleCheckboxChange(e, category)}
                    />
                    {item}
                </label>
            </li>
        ));
    };

    return (
        <div className="setAndDisplayParameters">
            <h2>Parameters</h2>
            <form>
                <div className="checkbox-group label">
                    <h3>Exchanges</h3>
                    <ul>{renderCheckboxes("exchanges")}</ul>
                    <h3>Symbols</h3>
                    <ul>{renderCheckboxes("symbols")}</ul>
                    <div className="save-row">
                        <button type="button" onClick={handleSave} disabled={saveStatus === "saving"}>
                            Set bot parameters
                        </button>
                        {saveStatus && (
                            <span className={`save-status save-status--${saveStatus}`}>
                                {SAVE_MESSAGES[saveStatus]}
                            </span>
                        )}
                    </div>
                </div>
            </form>
        </div>
    );
};

export default Parameters;
