import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { Link } from "react-router-dom";

interface QuickAccessItem {
  to: string;
  title: string;
  description: string;
  ownerOnly?: boolean;
}

const quickAccessItems: QuickAccessItem[] = [
  {
    to: "/entregas/nueva",
    title: "Nueva entrega",
    description: "Registrá consignaciones y enviá confirmación en un solo flujo.",
    ownerOnly: true,
  },
  {
    to: "/entregas",
    title: "Historial",
    description: "Revisá estado de envíos y últimas entregas registradas.",
  },
  {
    to: "/ubicaciones",
    title: "Ubicaciones",
    description: "Consultá y administrá puntos de entrega de tu organización.",
  },
  {
    to: "/productos",
    title: "Productos",
    description: "Gestioná catálogo o solicitá productos según tu perfil.",
  },
  {
    to: "/equipo",
    title: "Equipo",
    description: "Invitá miembros y seguí el estado de invitaciones.",
    ownerOnly: true,
  },
];

export function HomePage() {
  const { isOwner, user } = useAuth();
  const hasOrganization = Boolean(user?.organization_id);

  if (!hasOrganization) {
    return (
      <section className="page-section flex w-full justify-center">
        <Card className="w-full max-w-3xl overflow-hidden border-border/80 shadow-lg shadow-black/20">
          <div className="bg-gradient-to-r from-primary/15 via-primary/5 to-transparent">
            <CardHeader className="px-5 py-6 text-center sm:px-8 sm:py-7">
              <CardTitle className="text-xl sm:text-2xl">Cuenta lista para usar</CardTitle>
              <CardDescription className="mx-auto max-w-xl text-sm">
                Ya podés iniciar sesión como miembro base. Cuando quieras, creá tu organización
                desde este panel para habilitar la operación completa.
              </CardDescription>
            </CardHeader>
          </div>
          <CardContent className="grid gap-3 p-4 text-sm sm:grid-cols-2 sm:gap-4 sm:p-6">
            <Link
              className="group flex min-h-28 flex-col justify-between rounded-xl border border-border/80 bg-secondary/45 p-4 transition-all hover:-translate-y-0.5 hover:bg-secondary/70"
              to="/organizacion/crear"
            >
              <p className="text-sm font-semibold sm:text-base">Crear organización</p>
              <p className="text-muted-foreground group-hover:text-foreground/90">
                Definí nombre y comenzá como owner de tu espacio de trabajo.
              </p>
            </Link>
            <div className="flex min-h-28 flex-col justify-between rounded-xl border border-border/80 bg-secondary/25 p-4">
              <p className="text-sm font-semibold sm:text-base">¿Te invitaron por email?</p>
              <p className="text-muted-foreground">
                Abrí el enlace de invitación recibido para unirte a una organización existente.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    );
  }

  const visibleItems = quickAccessItems
    .filter((item) => !item.ownerOnly || isOwner)
    .map((item) =>
      !isOwner && item.to === "/productos"
        ? { ...item, title: "Solicitar productos" }
        : item,
    );

  return (
    <section className="page-section flex w-full justify-center">
      <Card className="w-full max-w-4xl overflow-hidden border-border/80 shadow-lg shadow-black/20">
        <div className="bg-gradient-to-r from-primary/15 via-primary/5 to-transparent">
          <CardHeader className="px-5 py-6 text-center sm:px-8 sm:py-7">
            <CardTitle className="text-xl sm:text-2xl">Panel operativo</CardTitle>
            <CardDescription className="mx-auto max-w-xl text-sm">
              Accedé rápido a los flujos habilitados para tu perfil dentro de la organización.
            </CardDescription>
          </CardHeader>
        </div>

        <CardContent className="grid gap-3 p-4 text-sm sm:grid-cols-2 sm:gap-4 sm:p-6">
          {visibleItems.map((item) => (
            <Link
              className="group flex min-h-28 flex-col justify-between rounded-xl border border-border/80 bg-secondary/45 p-4 transition-all hover:-translate-y-0.5 hover:bg-secondary/70"
              key={item.to}
              to={item.to}
            >
              <p className="text-sm font-semibold sm:text-base">{item.title}</p>
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
