import React, { useEffect, useRef } from "react";

interface BotConsoleProps {
    logs: string[];
}

const BotConsole: React.FC<BotConsoleProps> = ({ logs }) => {
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs]);

    return (
        <ul>
            <pre className="console">
                {logs.join("\n")}
                <div ref={endRef} />
            </pre>
        </ul>
    );
};

export default BotConsole;
