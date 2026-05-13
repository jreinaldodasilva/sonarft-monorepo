import React, { useEffect, useRef } from "react";

interface BotConsoleProps {
    logs: string[];
}

const getLogClass = (line: string): string => {
    if (/WARNING|WARN/i.test(line)) return "log-line log-line--warning";
    if (/ERROR|CRITICAL/i.test(line)) return "log-line log-line--error";
    if (/DEBUG/i.test(line)) return "log-line log-line--debug";
    return "log-line log-line--info";
};

const BotConsole: React.FC<BotConsoleProps> = ({ logs }) => {
    const preRef = useRef<HTMLPreElement>(null);

    useEffect(() => {
        const el = preRef.current;
        if (!el) return;
        // Only auto-scroll if the user is already near the bottom (within 60px)
        const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
        if (nearBottom) {
            el.scrollTop = el.scrollHeight;
        }
    }, [logs]);

    return (
        <pre ref={preRef} className="console" aria-label="Bot log output" aria-live="polite">
            {logs.map((line, i) => (
                <span key={i} className={getLogClass(line)}>
                    {line}
                    {"\n"}
                </span>
            ))}
        </pre>
    );
};

export default React.memo(BotConsole);
