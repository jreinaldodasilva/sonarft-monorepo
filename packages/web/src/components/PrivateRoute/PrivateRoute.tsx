import React from "react";
import { Navigate } from "react-router-dom";

interface PrivateRouteProps {
    children: React.ReactNode;
    value: unknown;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children, value }) =>
    value ? <>{children}</> : <Navigate to="/" />;

export default PrivateRoute;
