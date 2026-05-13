import React, { lazy, Suspense } from "react";
import { BrowserRouter as Router, Route, Routes, Navigate } from "react-router-dom";
import NavBar from "./components/NavBar/NavBar";
import Footer from "./components/Footer/Footer";
import { AuthProvider } from "./hooks/AuthProvider";
import "./App.css";
import "./styles.css";

const Crypto = lazy(() => import("./pages/Crypto/Crypto"));

const PageLoader: React.FC = () => <div className="page-loader">Loading...</div>;

const App: React.FC = () => (
    <AuthProvider>
        <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <div className="App">
                <header className="header">
                    <NavBar />
                </header>
                <main className="main-container">
                    <Suspense fallback={<PageLoader />}>
                        <Routes>
                            <Route path="/" element={<Navigate to="/crypto" replace />} />
                            <Route path="/crypto" element={<Crypto />} />
                            <Route path="*" element={<Navigate to="/crypto" replace />} />
                        </Routes>
                    </Suspense>
                </main>
                <Footer />
            </div>
        </Router>
    </AuthProvider>
);

export default App;
