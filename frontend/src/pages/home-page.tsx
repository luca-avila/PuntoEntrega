import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { useState } from "react";

export function HomePage() {
  const { user, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-4xl items-center px-4 py-10">
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Frontend base listo</CardTitle>
          <CardDescription>
            Esta pantalla confirma que el enrutado protegido y la sesión por cookie funcionan.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1 text-sm">
            <p>
              <span className="font-medium">Usuario:</span> {user?.email}
            </p>
            <p>
              <span className="font-medium">Organización:</span>{" "}
              {user?.organization_id ?? "Sin organización"}
            </p>
            <p>
              <span className="font-medium">Rol:</span> {user?.role ?? "Sin rol"}
            </p>
          </div>

          <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            Próximos pasos del plan frontend: contratos API, ubicaciones, productos, entregas e historial.
          </div>

          <Button disabled={isLoggingOut} onClick={handleLogout} variant="outline">
            {isLoggingOut ? "Cerrando sesión..." : "Cerrar sesión"}
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
