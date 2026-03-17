import { useAuth } from "@/hooks/use-auth";
import { Navigate, Outlet, useLocation } from "react-router-dom";

export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/20 px-4 text-sm text-muted-foreground">
        Cargando sesión...
      </div>
    );
  }

  if (status !== "authenticated") {
    return <Navigate replace to="/login" state={{ from: location }} />;
  }

  return <Outlet />;
}
