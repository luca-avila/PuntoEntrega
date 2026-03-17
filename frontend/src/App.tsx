import { AuthProvider } from "@/features/auth/auth-context";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { HomePage } from "@/pages/home-page";
import { LoginPage } from "@/pages/login-page";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<HomePage />} />
          </Route>
          <Route path="*" element={<Navigate replace to="/" />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
