import React from "react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import ErrorBoundary from "./ErrorBoundary";

expect.extend(toHaveNoViolations);

interface ThrowingProps {
    shouldThrow: boolean;
}

const ThrowingComponent: React.FC<ThrowingProps> = ({ shouldThrow }) => {
    if (shouldThrow) throw new Error("Test render error");
    return <div>Normal content</div>;
};

beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
    vi.mocked(console.error).mockRestore();
});

describe("ErrorBoundary", () => {
    it("renders children when no error occurs", () => {
        render(
            <ErrorBoundary>
                <div>Safe content</div>
            </ErrorBoundary>
        );
        expect(screen.getByText("Safe content")).toBeInTheDocument();
    });

    it("renders fallback UI when a child throws", () => {
        render(
            <ErrorBoundary>
                <ThrowingComponent shouldThrow={true} />
            </ErrorBoundary>
        );
        expect(screen.getByText("Something went wrong")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    });

    it("does not show children when in error state", () => {
        render(
            <ErrorBoundary>
                <ThrowingComponent shouldThrow={true} />
            </ErrorBoundary>
        );
        expect(screen.queryByText("Normal content")).not.toBeInTheDocument();
    });

    it("resets error state when Try again is clicked", () => {
        const { unmount } = render(
            <ErrorBoundary>
                <ThrowingComponent shouldThrow={true} />
            </ErrorBoundary>
        );
        expect(screen.getByText("Something went wrong")).toBeInTheDocument();

        fireEvent.click(screen.getByRole("button", { name: /try again/i }));
        unmount();

        render(
            <ErrorBoundary>
                <ThrowingComponent shouldThrow={false} />
            </ErrorBoundary>
        );
        expect(screen.getByText("Normal content")).toBeInTheDocument();
    });
});

describe("ErrorBoundary — accessibility", () => {
    it("has no accessibility violations in normal state", async () => {
        const { container } = render(
            <ErrorBoundary>
                <div>Safe content</div>
            </ErrorBoundary>
        );
        expect(await axe(container)).toHaveNoViolations();
    });

    it("has no accessibility violations in error state", async () => {
        const { container } = render(
            <ErrorBoundary>
                <ThrowingComponent shouldThrow={true} />
            </ErrorBoundary>
        );
        expect(await axe(container)).toHaveNoViolations();
    });
});
