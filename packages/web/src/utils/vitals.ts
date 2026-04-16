import type { Metric } from "web-vitals";

const isDev = process.env.NODE_ENV === "development";
const vitalsUrl = process.env.REACT_APP_VITALS_URL;

const sendVitals = (metric: Metric): void => {
    if (isDev) {
        // eslint-disable-next-line no-console
        console.log(`[Web Vitals] ${metric.name}: ${Math.round(metric.value)}ms (${metric.rating})`);
        return;
    }

    if (!vitalsUrl) return;

    const body = JSON.stringify({
        name: metric.name,
        value: metric.value,
        rating: metric.rating,
        delta: metric.delta,
        id: metric.id,
        navigationType: metric.navigationType,
        url: window.location.href,
        ts: Date.now(),
    });

    if (navigator.sendBeacon) {
        navigator.sendBeacon(vitalsUrl, new Blob([body], { type: "application/json" }));
    } else {
        fetch(vitalsUrl, {
            method: "POST",
            body,
            headers: { "Content-Type": "application/json" },
            keepalive: true,
        });
    }
};

export default sendVitals;
