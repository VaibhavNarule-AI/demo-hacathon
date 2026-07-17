import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { AppProvider } from "./context/AppContext";
import Admin from "./pages/Admin";
import BreachPredictor from "./pages/BreachPredictor";
import CustomerHealth from "./pages/CustomerHealth";
import Dashboard from "./pages/Dashboard";
import Incidents from "./pages/Incidents";
import Login from "./pages/Login";
import Notifications from "./pages/Notifications";
import Partners from "./pages/Partners";
import ThreatLandscape from "./pages/ThreatLandscape";
import Unauthorized from "./pages/Unauthorized";

const ALL_ROLES = ["super_admin", "partner_manager", "customer_viewer", "analyst"];

function AuthenticatedShell() {
  return (
    <AppProvider>
      <Layout />
    </AppProvider>
  );
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/unauthorized" element={<Unauthorized />} />

        <Route
          element={
            <ProtectedRoute allowedRoles={ALL_ROLES}>
              <AuthenticatedShell />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/breach-predictor" element={<BreachPredictor />} />
          <Route path="/customer-health" element={<CustomerHealth />} />
          <Route path="/threat-landscape" element={<ThreatLandscape />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route
            path="/partners"
            element={
              <ProtectedRoute allowedRoles={["super_admin", "partner_manager"]}>
                <Partners />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={["super_admin"]}>
                <Admin />
              </ProtectedRoute>
            }
          />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
