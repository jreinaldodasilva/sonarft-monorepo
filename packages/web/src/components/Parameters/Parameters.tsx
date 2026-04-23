import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getDefaultParameters, getParameters, updateParameters } from "../../utils/api";
import type { ParametersConfig } from "../../utils/api";
import "./parameters.css";

const SAVE_FEEDBACK_MS = 3000;

const DEFAULT_STATE: ParametersConfig = { exchanges: {}, symbols: {}, strategy: "market_making" };

const EXCHANGE_TOOLTIPS: Record<string, string> = {
    Binance: "Binance — world's largest crypto exchange by volume",
    Okx:     "OKX — major exchange with deep liquidity on most pairs",
    Kraken:  "Kraken — established exchange known for security and EUR pairs",
};

const SYMBOL_TOOLTIPS: Record<string, string> = {
    "BTC/USDT": "Bitcoin / Tether — highest liquidity trading pair",
    "ETH/USDT": "Ethereum / Tether — second largest crypto by market cap",
};

const STRATEGY_LABELS: Record<ParametersConfig["strategy"], string> = {
    arbitrage:     "Arbitrage — profit from price differences between exchanges",
    market_making: "Market Making — profit by posting limit orders on both sides of the spread",
};

interface ParametersProps {
    clientId: string;
}

const Parameters: React.FC<ParametersProps> = ({ clientId }) => {
    const [config, setConfig] = useState<ParametersConfig>(DEFAULT_STATE);
    const [saveStatus, setSaveStatus] = useState<"saving" | "saved" | "error" | null>(null);
    const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Load: server → localStorage → bundled defaults
    useEffect(() => {
        let cancelled = false;

        const load = async () => {
            try {
                const data = await getParameters(clientId);
                if (!cancelled) { setConfig(data); localStorage.setItem("parametersState", JSON.stringify(data)); return; }
            } catch { /* fall through */ }
            if (cancelled) return;
            try {
                const stored = JSON.parse(localStorage.getItem("parametersState") ?? "null") as ParametersConfig | null;
                if (!cancelled && stored) { setConfig(stored); return; }
            } catch { /* fall through */ }
            if (cancelled) return;
            try {
                const data = await getDefaultParameters();
                if (!cancelled) setConfig(data);
            } catch { /* all sources failed */ }
        };

        load();
        return () => { cancelled = true; };
    }, [clientId]);

    const scheduleStatus = useCallback((status: "saved" | "error") => {
        setSaveStatus(status);
        if (saveTimer.current) clearTimeout(saveTimer.current);
        saveTimer.current = setTimeout(() => setSaveStatus(null), SAVE_FEEDBACK_MS);
    }, []);

    const handleCheckboxChange = useCallback((e: React.ChangeEvent<HTMLInputElement>, section: "exchanges" | "symbols") => {
        const { name, checked } = e.target;
        setConfig(prev => {
            const next = { ...prev, [section]: { ...prev[section], [name]: checked } };
            localStorage.setItem("parametersState", JSON.stringify(next));
            return next;
        });
    }, []);

    const handleStrategyChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
        const next = e.target.value as ParametersConfig["strategy"];
        setConfig(prev => {
            const updated = { ...prev, strategy: next };
            localStorage.setItem("parametersState", JSON.stringify(updated));
            return updated;
        });
    }, []);

    const handleSave = useCallback(async () => {
        setSaveStatus("saving");
        try {
            await updateParameters(clientId, config);
            scheduleStatus("saved");
        } catch {
            scheduleStatus("error");
        }
    }, [clientId, config, scheduleStatus]);

    const exchangeEntries = useMemo(() => Object.entries(config.exchanges), [config.exchanges]);
    const symbolEntries  = useMemo(() => Object.entries(config.symbols),   [config.symbols]);

    return (
        <div className="setAndDisplayParameters">
            <h2>Parameters</h2>
            <div className="checkbox-group label">
                <div className="strategy-row">
                    <label htmlFor="strategy-select">Strategy</label>
                    <select
                        id="strategy-select"
                        value={config.strategy}
                        onChange={handleStrategyChange}
                        title={STRATEGY_LABELS[config.strategy]}
                    >
                        <option value="arbitrage">Arbitrage</option>
                        <option value="market_making">Market Making</option>
                    </select>
                </div>

                <h3>Exchanges</h3>
                <ul>
                    {exchangeEntries.map(([name, checked]) => (
                        <li key={name}>
                            <label title={EXCHANGE_TOOLTIPS[name] ?? name}>
                                <input
                                    type="checkbox"
                                    name={name}
                                    checked={checked}
                                    onChange={e => handleCheckboxChange(e, "exchanges")}
                                />
                                {name}
                            </label>
                        </li>
                    ))}
                </ul>

                <h3>Symbols</h3>
                <ul>
                    {symbolEntries.map(([name, checked]) => (
                        <li key={name}>
                            <label title={SYMBOL_TOOLTIPS[name] ?? name}>
                                <input
                                    type="checkbox"
                                    name={name}
                                    checked={checked}
                                    onChange={e => handleCheckboxChange(e, "symbols")}
                                />
                                {name}
                            </label>
                        </li>
                    ))}
                </ul>

                <div className="save-row">
                    <button type="button" onClick={handleSave} disabled={saveStatus === "saving"}>
                        Set bot parameters
                    </button>
                    {saveStatus && (
                        <span role="status" aria-live="polite" className={`save-status save-status--${saveStatus}`}>
                            {saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "✓ Saved" : "✗ Error — try again"}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Parameters;
