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
    title: "Historial de entregas",
    description: "Revisá estado de envíos y últimas entregas registradas.",
  },
  {
    to: "/pedidos",
    title: "Historial de pedidos",
    description: "Consultá solicitudes registradas y su estado de email.",
  },
  {
    to: "/ubicaciones",
    title: "Ubicaciones",
    description: "Consultá y administrá puntos de entrega de tu organización.",
    ownerOnly: true,
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
  const { isOwner, membership } = useAuth();
  const hasOrganization = Boolean(membership?.organization_id);

  if (!hasOrganization) {
    return (
      <section className="page-section">
        <Card className="w-full overflow-hidden border-border/80 shadow-lg shadow-black/20">
          <div className="bg-gradient-to-r from-primary/15 via-primary/5 to-transparent">
            <CardHeader className="px-6 py-7 text-center sm:px-10 sm:py-9">
              <CardTitle className="text-2xl sm:text-3xl">Cuenta lista para usar</CardTitle>
              <CardDescription className="mx-auto max-w-2xl">
                Ya podés iniciar sesión como miembro base. Cuando quieras, creá tu organización
                desde este panel para habilitar la operación completa.
              </CardDescription>
            </CardHeader>
          </div>
          <CardContent className="grid gap-4 p-5 sm:grid-cols-2 sm:p-7">
            <Link
              className="group flex min-h-36 flex-col justify-between rounded-xl border border-border/80 bg-secondary/45 p-5 transition-all hover:-translate-y-0.5 hover:bg-secondary/70"
              to="/organizacion/crear"
            >
              <p className="text-base font-semibold sm:text-lg">Crear organización</p>
              <p className="text-base leading-relaxed text-muted-foreground group-hover:text-foreground/90">
                Definí nombre y comenzá como owner de tu espacio de trabajo.
              </p>
            </Link>
            <div className="flex min-h-36 flex-col justify-between rounded-xl border border-border/80 bg-secondary/25 p-5">
              <p className="text-base font-semibold sm:text-lg">¿Te invitaron por email?</p>
              <p className="text-base leading-relaxed text-muted-foreground">
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
    <section className="page-section">
      <Card className="w-full overflow-hidden border-border/80 shadow-lg shadow-black/20">
        <div className="bg-gradient-to-r from-primary/15 via-primary/5 to-transparent">
          <CardHeader className="px-6 py-7 text-center sm:px-10 sm:py-9">
            <CardTitle className="text-2xl sm:text-3xl">Panel operativo</CardTitle>
            <CardDescription className="mx-auto max-w-2xl">
              Accedé rápido a los flujos habilitados para tu perfil dentro de la organización.
            </CardDescription>
          </CardHeader>
        </div>

        <CardContent className="grid gap-4 p-5 sm:grid-cols-2 sm:p-7 lg:grid-cols-3">
          {visibleItems.map((item) => (
            <Link
              className="group flex min-h-36 flex-col justify-between rounded-xl border border-border/80 bg-secondary/45 p-5 transition-all hover:-translate-y-0.5 hover:bg-secondary/70"
              key={item.to}
              to={item.to}
            >
              <p className="text-base font-semibold sm:text-lg">{item.title}</p>
              <p className="text-base leading-relaxed text-muted-foreground group-hover:text-foreground/90">
                {item.description}
              </p>
            </Link>
          ))}
        </CardContent>
      </Card>
    </section>
  );
}
