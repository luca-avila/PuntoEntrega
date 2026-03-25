import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const sharedNavigationItems = [
  { to: "/entregas", label: "Historial" },
  { to: "/ubicaciones", label: "Ubicaciones" },
  { to: "/productos", label: "Productos" },
  { to: "/", label: "Inicio" },
];

export function ProtectedLayout() {
  const { user, isOwner, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const location = useLocation();
  const isHistoryActive =
    location.pathname === "/entregas" ||
    (location.pathname.startsWith("/entregas/") &&
      !location.pathname.startsWith("/entregas/nueva"));
  const navigationItems = isOwner
    ? [
        { to: "/entregas/nueva", label: "Nueva entrega" },
        ...sharedNavigationItems,
        { to: "/equipo", label: "Equipo" },
      ]
    : sharedNavigationItems;

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="border-b border-border/70 bg-background/85 backdrop-blur">
        <div className="mx-auto w-full max-w-6xl px-4 py-4 sm:py-5">
          <div className="flex items-start justify-between gap-3 sm:items-center">
            <div className="min-w-0">
              <h1 className="font-heading text-lg font-semibold">PuntoEntrega</h1>
              <p className="truncate text-sm text-muted-foreground">
                {user?.email ?? "Sesion activa"}
              </p>
            </div>

            <Button
              className="shrink-0"
              disabled={isLoggingOut}
              onClick={handleLogout}
              variant="outline"
            >
              {isLoggingOut ? "Cerrando..." : "Salir"}
            </Button>
          </div>

          <nav className="mt-4 grid grid-cols-2 gap-2 sm:mt-3 sm:flex sm:flex-wrap sm:items-center sm:gap-2">
            {navigationItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => {
                  const isItemActive =
                    item.to === "/entregas" ? isHistoryActive : isActive;

                  return cn(
                    "flex min-h-10 items-center justify-center rounded-lg border px-3 text-sm font-medium transition-colors",
                    isItemActive
                      ? "border-primary/40 bg-primary/20 text-primary"
                      : "border-border/70 bg-secondary/60 text-secondary-foreground hover:bg-secondary",
                  );
                }}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 py-5 sm:py-6">
        <Outlet />
      </main>
    </div>
  );
}
