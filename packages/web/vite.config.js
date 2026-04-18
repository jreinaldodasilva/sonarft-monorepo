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
    },

    test: {
        globals: true,
        environment: "jsdom",
        setupFiles: "./src/setupTests.ts",
        css: false,
    },
});
