import { invitationsApi, type OrganizationInvitationAcceptInfoRead } from "@/api";
import { ApiError } from "@/api/http-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/errors";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";

interface AcceptNewAccountFormValues {
  password: string;
  passwordConfirm: string;
}

const statusTitleMap: Record<OrganizationInvitationAcceptInfoRead["status"], string> = {
  valid: "Invitación válida",
  invalid: "Invitación inválida",
  expired: "Invitación expirada",
  cancelled: "Invitación cancelada",
  accepted: "Invitación ya aceptada",
};

const statusDescriptionMap: Record<OrganizationInvitationAcceptInfoRead["status"], string> = {
  valid: "Podés unirte a la organización desde esta pantalla.",
  invalid: "El token no es válido. Verificá el enlace recibido.",
  expired: "Esta invitación venció. Pedí una nueva invitación al owner.",
  cancelled: "La invitación fue cancelada por el owner.",
  accepted: "Esta invitación ya fue utilizada.",
};

export function AcceptInvitationPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { status } = useAuth();

  const token = (searchParams.get("token") ?? "").trim();

  const [invitationInfo, setInvitationInfo] = useState<OrganizationInvitationAcceptInfoRead | null>(null);
  const [isLoadingInfo, setIsLoadingInfo] = useState(true);
  const [acceptError, setAcceptError] = useState<string | null>(null);
  const [acceptSuccessMessage, setAcceptSuccessMessage] = useState<string | null>(null);
  const [isAcceptingAuthenticated, setIsAcceptingAuthenticated] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AcceptNewAccountFormValues>({
    defaultValues: {
      password: "",
      passwordConfirm: "",
    },
  });

  const loadAcceptInfo = useCallback(async () => {
    setIsLoadingInfo(true);
    setAcceptError(null);
    setAcceptSuccessMessage(null);

    if (!token) {
      setInvitationInfo({
        status: "invalid",
        is_valid: false,
        invited_email: null,
        organization_id: null,
        organization_name: null,
        expires_at: null,
      });
      setIsLoadingInfo(false);
      return;
    }

    try {
      const info = await invitationsApi.getAcceptInfo(token);
      setInvitationInfo(info);
    } catch (error) {
      setAcceptError(getApiErrorMessage(error, "No pudimos validar la invitación."));
      setInvitationInfo({
        status: "invalid",
        is_valid: false,
        invited_email: null,
        organization_id: null,
        organization_name: null,
        expires_at: null,
      });
    } finally {
      setIsLoadingInfo(false);
    }
  }, [token]);

  useEffect(() => {
    void loadAcceptInfo();
  }, [loadAcceptInfo]);

  const loginRedirectPath = useMemo(() => {
    const currentPath = `/aceptar-invitacion${token ? `?token=${encodeURIComponent(token)}` : ""}`;
    return `/iniciar-sesion?next=${encodeURIComponent(currentPath)}`;
  }, [token]);

  const onSubmitNewAccount = handleSubmit(async (formValues) => {
    setAcceptError(null);
    setAcceptSuccessMessage(null);

    if (formValues.password !== formValues.passwordConfirm) {
      setError("passwordConfirm", {
        type: "validate",
        message: "Las contraseñas no coinciden.",
      });
      return;
    }

    try {
      await invitationsApi.acceptNewAccount({
        token,
        password: formValues.password,
        password_confirm: formValues.passwordConfirm,
      });
      setAcceptSuccessMessage("Invitación aceptada. Ahora podés iniciar sesión con tu cuenta.");
      reset();
      await loadAcceptInfo();
    } catch (error) {
      setAcceptError(
        getApiErrorMessage(error, "No pudimos aceptar la invitación con una cuenta nueva."),
      );
    }
  });

  const handleAcceptAuthenticated = async () => {
    setIsAcceptingAuthenticated(true);
    setAcceptError(null);
    setAcceptSuccessMessage(null);
    try {
      await invitationsApi.acceptAuthenticated({ token });
      setAcceptSuccessMessage("Invitación aceptada correctamente.");
      await loadAcceptInfo();
      navigate("/", { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        navigate(loginRedirectPath, { replace: true });
        return;
      }

      setAcceptError(
        getApiErrorMessage(error, "No pudimos aceptar la invitación con tu sesión actual."),
      );
    } finally {
      setIsAcceptingAuthenticated(false);
    }
  };

  if (isLoadingInfo) {
    return (
      <div className="auth-shell">
        <Card className="w-full max-w-xl">
          <CardContent className="p-6 text-sm text-muted-foreground">
            Validando invitación...
          </CardContent>
        </Card>
      </div>
    );
  }

  const info = invitationInfo;
  const isValid = Boolean(info?.is_valid);

  return (
    <div className="auth-shell">
      <div className="w-full max-w-xl space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>{statusTitleMap[info?.status ?? "invalid"]}</CardTitle>
            <CardDescription>{statusDescriptionMap[info?.status ?? "invalid"]}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              <span className="font-medium">Organización:</span>{" "}
              {info?.organization_name ?? "-"}
            </p>
            <p>
              <span className="font-medium">Email invitado:</span>{" "}
              {info?.invited_email ?? "-"}
            </p>
          </CardContent>
        </Card>

        {acceptSuccessMessage ? (
          <p className="feedback-success">{acceptSuccessMessage}</p>
        ) : null}
        {acceptError ? (
          <p className="feedback-error">{acceptError}</p>
        ) : null}

        {isValid ? (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Aceptar con cuenta existente</CardTitle>
                <CardDescription>
                  Ingresá con el mismo email invitado para unirte a la organización.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {status === "authenticated" ? (
                  <Button
                    onClick={() => void handleAcceptAuthenticated()}
                    disabled={isAcceptingAuthenticated}
                    className="w-full"
                  >
                    {isAcceptingAuthenticated ? "Aceptando..." : "Aceptar invitación con mi cuenta"}
                  </Button>
                ) : (
                  <Button className="w-full" onClick={() => navigate(loginRedirectPath)}>
                    Iniciar sesión para aceptar
                  </Button>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Aceptar con cuenta nueva</CardTitle>
                <CardDescription>
                  Creá tu contraseña para activar la cuenta invitada.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form className="space-y-3" noValidate onSubmit={onSubmitNewAccount}>
                  <div className="space-y-2">
                    <Label htmlFor="new-password">Contraseña</Label>
                    <Input
                      id="new-password"
                      type="password"
                      autoComplete="new-password"
                      placeholder="********"
                      {...register("password", {
                        required: "La contraseña es obligatoria.",
                        minLength: {
                          value: 8,
                          message: "Debe tener al menos 8 caracteres.",
                        },
                      })}
                    />
                    {errors.password ? (
                      <p className="text-sm text-destructive">{errors.password.message}</p>
                    ) : null}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="new-password-confirm">Confirmar contraseña</Label>
                    <Input
                      id="new-password-confirm"
                      type="password"
                      autoComplete="new-password"
                      placeholder="********"
                      {...register("passwordConfirm", {
                        required: "Confirmá tu contraseña.",
                      })}
                    />
                    {errors.passwordConfirm ? (
                      <p className="text-sm text-destructive">{errors.passwordConfirm.message}</p>
                    ) : null}
                  </div>

                  <Button className="w-full" disabled={isSubmitting} type="submit">
                    {isSubmitting ? "Aceptando..." : "Aceptar con cuenta nueva"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </>
        ) : (
          <Card>
            <CardContent className="p-6">
              <Button className="w-full" onClick={() => navigate("/iniciar-sesion")}>
                Volver a iniciar sesión
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
