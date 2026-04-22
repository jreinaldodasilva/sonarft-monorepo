import js from "@eslint/js";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import jsxA11y from "eslint-plugin-jsx-a11y";

export default [
    js.configs.recommended,

    // TypeScript source files
    {
        files: ["src/**/*.{ts,tsx}"],
        languageOptions: {
            parser: tsParser,
            parserOptions: {
                ecmaVersion: "latest",
                sourceType: "module",
                ecmaFeatures: { jsx: true },
            },
            globals: {
                window: "readonly",
                document: "readonly",
                navigator: "readonly",
                console: "readonly",
                fetch: "readonly",
                setTimeout: "readonly",
                clearTimeout: "readonly",
                setInterval: "readonly",
                clearInterval: "readonly",
                requestAnimationFrame: "readonly",
                cancelAnimationFrame: "readonly",
                localStorage: "readonly",
                WebSocket: "readonly",
                MessageEvent: "readonly",
                Blob: "readonly",
                HTMLDivElement: "readonly",
                HTMLInputElement: "readonly",
                HTMLButtonElement: "readonly",
                HTMLElement: "readonly",
                React: "readonly",
            },
        },
        plugins: {
            react: reactPlugin,
            "react-hooks": reactHooksPlugin,
            "@typescript-eslint": tsPlugin,
            "jsx-a11y": jsxA11y,
        },
        settings: {
            react: { version: "detect" },
        },
        rules: {
            // Core quality
            "no-console": "warn",
            "no-unused-vars": "off",                          // handled by @typescript-eslint
            "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
            "@typescript-eslint/no-explicit-any": "warn",

            // React
            "react/react-in-jsx-scope": "off",               // not needed with react-jsx transform
            "react/prop-types": "off",                        // TypeScript handles this
            "react/jsx-key": "error",

            // React Hooks — critical for correctness
            "react-hooks/rules-of-hooks": "error",
            "react-hooks/exhaustive-deps": "warn",

            // Accessibility
            "jsx-a11y/alt-text": "warn",
            "jsx-a11y/aria-props": "warn",
            "jsx-a11y/aria-role": "warn",
            "jsx-a11y/no-noninteractive-element-interactions": "warn",
        },
    },

    // Test files — relax some rules and add test globals
    {
        files: ["src/**/*.test.{ts,tsx}", "src/mocks/**/*.{ts,tsx}", "src/integration/**/*.{ts,tsx}", "src/setupTests.ts"],
        languageOptions: {
            globals: {
                describe: "readonly",
                it: "readonly",
                expect: "readonly",
                beforeEach: "readonly",
                afterEach: "readonly",
                beforeAll: "readonly",
                afterAll: "readonly",
                vi: "readonly",
                HTMLInputElement: "readonly",
                HTMLDivElement: "readonly",
                HTMLButtonElement: "readonly",
                React: "readonly",
            },
        },
        rules: {
            "no-console": "off",
            "@typescript-eslint/no-explicit-any": "off",
            "no-undef": "off",
        },
    },

    // Ignore build output and config files
    {
        ignores: ["build/**", "node_modules/**", "*.config.js", "*.config.ts"],
    },
];
