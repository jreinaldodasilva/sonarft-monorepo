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
        <pre className="console">
            {logs.join("\n")}
            <span ref={endRef} />
        </pre>
    );
};

export default React.memo(BotConsole);
