import React, { useContext } from "react";
import { AuthContext } from "../../hooks/AuthProvider";
import PrivateRoute from "../../components/PrivateRoute/PrivateRoute";
import Building from "../../components/Building/Building";
import "./forex.css";

const Forex: React.FC = () => {
    const { user } = useContext(AuthContext);
    return (
        <section>
            <main className="forex-container">
                <PrivateRoute value={user}><Building /></PrivateRoute>
            </main>
        </section>
    );
};

export default Forex;
