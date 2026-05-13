import React, { useCallback, useMemo } from "react";
import useConfigCheckboxes from "../../hooks/useConfigCheckboxes";
import "./configpanel.css";

type ConfigState = Record<string, Record<string, boolean> | string | number | undefined>;

export interface ConfigSection<T extends ConfigState> {
    key: keyof T;
    label: string;
    tooltips?: Record<string, string>;
}

interface ConfigCheckboxPanelProps<T extends ConfigState> {
    title: string;
    clientId: string;
    storageKey: string;
    defaultState: T;
    sections: ConfigSection<T>[];
    fetchFn: (clientId: string) => Promise<T>;
    defaultFn: () => Promise<T>;
    updateFn: (clientId: string, state: T) => Promise<unknown>;
    saveLabel: string;
    className: string;
    /** Optional slot rendered above the checkbox sections — receives live config and a setter. */
    headerSlot?: (config: T, setConfig: React.Dispatch<React.SetStateAction<T>>) => React.ReactNode;
}

const SAVE_MESSAGES: Record<string, string> = {
    saving: "Saving...",
    saved: "✓ Saved",
    error: "✗ Error — try again",
};

function ConfigCheckboxPanel<T extends ConfigState>({
    title,
    clientId,
    storageKey,
    defaultState,
    sections,
    fetchFn,
    defaultFn,
    updateFn,
    saveLabel,
    className,
    headerSlot,
}: ConfigCheckboxPanelProps<T>): React.ReactElement {
    const stateKeys = useMemo(() => sections.map((s) => s.key), [sections]);

    const { config, setConfig, saveStatus, handleCheckboxChange, handleSave } = useConfigCheckboxes(
        {
            storageKey,
            defaultState,
            fetchFn,
            defaultFn,
            updateFn,
            stateKeys,
            clientId,
        }
    );

    const renderCheckboxes = useCallback(
        (section: ConfigSection<T>): React.ReactNode => {
            const options = (config as ConfigState)[section.key as string];
            if (!options) return <div>Error: Invalid category</div>;
            const tips = section.tooltips ?? {};
            return Object.keys(options).map((item) => (
                <li key={item}>
                    <label title={tips[item] ?? item}>
                        <input
                            type="checkbox"
                            name={item}
                            checked={options[item] ?? false}
                            onChange={(e) => handleCheckboxChange(e, section.key as string)}
                        />
                        {item}
                    </label>
                </li>
            ));
        },
        [config, handleCheckboxChange]
    );

    return (
        <div className={className}>
            <h2>{title}</h2>
            <div className="checkbox-group label">
                {headerSlot && headerSlot(config, setConfig)}
                {sections.map((section) => (
                    <React.Fragment key={section.key as string}>
                        <h3>{section.label}</h3>
                        <ul>{renderCheckboxes(section)}</ul>
                    </React.Fragment>
                ))}
                <div className="save-row">
                    <button type="button" onClick={handleSave} disabled={saveStatus === "saving"}>
                        {saveLabel}
                    </button>
                    {saveStatus && (
                        <span
                            role="status"
                            aria-live="polite"
                            className={`save-status save-status--${saveStatus}`}
                        >
                            {SAVE_MESSAGES[saveStatus]}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ConfigCheckboxPanel;
