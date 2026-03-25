import {
  invitationsApi,
  organizationMembersApi,
  type OrganizationInvitationRead,
  type OrganizationMemberRead,
} from "@/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getApiErrorMessage } from "@/lib/errors";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";

interface InviteFormValues {
  email: string;
}

const invitationStatusLabel: Record<OrganizationInvitationRead["status"], string> = {
  pending: "Pendiente",
  accepted: "Aceptada",
  expired: "Expirada",
  cancelled: "Cancelada",
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function getInvitationStatusClass(status: OrganizationInvitationRead["status"]): string {
  switch (status) {
    case "pending":
      return "status-chip status-chip-muted";
    case "accepted":
      return "status-chip status-chip-success";
    case "expired":
      return "status-chip status-chip-danger";
    case "cancelled":
      return "status-chip status-chip-muted";
    default:
      return "status-chip status-chip-muted";
  }
}

export function TeamPage() {
  const [members, setMembers] = useState<OrganizationMemberRead[]>([]);
  const [invitations, setInvitations] = useState<OrganizationInvitationRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCancellingId, setIsCancellingId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteSuccessMessage, setInviteSuccessMessage] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<InviteFormValues>({
    defaultValues: {
      email: "",
    },
  });

  const loadTeamData = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [membersData, invitationsData] = await Promise.all([
        organizationMembersApi.list(),
        invitationsApi.list(),
      ]);
      setMembers(membersData);
      setInvitations(invitationsData);
    } catch (error) {
      setLoadError(getApiErrorMessage(error, "No pudimos cargar la información del equipo."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTeamData();
  }, [loadTeamData]);

  const pendingInvitationsCount = useMemo(
    () => invitations.filter((invitation) => invitation.status === "pending").length,
    [invitations],
  );

  const onSubmitInvite = handleSubmit(async (formValues) => {
    setInviteError(null);
    setInviteSuccessMessage(null);
    try {
      const invitation = await invitationsApi.create({
        email: formValues.email,
      });
      setInvitations((current) => [invitation, ...current.filter((item) => item.id !== invitation.id)]);
      setInviteSuccessMessage(`Invitación enviada a ${invitation.invited_email}.`);
      reset();
    } catch (error) {
      setInviteError(getApiErrorMessage(error, "No pudimos enviar la invitación."));
    }
  });

  const handleCancelInvitation = async (invitationId: string) => {
    setIsCancellingId(invitationId);
    setInviteError(null);
    setInviteSuccessMessage(null);
    try {
      const updatedInvitation = await invitationsApi.cancel(invitationId);
      setInvitations((current) =>
        current.map((invitation) =>
          invitation.id === invitationId ? updatedInvitation : invitation,
        ),
      );
    } catch (error) {
      setInviteError(getApiErrorMessage(error, "No pudimos cancelar la invitación."));
    } finally {
      setIsCancellingId(null);
    }
  };

  return (
    <section className="page-section">
      <div>
        <h2 className="page-title">Equipo</h2>
        <p className="page-description">
          Gestioná miembros de tu organización e invitá nuevos usuarios por email.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Miembros</CardTitle>
            <CardDescription>
              {members.length} usuario(s) en la organización.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoading ? (
              <p className="text-sm text-muted-foreground">Cargando miembros...</p>
            ) : null}

            {!isLoading && members.length === 0 ? (
              <p className="text-sm text-muted-foreground">Todavía no hay miembros cargados.</p>
            ) : null}

            {!isLoading && members.length > 0 ? (
              <div className="space-y-2">
                {members.map((member) => (
                  <div
                    key={member.id}
                    className="rounded-lg border border-border/70 bg-secondary/50 px-3 py-2"
                  >
                    <p className="text-sm font-medium">{member.email}</p>
                    <p className="text-xs text-muted-foreground">
                      {member.is_verified ? "Verificado" : "Sin verificar"} ·{" "}
                      {member.is_active ? "Activo" : "Inactivo"} · Alta:{" "}
                      {formatDateTime(member.created_at)}
                    </p>
                  </div>
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Invitar miembro</CardTitle>
            <CardDescription>
              Invitaciones pendientes: {pendingInvitationsCount}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-3" noValidate onSubmit={onSubmitInvite}>
              <div className="space-y-2">
                <Label htmlFor="invite-email">Email</Label>
                <Input
                  id="invite-email"
                  type="email"
                  placeholder="nombre@empresa.com"
                  autoComplete="email"
                  {...register("email", {
                    required: "El email es obligatorio.",
                    setValueAs: (value: string) => value.trim().toLowerCase(),
                    pattern: {
                      value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                      message: "Ingresá un email válido.",
                    },
                  })}
                />
                {errors.email ? (
                  <p className="text-sm text-destructive">{errors.email.message}</p>
                ) : null}
              </div>

              {inviteSuccessMessage ? (
                <p className="feedback-success">{inviteSuccessMessage}</p>
              ) : null}
              {inviteError ? (
                <p className="feedback-error">{inviteError}</p>
              ) : null}

              <Button className="w-full" disabled={isSubmitting} type="submit">
                {isSubmitting ? "Enviando invitación..." : "Enviar invitación"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Invitaciones</CardTitle>
          <CardDescription>
            Estado de invitaciones enviadas y acciones disponibles.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Cargando invitaciones...</p>
          ) : null}

          {loadError ? (
            <p className="feedback-error">{loadError}</p>
          ) : null}

          {!isLoading && !loadError && invitations.length === 0 ? (
            <p className="text-sm text-muted-foreground">Todavía no hay invitaciones.</p>
          ) : null}

          {!isLoading && invitations.length > 0 ? (
            <div className="space-y-2">
              {invitations.map((invitation) => (
                <div
                  key={invitation.id}
                  className="flex flex-col gap-3 rounded-lg border border-border/70 bg-secondary/50 p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="space-y-1">
                    <p className="text-sm font-medium">{invitation.invited_email}</p>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span className={getInvitationStatusClass(invitation.status)}>
                        {invitationStatusLabel[invitation.status]}
                      </span>
                      <span>Creada: {formatDateTime(invitation.created_at)}</span>
                      <span>Expira: {formatDateTime(invitation.expires_at)}</span>
                    </div>
                  </div>

                  <Button
                    onClick={() => void handleCancelInvitation(invitation.id)}
                    variant="outline"
                    size="sm"
                    disabled={invitation.status !== "pending" || isCancellingId === invitation.id}
                  >
                    {isCancellingId === invitation.id ? "Cancelando..." : "Cancelar"}
                  </Button>
                </div>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
