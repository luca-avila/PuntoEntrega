import { useAuth } from "@/hooks/use-auth";
import { Navigate, Outlet, useLocation } from "react-router-dom";

export function OnboardingOnlyRoute() {
  const { status, user } = useAuth();

  if (status === "loading") {
    return (
      <div className="auth-shell text-sm text-muted-foreground">
        Cargando sesión...
      </div>
    );
  }

  if (user?.organization_id) {
    return <Navigate replace to="/" />;
  }

  return <Outlet />;
}

export function OrganizationRequiredRoute() {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div className="auth-shell text-sm text-muted-foreground">
        Cargando sesión...
      </div>
    );
  }

  if (!user?.organization_id) {
    return <Navigate replace to="/onboarding/organizacion" state={{ from: location }} />;
  }

  return <Outlet />;
}
