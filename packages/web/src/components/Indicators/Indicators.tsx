import React from "react";
import ConfigCheckboxPanel from "../ConfigCheckboxPanel/ConfigCheckboxPanel";
import { getDefaultIndicators, getIndicators, updateIndicators } from "../../utils/api";
import type { IndicatorsConfig } from "../../utils/api";
import type { ConfigSection } from "../ConfigCheckboxPanel/ConfigCheckboxPanel";
import "./indicators.css";

const DEFAULT_STATE: IndicatorsConfig = { periods: {}, oscillators: {}, movingaverages: {} };

const SECTIONS: ConfigSection<IndicatorsConfig>[] = [
    {
        key: "periods",
        label: "Periods",
        tooltips: {
            "5min": "5-minute candles — high frequency, more noise, faster signals",
            "15min": "15-minute candles — balanced between noise and signal quality",
            "30min": "30-minute candles — medium-term trend analysis",
            "45min": "45-minute candles — less common; between 30m and 1h",
            "1h": "1-hour candles — lower noise, stronger trend signals",
        },
    },
    {
        key: "oscillators",
        label: "Oscillators",
        tooltips: {
            "Relative Strength Index (14)":
                "RSI (14) — measures momentum; ≥70 overbought, ≤30 oversold",
            "Stochastic %K (14, 3, 3)":
                "Stochastic Oscillator — compares closing price to price range; signals reversals",
            "MACD Level (12, 26)":
                "MACD — difference between 12 and 26-period EMAs; trend and momentum indicator",
            "Stochastic RSI Fast (3, 3, 14, 14)":
                "StochRSI — applies Stochastic formula to RSI values; more sensitive than RSI alone",
            "Momentum (10)": "Momentum (10) — rate of price change over 10 periods",
            "Awesome Oscillator":
                "Awesome Oscillator — difference between 5 and 34-period simple moving averages",
        },
    },
    {
        key: "movingaverages",
        label: "Moving Averages",
        tooltips: {
            "Exponential Moving Average (10)":
                "EMA (10) — weighted average giving more importance to recent prices; fast response",
            "Simple Moving Average (10)":
                "SMA (10) — equal-weight average of last 10 periods; smoother but slower",
            "Exponential Moving Average (30)":
                "EMA (30) — medium-term trend; slower than EMA(10) but less noise",
            "Simple Moving Average (30)":
                "SMA (30) — medium-term equal-weight average; common support/resistance reference",
            "Ichimoku Base Line (9, 26, 52, 26)":
                "Ichimoku Kijun-sen — midpoint of 26-period high/low; key support/resistance level",
        },
    },
];

interface IndicatorsProps {
    clientId: string;
}

const Indicators: React.FC<IndicatorsProps> = ({ clientId }) => (
    <ConfigCheckboxPanel
        title="Indicators"
        clientId={clientId}
        storageKey="indicatorsState"
        defaultState={DEFAULT_STATE}
        sections={SECTIONS}
        fetchFn={getIndicators}
        defaultFn={getDefaultIndicators}
        updateFn={updateIndicators}
        saveLabel="Set bot indicators"
        className="setAndDisplayIndicators"
    />
);

export default Indicators;
