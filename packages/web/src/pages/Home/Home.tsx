import React from "react";
import Welcome from "./Welcome/Welcome";
import "./home.css";

const Home: React.FC = () => (
    <main className="home-container">
        <main className="welcome-container">
            <Welcome />
        </main>
    </main>
);

export default Home;
