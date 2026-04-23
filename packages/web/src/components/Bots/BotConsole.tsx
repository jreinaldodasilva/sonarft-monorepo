import React, { useEffect, useRef } from "react";

interface BotConsoleProps {
    logs: string[];
}

const getLogClass = (line: string): string => {
    if (/WARNING|WARN/i.test(line))  return "log-line log-line--warning";
    if (/ERROR|CRITICAL/i.test(line)) return "log-line log-line--error";
    if (/DEBUG/i.test(line))          return "log-line log-line--debug";
    return "log-line log-line--info";
};

const BotConsole: React.FC<BotConsoleProps> = ({ logs }) => {
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs]);

    return (
        <pre className="console" aria-label="Bot log output" aria-live="polite">
            {logs.map((line, i) => (
                <span key={i} className={getLogClass(line)}>{line}{"\n"}</span>
            ))}
            <span ref={endRef} />
        </pre>
    );
};

export default React.memo(BotConsole);
