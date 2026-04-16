import React from "react";
import CChatGPT from "../../components/CChatGPT/CChatGPT";
import "./cryptochatgpt.css";

const CryptoChatGPT: React.FC = () => (
    <section>
        <main className="cryptochatgpt">
            <div className="cryptochatgpt-container">
                <CChatGPT />
            </div>
        </main>
    </section>
);

export default CryptoChatGPT;
