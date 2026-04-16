import React, { useContext } from "react";
import { AuthContext } from "../../hooks/AuthProvider";
import PrivateRoute from "../../components/PrivateRoute/PrivateRoute";
import Building from "../../components/Building/Building";
import "./dex.css";

const Dex: React.FC = () => {
    const { user } = useContext(AuthContext);
    return (
        <section>
            <main className="DEX-container">
                <PrivateRoute value={user}><Building /></PrivateRoute>
            </main>
        </section>
    );
};

export default Dex;
