import React, { useContext } from "react";
import { AuthContext } from "../../hooks/AuthProvider";
import ErrorBoundary from "../../components/ErrorBoundary/ErrorBoundary";
import Bots from "../../components/Bots/Bots";
import Parameters from "../../components/Parameters/Parameters";
import Indicators from "../../components/Indicators/Indicators";
import "./crypto.css";

const Crypto: React.FC = () => {
    const { user } = useContext(AuthContext);

    if (!user) return null;

    return (
        <section>
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
