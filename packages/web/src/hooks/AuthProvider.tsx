import React, { createContext, useState, useEffect, useCallback, useMemo } from "react";
import netlifyIdentity from "netlify-identity-widget";
import useIdleTimeout from "./useIdleTimeout";

interface NetlifyUser {
    id: string;
    email: string;
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
    process.env.REACT_APP_IDLE_TIMEOUT_MS ?? "1800000",
    10
);

interface AuthProviderProps {
    children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [user, setUser] = useState<NetlifyUser | null>(null);

    const handleLogin = useCallback(() => { netlifyIdentity.open(); }, []);
    const handleLogout = useCallback(() => { netlifyIdentity.logout(); }, []);
    const handleLoginSuccess = useCallback((u: NetlifyUser) => { setUser(u); }, []);
    const handleLogoutSuccess = useCallback(() => { setUser(null); }, []);

    useEffect(() => {
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
