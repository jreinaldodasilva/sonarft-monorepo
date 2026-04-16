import React, { useContext } from "react";
import { AuthContext } from "../../hooks/AuthProvider";
import PrivateRoute from "../../components/PrivateRoute/PrivateRoute";
import ErrorBoundary from "../../components/ErrorBoundary/ErrorBoundary";
import Bots from "../../components/Bots/Bots";
import Parameters from "../../components/Parameters/Parameters";
import Indicators from "../../components/Indicators/Indicators";
import "./crypto.css";

const Crypto: React.FC = () => {
    const { user } = useContext(AuthContext);

    return (
        <section>
            <main className="crypto">
                <PrivateRoute value={user}>
                    <ErrorBoundary>
                        <div className="parameters-container">
                            <Parameters clientId={user!.id} />
                            <Indicators clientId={user!.id} />
                        </div>
                        <div className="bots-container">
                            <Bots user={user as { id: string; email?: string }} />
                        </div>
                    </ErrorBoundary>
                </PrivateRoute>
            </main>
        </section>
    );
};

export default Crypto;
