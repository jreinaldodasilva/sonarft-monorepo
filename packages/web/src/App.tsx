import React, { lazy, Suspense } from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Header from "./components/Header/Header";
import Footer from "./components/Footer/Footer";
import CryptoTicker from "./components/CryptoTicker/CryptoTicker";
import { AuthProvider } from "./hooks/AuthProvider";
import "./App.css";
import "./styles.css";

const Home = lazy(() => import("./pages/Home/Home"));
const Crypto = lazy(() => import("./pages/Crypto/Crypto"));
const CryptoChatGPT = lazy(() => import("./pages/CryptoChatGPT/CryptoChatGPT"));
const Doggy = lazy(() => import("./pages/Doggy/Doggy"));

const PageLoader: React.FC = () => (
    <div className="page-loader">Loading...</div>
);

const App: React.FC = () => (
    <AuthProvider>
        <Router>
            <div className="App">
                <Header />
                <CryptoTicker />
                <main className="main-container">
                    <Suspense fallback={<PageLoader />}>
                        <Routes>
                            <Route path="/" element={<Home />} />
                            <Route path="/crypto" element={<Crypto />} />
                            <Route path="/cryptochatgpt" element={<CryptoChatGPT />} />
                            <Route path="/doggy" element={<Doggy />} />
                        </Routes>
                    </Suspense>
                </main>
                <Footer />
            </div>
        </Router>
    </AuthProvider>
);

export default App;
