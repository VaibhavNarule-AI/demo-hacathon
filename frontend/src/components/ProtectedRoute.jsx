import { Navigate } from "react-router-dom";

export default function ProtectedRoute({ allowedRoles, children }) {
  const token = localStorage.getItem("token");
  const tokenExp = Number(localStorage.getItem("tokenExp") || 0);
  const role = localStorage.getItem("role");

  if (!token || !tokenExp || Date.now() >= tokenExp) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return children;
}
