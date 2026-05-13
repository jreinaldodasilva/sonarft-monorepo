import React, { useContext } from "react";
import { AuthContext } from "../../hooks/AuthProvider";
import ErrorBoundary from "../../components/ErrorBoundary/ErrorBoundary";
import Bots from "../../components/Bots/Bots";
import Parameters from "../../components/Parameters/Parameters";
import Indicators from "../../components/Indicators/Indicators";
import "./crypto.css";

const Crypto: React.FC = () => {
    const { user } = useContext(AuthContext);

    // PrivateRoute redirects unauthenticated users before this renders.
    // The only case where user is null here is a mid-session 401 expiry.
    if (!user)
        return (
            <div className="session-expired" role="alert">
                ⚠ Your session has expired. Please refresh the page to log in again.
            </div>
        );

    return (
        <section>
            <h1 className="sr-only">SonarFT Trading Dashboard</h1>
            <main className="crypto">
                <ErrorBoundary>
                    <div className="parameters-container">
                        <Parameters clientId={user.id} />
                        <Indicators clientId={user.id} />
                    </div>
                    <div className="bots-container">
                        <Bots user={user} />
                    </div>
                </ErrorBoundary>
            </main>
        </section>
    );
};

export default Crypto;
