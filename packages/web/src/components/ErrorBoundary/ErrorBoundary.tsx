import React, { Component, ErrorInfo } from "react";
import "./errorboundary.css";

interface Props {
    children: React.ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, info: ErrorInfo): void {
        // Could send to error reporting service here
        void error; void info;
    }

    handleReload = (): void => {
        this.setState({ hasError: false, error: null });
    };

    render(): React.ReactNode {
        if (this.state.hasError) {
            return (
                <div className="error-boundary">
                    <div className="error-boundary__box">
                        <h2>Something went wrong</h2>
                        <p>An unexpected error occurred in the trading interface.</p>
                        {process.env.NODE_ENV === "development" && (
                            <pre className="error-boundary__detail">
                                {this.state.error?.message}
                            </pre>
                        )}
                        <button onClick={this.handleReload}>Try again</button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}

export default ErrorBoundary;
