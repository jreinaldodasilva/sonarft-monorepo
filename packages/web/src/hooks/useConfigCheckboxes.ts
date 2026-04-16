import { useState, useEffect, useCallback } from "react";

const SAVE_FEEDBACK_MS = 3000;

type SaveStatus = "saving" | "saved" | "error" | null;
type ConfigState = Record<string, Record<string, boolean>>;

interface UseConfigCheckboxesOptions<T extends ConfigState> {
    storageKey: string;
    defaultState: T;
    fetchFn: (clientId: string) => Promise<T>;
    defaultFn: () => Promise<T>;
    updateFn: (clientId: string, state: T) => Promise<unknown>;
    stateKeys: (keyof T)[];
    clientId: string;
}

interface UseConfigCheckboxesReturn<T extends ConfigState> {
    config: T;
    saveStatus: SaveStatus;
    handleCheckboxChange: (e: React.ChangeEvent<HTMLInputElement>, category: string) => void;
    handleSave: () => Promise<void>;
}

const useConfigCheckboxes = <T extends ConfigState>({
    storageKey,
    defaultState,
    fetchFn,
    defaultFn,
    updateFn,
    stateKeys,
    clientId,
}: UseConfigCheckboxesOptions<T>): UseConfigCheckboxesReturn<T> => {
    const [config, setConfig] = useState<T>(() => {
        try {
            const stored = localStorage.getItem(storageKey);
            return stored ? (JSON.parse(stored) as T) : defaultState;
        } catch {
            return defaultState;
        }
    });
    const [saveStatus, setSaveStatus] = useState<SaveStatus>(null);

    useEffect(() => {
        const load = async () => {
            try {
                const data = await fetchFn(clientId);
                if (data) {
                    const next = {} as T;
                    stateKeys.forEach((k) => { (next as ConfigState)[k as string] = (data as ConfigState)[k as string]; });
                    setConfig(next);
                    return;
                }
            } catch { /* fall through */ }

            try {
                const stored = JSON.parse(localStorage.getItem(storageKey) ?? "null") as T | null;
                if (stored) {
                    const next = {} as T;
                    stateKeys.forEach((k) => { (next as ConfigState)[k as string] = (stored as ConfigState)[k as string]; });
                    setConfig(next);
                    return;
                }
            } catch { /* fall through */ }

            try {
                const data = await defaultFn();
                const next = {} as T;
                stateKeys.forEach((k) => { (next as ConfigState)[k as string] = (data as ConfigState)[k as string]; });
                setConfig(next);
            } catch { /* all sources failed */ }
        };

        load();
    }, [clientId]); // eslint-disable-line react-hooks/exhaustive-deps

    const handleCheckboxChange = useCallback((e: React.ChangeEvent<HTMLInputElement>, category: string) => {
        const { name, checked } = e.target;
        setConfig((prev) => {
            const next = {
                ...prev,
                [category]: { ...(prev as ConfigState)[category], [name]: checked },
            } as T;
            localStorage.setItem(storageKey, JSON.stringify(next));
            return next;
        });
    }, [storageKey]);

    const handleSave = useCallback(async () => {
        setSaveStatus("saving");
        try {
            await updateFn(clientId, config);
            setSaveStatus("saved");
            setTimeout(() => setSaveStatus(null), SAVE_FEEDBACK_MS);
        } catch {
            setSaveStatus("error");
            setTimeout(() => setSaveStatus(null), SAVE_FEEDBACK_MS);
        }
    }, [clientId, config, updateFn]);

    return { config, saveStatus, handleCheckboxChange, handleSave };
};

export default useConfigCheckboxes;
