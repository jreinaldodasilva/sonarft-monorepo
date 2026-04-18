import React, { createContext, useState, useEffect, useCallback, useMemo } from "react";
import netlifyIdentity from "netlify-identity-widget";
import useIdleTimeout from "./useIdleTimeout";

export interface NetlifyUser {
    id: string;
    email?: string;
    token?: { access_token?: string };
    [key: string]: unknown;
}

export interface AuthContextValue {
    user: NetlifyUser | null;
    handleLogin: () => void;
    handleLogout: () => void;
}

export const AuthContext = createContext<AuthContextValue>({
    user: null,
    handleLogin: () => {},
    handleLogout: () => {},
});

const IDLE_TIMEOUT_MS = parseInt(
    (import.meta.env.VITE_IDLE_TIMEOUT_MS as string) ?? "1800000",
    10
);

const DEV_AUTH_BYPASS = import.meta.env.VITE_DEV_AUTH_BYPASS === "true";

const DEV_USER: NetlifyUser = {
    id: "dev_user",
    email: "dev@localhost",
    token: { access_token: "dev-token" },
};

interface AuthProviderProps {
    children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [user, setUser] = useState<NetlifyUser | null>(
        DEV_AUTH_BYPASS ? DEV_USER : null
    );

    const handleLogin = useCallback(() => {
        if (DEV_AUTH_BYPASS) return;
        netlifyIdentity.open();
    }, []);
    const handleLogout = useCallback(() => {
        if (DEV_AUTH_BYPASS) return;
        netlifyIdentity.logout();
    }, []);
    const handleLoginSuccess = useCallback((u: NetlifyUser) => { setUser(u); }, []);
    const handleLogoutSuccess = useCallback(() => { setUser(null); }, []);

    useEffect(() => {
        if (DEV_AUTH_BYPASS) return;

        netlifyIdentity.init({ locale: "en" });
        netlifyIdentity.on("login", handleLoginSuccess as (user: object) => void);
        netlifyIdentity.on("logout", handleLogoutSuccess);

        const currentUser = netlifyIdentity.currentUser() as NetlifyUser | null;
        if (currentUser) setUser(currentUser);

        return () => {
            netlifyIdentity.off("login", handleLoginSuccess as (user: object) => void);
            netlifyIdentity.off("logout", handleLogoutSuccess);
        };
    }, [handleLoginSuccess, handleLogoutSuccess]);

    useIdleTimeout(handleLogout, IDLE_TIMEOUT_MS, !!user);

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
