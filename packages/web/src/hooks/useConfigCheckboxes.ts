import { useState, useEffect, useCallback } from "react";

const SAVE_FEEDBACK_MS = 3000;

type SaveStatus = "saving" | "saved" | "error" | null;
type ConfigState = Record<string, Record<string, boolean> | string | number | undefined>;

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
    setConfig: React.Dispatch<React.SetStateAction<T>>;
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
        let cancelled = false;

        const pickKeys = (source: ConfigState): T => {
            const next = {} as T;
            stateKeys.forEach((k) => {
                (next as ConfigState)[k as string] = source[k as string];
            });
            return next;
        };

        const load = async () => {
            // 1. Try server
            try {
                const data = await fetchFn(clientId);
                if (!cancelled && data) {
                    setConfig(pickKeys(data as ConfigState));
                    return;
                }
            } catch {
                /* fall through */
            }

            if (cancelled) return;

            // 2. Try localStorage
            try {
                const stored = JSON.parse(localStorage.getItem(storageKey) ?? "null") as T | null;
                if (!cancelled && stored) {
                    setConfig(pickKeys(stored as ConfigState));
                    return;
                }
            } catch {
                /* fall through */
            }

            if (cancelled) return;

            // 3. Try bundled defaults
            try {
                const data = await defaultFn();
                if (!cancelled && data) {
                    setConfig(pickKeys(data as ConfigState));
                }
            } catch {
                /* all sources failed */
            }
        };

        load();

        return () => {
            cancelled = true;
        };
    }, [clientId, storageKey, fetchFn, defaultFn, stateKeys]); // all deps explicit — no suppression

    const handleCheckboxChange = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>, category: string) => {
            const { name, checked } = e.target;
            setConfig((prev) => {
                const next = {
                    ...prev,
                    [category]: { ...(prev as ConfigState)[category], [name]: checked },
                } as T;
                localStorage.setItem(storageKey, JSON.stringify(next));
                return next;
            });
        },
        [storageKey]
    );

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

    return { config, setConfig, saveStatus, handleCheckboxChange, handleSave };
};

export default useConfigCheckboxes;
