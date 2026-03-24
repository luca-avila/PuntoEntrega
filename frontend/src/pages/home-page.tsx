import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "react-router-dom";

const quickAccessItems = [
  {
    to: "/entregas/nueva",
    title: "Nueva entrega",
    description: "Registrá consignaciones y enviá confirmación en un solo flujo.",
  },
  {
    to: "/entregas",
    title: "Historial",
    description: "Revisá estado de envíos y últimas entregas registradas.",
  },
  {
    to: "/ubicaciones",
    title: "Ubicaciones",
    description: "Administrá puntos de entrega con geocodificación precisa.",
  },
  {
    to: "/productos",
    title: "Productos",
    description: "Mantené activo el catálogo para futuras consignaciones.",
  },
];

export function HomePage() {
  return (
    <section className="page-section">
      <Card className="mx-auto w-full max-w-5xl overflow-hidden border-border/80 shadow-lg shadow-black/20">
        <div className="bg-gradient-to-r from-primary/15 via-primary/5 to-transparent">
          <CardHeader className="px-6 py-8 text-center sm:px-10">
            <CardTitle className="text-2xl sm:text-3xl">Panel operativo</CardTitle>
            <CardDescription className="mx-auto max-w-2xl text-sm sm:text-base">
              Accedé rápido a entregas, ubicaciones y productos desde un panel más claro y ordenado.
            </CardDescription>
          </CardHeader>
        </div>

        <CardContent className="grid gap-4 p-5 text-sm sm:grid-cols-2 sm:gap-5 sm:p-8">
          {quickAccessItems.map((item) => (
            <Link
              className="group flex min-h-36 flex-col justify-between rounded-2xl border border-border/80 bg-secondary/45 p-5 transition-all hover:-translate-y-0.5 hover:bg-secondary/70"
              key={item.to}
              to={item.to}
            >
              <p className="text-base font-semibold">{item.title}</p>
              <p className="text-muted-foreground group-hover:text-foreground/90">
                {item.description}
              </p>
            </Link>
          ))}
        </CardContent>
      </Card>
    </section>
  );
}
