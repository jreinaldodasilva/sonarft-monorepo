import React, { lazy, Suspense, useContext } from "react";
import { BrowserRouter as Router, Route, Routes, Navigate } from "react-router-dom";
import NavBar from "./components/NavBar/NavBar";
import Footer from "./components/Footer/Footer";
import { AuthProvider, AuthContext } from "./hooks/AuthProvider";
import PrivateRoute from "./components/PrivateRoute/PrivateRoute";
import "./App.css";
import "./styles.css";

const Crypto = lazy(() => import("./pages/Crypto/Crypto"));

const PageLoader: React.FC = () => <div className="page-loader">Loading...</div>;

const AppRoutes: React.FC = () => {
    const { user } = useContext(AuthContext);
    return (
        <Suspense fallback={<PageLoader />}>
            <Routes>
                <Route path="/" element={<Navigate to="/crypto" replace />} />
                <Route
                    path="/crypto"
                    element={
                        <PrivateRoute value={user}>
                            <Crypto />
                        </PrivateRoute>
                    }
                />
                <Route path="*" element={<Navigate to="/crypto" replace />} />
            </Routes>
        </Suspense>
    );
};

const App: React.FC = () => (
    <AuthProvider>
        <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <div className="App">
                <header className="header">
                    <NavBar />
                </header>
                <main className="main-container">
                    <AppRoutes />
                </main>
                <Footer />
            </div>
        </Router>
    </AuthProvider>
);

export default App;
