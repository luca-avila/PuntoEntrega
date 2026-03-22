import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <section className="page-section">
      <Card>
        <CardHeader>
          <CardTitle>Panel operativo</CardTitle>
          <CardDescription>
            Gestioná ubicaciones, productos y entregas desde este espacio.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <Link
            className="rounded-xl border border-border/80 bg-secondary/40 p-4 transition-colors hover:bg-secondary/70"
            to="/entregas/nueva"
          >
            <p className="font-medium">Nueva entrega</p>
            <p className="text-muted-foreground">
              Pantalla principal para registrar consignaciones.
            </p>
          </Link>

          <Link
            className="rounded-xl border border-border/80 bg-secondary/40 p-4 transition-colors hover:bg-secondary/70"
            to="/entregas"
          >
            <p className="font-medium">Historial</p>
            <p className="text-muted-foreground">
              Consultá entregas anteriores y estado de email.
            </p>
          </Link>

          <Link
            className="rounded-xl border border-border/80 bg-secondary/40 p-4 transition-colors hover:bg-secondary/70"
            to="/ubicaciones"
          >
            <p className="font-medium">Ubicaciones</p>
            <p className="text-muted-foreground">
              Alta y edición de puntos de entrega con mapa.
            </p>
          </Link>

          <Link
            className="rounded-xl border border-border/80 bg-secondary/40 p-4 transition-colors hover:bg-secondary/70"
            to="/productos"
          >
            <p className="font-medium">Productos</p>
            <p className="text-muted-foreground">
              Gestión del catálogo activo/inactivo para entregas.
            </p>
          </Link>
        </CardContent>
      </Card>
    </section>
  );
}
