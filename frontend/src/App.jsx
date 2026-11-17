import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { Spinner } from "./components/ui.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import CareerRoadmap from "./pages/CareerRoadmap.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import FindCompanies from "./pages/FindCompanies.jsx";
import ProfileSettings from "./pages/ProfileSettings.jsx";
import ResumeAnalysis from "./pages/ResumeAnalysis.jsx";
import UnlockOpportunities from "./pages/UnlockOpportunities.jsx";
import { useAuth } from "./services/auth.jsx";

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner />;
  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/register" element={<AuthPage mode="register" />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="/analysis" element={<ResumeAnalysis />} />
        <Route path="/companies" element={<FindCompanies />} />
        <Route path="/opportunities" element={<UnlockOpportunities />} />
        <Route path="/roadmap" element={<CareerRoadmap />} />
        <Route path="/profile" element={<ProfileSettings />} />
        {/* Just signed up: go straight to the upload step. */}
        <Route path="/register" element={<Navigate to="/analysis" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
