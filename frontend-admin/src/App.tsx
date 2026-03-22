import React, { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./api/client";
import AdminLayout from "./components/AdminLayout";

const Login = lazy(() => import("./pages/Login"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Users = lazy(() => import("./pages/Users"));
const Plans = lazy(() => import("./pages/Plans"));
const Subscriptions = lazy(() => import("./pages/Subscriptions"));
const Financial = lazy(() => import("./pages/Financial"));
const Invites = lazy(() => import("./pages/Invites"));
const PromoCodes = lazy(() => import("./pages/PromoCodes"));
const Storage = lazy(() => import("./pages/Storage"));
const PlatformSettings = lazy(() => import("./pages/PlatformSettings"));

function RequireAdmin({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div style={{ padding: "2rem", color: "#888" }}>Carregando...</div>}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={
            <RequireAdmin>
              <AdminLayout />
            </RequireAdmin>
          }>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="users" element={<Users />} />
            <Route path="plans" element={<Plans />} />
            <Route path="subscriptions" element={<Subscriptions />} />
            <Route path="financial" element={<Financial />} />
            <Route path="invites" element={<Invites />} />
            <Route path="promo-codes" element={<PromoCodes />} />
            <Route path="storage" element={<Storage />} />
            <Route path="settings" element={<PlatformSettings />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
