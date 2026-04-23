import React, { useCallback, useEffect, useState } from "react";
import ConfigCheckboxPanel from "../ConfigCheckboxPanel/ConfigCheckboxPanel";
import { getDefaultParameters, getParameters, updateParameters } from "../../utils/api";
import type { ParametersConfig } from "../../utils/api";
import type { ConfigSection } from "../ConfigCheckboxPanel/ConfigCheckboxPanel";
import "./parameters.css";

const DEFAULT_STATE: ParametersConfig = { exchanges: {}, symbols: {}, strategy: "arbitrage" };

const SECTIONS: ConfigSection<ParametersConfig>[] = [
    {
        key: "exchanges",
        label: "Exchanges",
        tooltips: {
            Binance: "Binance — world's largest crypto exchange by volume",
            Okx:     "OKX — major exchange with deep liquidity on most pairs",
            Kraken:  "Kraken — established exchange known for security and EUR pairs",
        },
    },
    {
        key: "symbols",
        label: "Symbols",
        tooltips: {
            "BTC/USDT": "Bitcoin / Tether — highest liquidity trading pair",
            "ETH/USDT": "Ethereum / Tether — second largest crypto by market cap",
        },
    },
];

const STRATEGY_LABELS: Record<ParametersConfig["strategy"], string> = {
    arbitrage:     "Arbitrage — profit from price differences between exchanges",
    market_making: "Market Making — profit by posting limit orders on both sides of the spread",
};

interface ParametersProps {
    clientId: string;
}

const Parameters: React.FC<ParametersProps> = ({ clientId }) => {
    const [strategy, setStrategy] = useState<ParametersConfig["strategy"]>("arbitrage");
    const [saveStatus, setSaveStatus] = useState<"saving" | "saved" | "error" | null>(null);

    useEffect(() => {
        let cancelled = false;
        getParameters(clientId)
            .then(p => { if (!cancelled) setStrategy(p.strategy ?? "arbitrage"); })
            .catch(() =>
                getDefaultParameters()
                    .then(p => { if (!cancelled) setStrategy(p.strategy ?? "arbitrage"); })
                    .catch(() => {})
            );
        return () => { cancelled = true; };
    }, [clientId]);

    const handleStrategyChange = useCallback(
        async (e: React.ChangeEvent<HTMLSelectElement>) => {
            const next = e.target.value as ParametersConfig["strategy"];
            setStrategy(next);
            setSaveStatus("saving");
            try {
                const current = await getParameters(clientId).catch(() => DEFAULT_STATE);
                await updateParameters(clientId, { ...current, strategy: next });
                setSaveStatus("saved");
            } catch {
                setSaveStatus("error");
            } finally {
                setTimeout(() => setSaveStatus(null), 3000);
            }
        },
        [clientId]
    );

    return (
        <div className="setAndDisplayParameters">
            <div className="strategy-row">
                <label htmlFor="strategy-select">Strategy</label>
                <select
                    id="strategy-select"
                    value={strategy}
                    onChange={handleStrategyChange}
                    title={STRATEGY_LABELS[strategy]}
                >
                    {(Object.keys(STRATEGY_LABELS) as ParametersConfig["strategy"][]).map(s => (
                        <option key={s} value={s}>{s === "arbitrage" ? "Arbitrage" : "Market Making"}</option>
                    ))}
                </select>
                {saveStatus && (
                    <span role="status" aria-live="polite" className={`save-status save-status--${saveStatus}`}>
                        {saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "✓ Saved" : "✗ Error"}
                    </span>
                )}
            </div>
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
                className=""
            />
        </div>
    );
};

export default Parameters;
