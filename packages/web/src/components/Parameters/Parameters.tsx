import React from "react";
import ConfigCheckboxPanel from "../ConfigCheckboxPanel/ConfigCheckboxPanel";
import { getDefaultParameters, getParameters, updateParameters } from "../../utils/api";
import type { ParametersConfig } from "../../utils/api";
import type { ConfigSection } from "../ConfigCheckboxPanel/ConfigCheckboxPanel";
import "./parameters.css";

const DEFAULT_STATE: ParametersConfig = { exchanges: {}, symbols: {}, strategy: "market_making" };

const EXCHANGE_TOOLTIPS: Record<string, string> = {
    Binance: "Binance — world's largest crypto exchange by volume",
    Okx: "OKX — major exchange with deep liquidity on most pairs",
    Kraken: "Kraken — established exchange known for security and EUR pairs",
};

const SYMBOL_TOOLTIPS: Record<string, string> = {
    "BTC/USDT": "Bitcoin / Tether — highest liquidity trading pair",
    "ETH/USDT": "Ethereum / Tether — second largest crypto by market cap",
};

const STRATEGY_LABELS: Record<ParametersConfig["strategy"], string> = {
    arbitrage: "Arbitrage — profit from price differences between exchanges",
    market_making: "Market Making — profit by posting limit orders on both sides of the spread",
};

const SECTIONS: ConfigSection<ParametersConfig>[] = [
    { key: "exchanges", label: "Exchanges", tooltips: EXCHANGE_TOOLTIPS },
    { key: "symbols", label: "Symbols", tooltips: SYMBOL_TOOLTIPS },
];

interface ParametersProps {
    clientId: string;
}

const Parameters: React.FC<ParametersProps> = ({ clientId }) => (
    <ConfigCheckboxPanel
        title="Parameters"
        clientId={clientId}
        storageKey="parametersState"
        defaultState={DEFAULT_STATE}
        sections={SECTIONS}
        fetchFn={getParameters}
        defaultFn={getDefaultParameters}
        updateFn={updateParameters}
        saveLabel="Set bot parameters"
        className="setAndDisplayParameters"
        headerSlot={(config, setConfig) => (
            <div className="strategy-row">
                <label htmlFor="strategy-select">Strategy</label>
                <select
                    id="strategy-select"
                    value={config.strategy}
                    onChange={(e) => {
                        const next = e.target.value as ParametersConfig["strategy"];
                        setConfig((prev) => {
                            const updated = { ...prev, strategy: next };
                            localStorage.setItem("parametersState", JSON.stringify(updated));
                            return updated;
                        });
                    }}
                    title={STRATEGY_LABELS[config.strategy]}
                >
                    <option value="arbitrage">Arbitrage</option>
                    <option value="market_making">Market Making</option>
                </select>
            </div>
        )}
    />
);

export default Parameters;
