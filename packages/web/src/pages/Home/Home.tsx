import React from "react";
import Welcome from "./Welcome/Welcome";
import "./home.css";

const Home: React.FC = () => (
    <div className="home-container">
        <section className="welcome-container">
            <Welcome />
        </section>
    </div>
);

export default Home;
