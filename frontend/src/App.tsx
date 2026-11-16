import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { NavBar } from "./components/NavBar";
import { useAuth } from "./context/AuthContext";
import { ContractDetailPage } from "./pages/ContractDetailPage";
import { ContractsPage } from "./pages/ContractsPage";
import { LoginPage } from "./pages/LoginPage";
import { QueryHistoryPage } from "./pages/QueryHistoryPage";

function RequireAuth({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function App() {
  return (
    <div className="app-shell">
      <NavBar />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/contracts"
          element={
            <RequireAuth>
              <ContractsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/contracts/:id"
          element={
            <RequireAuth>
              <ContractDetailPage />
            </RequireAuth>
          }
        />
        <Route
          path="/queries"
          element={
            <RequireAuth>
              <QueryHistoryPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/contracts" replace />} />
      </Routes>
    </div>
  );
}

export default App;
