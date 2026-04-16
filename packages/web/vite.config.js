import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],

    // Expose env vars prefixed with REACT_APP_ for CRA compatibility
    envPrefix: "REACT_APP_",

    server: {
        port: 3000,
        open: true,
    },

    build: {
        outDir: "build",
        sourcemap: false,
    },

    test: {
        globals: true,
        environment: "jsdom",
        setupFiles: "./src/setupTests.ts",
        css: false,
    },
});
