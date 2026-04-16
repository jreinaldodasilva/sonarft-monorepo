import React from "react";
import DoggyWelcome from "../../components/DoggyWelcome/DoggyWelcome";
import "./doggy.css";

const Doggy: React.FC = () => (
    <section>
        <main className="doggy">
            <div className="doggy-container">
                <DoggyWelcome />
            </div>
        </main>
    </section>
);

export default Doggy;
