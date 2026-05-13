import React, { createContext, useState, useCallback, useMemo, useContext, useEffect } from "react";
import useIdleTimeout from "./useIdleTimeout";
import { setUnauthorizedHandler } from "../utils/api";

export interface AppUser {
    id: string;
    email?: string;
}

export interface AuthContextValue {
    user: AppUser | null;
    sessionExpired: boolean;
    handleLogin: () => void;
    handleLogout: () => void;
}

export const AuthContext = createContext<AuthContextValue>({
    user: null,
    sessionExpired: false,
    handleLogin: () => {},
    handleLogout: () => {},
});

const DEFAULT_USER: AppUser = {
    id: import.meta.env.VITE_DEFAULT_USER_ID ?? "dev_user",
    email: import.meta.env.VITE_DEFAULT_USER_EMAIL ?? "user@sonarft.local",
};

const IDLE_MS: number = parseInt(import.meta.env.VITE_IDLE_TIMEOUT_MS ?? "1800000", 10);

interface AuthProviderProps {
    children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [user, setUser] = useState<AppUser | null>(DEFAULT_USER);
    const [sessionExpired, setSessionExpired] = useState(false);

    const handleLogout = useCallback(() => {
        setUser(null);
        sessionStorage.removeItem("sonarft_token");
    }, []);

    const handleLogin = useCallback(() => {
        setUser(DEFAULT_USER);
        setSessionExpired(false);
    }, []);

    // Register 401 handler — triggers logout and shows session-expired banner
    useEffect(() => {
        setUnauthorizedHandler(() => {
            setSessionExpired(true);
            handleLogout();
        });
        return () => setUnauthorizedHandler(() => {});
    }, [handleLogout]);

    // Auto-logout after IDLE_MS ms of inactivity — only active while logged in
    useIdleTimeout(handleLogout, IDLE_MS, !!user);

    const contextValue = useMemo<AuthContextValue>(
        () => ({ user, sessionExpired, handleLogin, handleLogout }),
        [user, sessionExpired, handleLogin, handleLogout]
    );

    return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};

/** Convenience hook */
export const useAuth = (): AuthContextValue => useContext(AuthContext);
