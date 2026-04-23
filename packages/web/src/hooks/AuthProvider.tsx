import React, { createContext, useState, useCallback, useMemo, useContext } from "react";

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

interface AuthProviderProps {
    children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [user, setUser] = useState<AppUser | null>(DEFAULT_USER);

    const handleLogin  = useCallback(() => setUser(DEFAULT_USER), []);
    const handleLogout = useCallback(() => setUser(null), []);

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
