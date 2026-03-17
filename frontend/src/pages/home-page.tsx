import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <section className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Panel operativo</CardTitle>
          <CardDescription>
            Gestioná ubicaciones, productos y entregas desde este espacio.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
          <Link
            className="rounded-md border p-4 transition-colors hover:bg-muted"
            to="/locations"
          >
            <p className="font-medium">Ubicaciones</p>
            <p className="text-muted-foreground">
              Alta y edición de puntos de entrega con mapa.
            </p>
          </Link>

          <Link
            className="rounded-md border p-4 transition-colors hover:bg-muted"
            to="/products"
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
