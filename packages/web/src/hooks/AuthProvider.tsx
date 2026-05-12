import React, { createContext, useState, useCallback, useMemo, useContext } from "react";
import useIdleTimeout from "./useIdleTimeout";

export interface AppUser {
    id: string;
    email?: string;
}

export interface AuthContextValue {
    user: AppUser | null;
    handleLogin: () => void;
    handleLogout: () => void;
}

export const AuthContext = createContext<AuthContextValue>({
    user: null,
    handleLogin: () => {},
    handleLogout: () => {},
});

const DEFAULT_USER: AppUser = {
    id: (import.meta.env.VITE_DEFAULT_USER_ID as string) ?? "dev_user",
    email: (import.meta.env.VITE_DEFAULT_USER_EMAIL as string) ?? "user@sonarft.local",
};

const IDLE_MS: number = parseInt(
    (import.meta.env.VITE_IDLE_TIMEOUT_MS as string) ?? "1800000",
    10
);

interface AuthProviderProps {
    children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [user, setUser] = useState<AppUser | null>(DEFAULT_USER);

    const handleLogout = useCallback(() => {
        setUser(null);
        sessionStorage.removeItem("sonarft_token");
    }, []);

    const handleLogin  = useCallback(() => setUser(DEFAULT_USER), []);

    // Auto-logout after IDLE_MS ms of inactivity — only active while logged in
    useIdleTimeout(handleLogout, IDLE_MS, !!user);

    const contextValue = useMemo<AuthContextValue>(
        () => ({ user, handleLogin, handleLogout }),
        [user, handleLogin, handleLogout]
    );

    return (
        <AuthContext.Provider value={contextValue}>
            {children}
        </AuthContext.Provider>
    );
};

/** Convenience hook */
export const useAuth = (): AuthContextValue => useContext(AuthContext);
