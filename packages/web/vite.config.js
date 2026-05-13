import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],

    // Expose env vars prefixed with VITE_ (Vite default)
    envPrefix: "VITE_",

    server: {
        port: 3000,
        open: false,
    },

    build: {
        outDir: "build",
        sourcemap: false,
        // Warn if any chunk exceeds 100KB gzipped
        chunkSizeWarningLimit: 100,
        rollupOptions: {
            output: {
                manualChunks(id) {
                    if (id.includes("netlify-identity-widget")) return "vendor-netlify";
                    if (id.includes("recharts") || id.includes("victory-vendor")) return "vendor-recharts";
                    if (id.includes("node_modules/react/") || id.includes("node_modules/react-dom/") || id.includes("node_modules/react-router")) return "vendor-react";
                },
            },
        },
    },

    test: {
        globals: true,
        environment: "jsdom",
        setupFiles: "./src/setupTests.ts",
        css: false,
        coverage: {
            provider: "v8",
            reporter: ["text", "lcov"],
            thresholds: {
                lines: 60,
                functions: 60,
                branches: 50,
            },
            exclude: [
                "src/mocks/**",
                "src/setupTests.ts",
                "src/utils/vitals.ts",
                "src/vite-env.d.ts",
            ],
        },
    },
});
