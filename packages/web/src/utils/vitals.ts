import type { Metric } from "web-vitals";

const isDev = import.meta.env.DEV;
const vitalsUrl = import.meta.env.VITE_VITALS_URL as string | undefined;

interface MetricV3 extends Metric {
    rating?: string;
    navigationType?: string;
}

const sendVitals = (metric: MetricV3): void => {
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
