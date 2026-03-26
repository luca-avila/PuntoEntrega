import { useAuth } from "@/hooks/use-auth";
import { Navigate, Outlet, useLocation } from "react-router-dom";

export function OnboardingOnlyRoute() {
  const { status, membership } = useAuth();

  if (status === "loading") {
    return (
      <div className="auth-shell text-sm text-muted-foreground">
        Cargando sesión...
      </div>
    );
  }

  if (membership?.organization_id) {
    return <Navigate replace to="/" />;
  }

  return <Outlet />;
}

export function OrganizationRequiredRoute() {
  const { status, membership } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div className="auth-shell text-sm text-muted-foreground">
        Cargando sesión...
      </div>
    );
  }

  if (!membership?.organization_id) {
    return <Navigate replace to="/organizacion/crear" state={{ from: location }} />;
  }

  return <Outlet />;
}

export function OwnerOnlyRoute() {
  const { status, isOwner } = useAuth();

  if (status === "loading") {
    return (
      <div className="auth-shell text-sm text-muted-foreground">
        Cargando sesión...
      </div>
    );
  }

  if (!isOwner) {
    return <Navigate replace to="/" />;
  }

  return <Outlet />;
}
