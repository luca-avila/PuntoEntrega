import { useAuth } from "@/hooks/use-auth";
import { Navigate, Outlet, useLocation } from "react-router-dom";

export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div className="auth-shell text-sm text-muted-foreground">
        Cargando sesión...
      </div>
    );
  }

  if (status !== "authenticated") {
    return <Navigate replace to="/iniciar-sesion" state={{ from: location }} />;
  }

  return <Outlet />;
}
