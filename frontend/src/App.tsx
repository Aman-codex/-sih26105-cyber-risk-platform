import { Navigate, Route, Routes } from "react-router-dom";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Assets from "@/pages/Assets";
import Vulnerabilities from "@/pages/Vulnerabilities";
import Threats from "@/pages/Threats";
import Controls from "@/pages/Controls";
import RiskOverview from "@/pages/RiskOverview";
import Compliance from "@/pages/Compliance";
import InvestmentOptimization from "@/pages/InvestmentOptimization";
import WhatIfSimulator from "@/pages/WhatIfSimulator";
import MLPredictions from "@/pages/MLPredictions";
import Assistant from "@/pages/Assistant";
import { useAuth } from "@/hooks/useAuth";

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div className="p-8 text-sm text-muted-foreground">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="risk" replace />} />
        <Route path="risk" element={<RiskOverview />} />
        <Route path="assets" element={<Assets />} />
        <Route path="vulnerabilities" element={<Vulnerabilities />} />
        <Route path="threats" element={<Threats />} />
        <Route path="controls" element={<Controls />} />
        <Route path="compliance" element={<Compliance />} />
        <Route path="investments" element={<InvestmentOptimization />} />
        <Route path="what-if" element={<WhatIfSimulator />} />
        <Route path="ml" element={<MLPredictions />} />
        <Route path="assistant" element={<Assistant />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
