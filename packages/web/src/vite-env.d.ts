/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_URL: string;
    readonly VITE_WS_URL: string;
    readonly VITE_DEV_AUTH_BYPASS: string;
    readonly VITE_DEFAULT_USER_ID: string;
    readonly VITE_DEFAULT_USER_EMAIL: string;
    readonly VITE_VITALS_URL: string | undefined;
    readonly VITE_IDLE_TIMEOUT_MS: string | undefined;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}
