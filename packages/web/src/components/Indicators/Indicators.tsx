import React from "react";
import "./indicators.css";
import { getDefaultIndicators, getIndicators, updateIndicators } from "../../utils/api";
import type { IndicatorsConfig } from "../../utils/api";
import useConfigCheckboxes from "../../hooks/useConfigCheckboxes";

const SAVE_MESSAGES: Record<string, string> = {
    saving: "Saving...", saved: "✓ Saved", error: "✗ Error — try again",
};

const DEFAULT_STATE: IndicatorsConfig = { periods: {}, oscillators: {}, movingaverages: {} };
const STATE_KEYS: (keyof IndicatorsConfig)[] = ["periods", "oscillators", "movingaverages"];

const TOOLTIPS: Record<string, Record<string, string>> = {
    periods: {
        "5min":  "5-minute candles — high frequency, more noise, faster signals",
        "15min": "15-minute candles — balanced between noise and signal quality",
        "30min": "30-minute candles — medium-term trend analysis",
        "45min": "45-minute candles — less common; between 30m and 1h",
        "1h":    "1-hour candles — lower noise, stronger trend signals",
    },
    oscillators: {
        "Relative Strength Index (14)":       "RSI (14) — measures momentum; ≥70 overbought, ≤30 oversold",
        "Stochastic %K (14, 3, 3)":           "Stochastic Oscillator — compares closing price to price range; signals reversals",
        "MACD Level (12, 26)":                "MACD — difference between 12 and 26-period EMAs; trend and momentum indicator",
        "Stochastic RSI Fast (3, 3, 14, 14)": "StochRSI — applies Stochastic formula to RSI values; more sensitive than RSI alone",
        "Momentum (10)":                      "Momentum (10) — rate of price change over 10 periods",
        "Awesome Oscillator":                 "Awesome Oscillator — difference between 5 and 34-period simple moving averages",
    },
    movingaverages: {
        "Exponential Moving Average (10)":    "EMA (10) — weighted average giving more importance to recent prices; fast response",
        "Simple Moving Average (10)":         "SMA (10) — equal-weight average of last 10 periods; smoother but slower",
        "Exponential Moving Average (30)":    "EMA (30) — medium-term trend; slower than EMA(10) but less noise",
        "Simple Moving Average (30)":         "SMA (30) — medium-term equal-weight average; common support/resistance reference",
        "Ichimoku Base Line (9, 26, 52, 26)": "Ichimoku Kijun-sen — midpoint of 26-period high/low; key support/resistance level",
    },
};

interface IndicatorsProps {
    clientId: string;
}

const Indicators: React.FC<IndicatorsProps> = ({ clientId }) => {
    const { config, saveStatus, handleCheckboxChange, handleSave } = useConfigCheckboxes({
        storageKey: "indicatorsState",
        defaultState: DEFAULT_STATE,
        fetchFn: getIndicators,
        defaultFn: getDefaultIndicators,
        updateFn: updateIndicators,
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
        <div className="setAndDisplayIndicators">
            <h2>Indicators</h2>
            <form>
                <div className="checkbox-group label">
                    <h3>Periods</h3>
                    <ul>{renderCheckboxes("periods")}</ul>
                    <h3>Oscillators</h3>
                    <ul>{renderCheckboxes("oscillators")}</ul>
                    <h3>Moving Averages</h3>
                    <ul>{renderCheckboxes("movingaverages")}</ul>
                    <div className="save-row">
                        <button type="button" onClick={handleSave} disabled={saveStatus === "saving"}>
                            Set bot indicators
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

export default Indicators;
