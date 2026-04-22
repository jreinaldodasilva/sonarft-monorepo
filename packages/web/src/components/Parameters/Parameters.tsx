import React from "react";
import ConfigCheckboxPanel from "../ConfigCheckboxPanel/ConfigCheckboxPanel";
import { getDefaultParameters, getParameters, updateParameters } from "../../utils/api";
import type { ParametersConfig } from "../../utils/api";
import type { ConfigSection } from "../ConfigCheckboxPanel/ConfigCheckboxPanel";
import "./parameters.css";

const DEFAULT_STATE: ParametersConfig = { exchanges: {}, symbols: {} };

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
    />
);

export default Parameters;
