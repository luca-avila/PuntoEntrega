import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const navigationItems = [
  { to: "/entregas/nueva", label: "Nueva entrega" },
  { to: "/entregas", label: "Historial" },
  { to: "/ubicaciones", label: "Ubicaciones" },
  { to: "/productos", label: "Productos" },
  { to: "/", label: "Inicio" },
];

export function ProtectedLayout() {
  const { user, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const location = useLocation();
  const isHistoryActive =
    location.pathname === "/entregas" ||
    (location.pathname.startsWith("/entregas/") &&
      !location.pathname.startsWith("/entregas/nueva"));

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <div className="min-h-screen bg-muted/20">
      <header className="border-b bg-background">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold">PuntoEntrega</h1>
            <p className="text-sm text-muted-foreground">{user?.email}</p>
          </div>

          <div className="flex items-center gap-2">
            <nav className="flex flex-wrap items-center gap-2">
              {navigationItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => {
                    const isItemActive =
                      item.to === "/entregas" ? isHistoryActive : isActive;

                    return cn(
                      "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      isItemActive
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary text-secondary-foreground hover:bg-secondary/80",
                    );
                  }}
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <Button disabled={isLoggingOut} onClick={handleLogout} variant="outline">
              {isLoggingOut ? "Cerrando..." : "Salir"}
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
