import { authApi } from "@/api/auth-api";
import { ApiError } from "@/api/http-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

interface ResetPasswordFormValues {
  password: string;
  confirmPassword: string;
}

function mapResetPasswordErrorToMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const detail =
      typeof error.payload === "object" && error.payload !== null && "detail" in error.payload
        ? (error.payload as Record<string, unknown>).detail
        : null;

    if (detail === "RESET_PASSWORD_BAD_TOKEN") {
      return "El enlace de recuperación es inválido o venció.";
    }

    if (typeof detail === "object" && detail !== null && "code" in detail && "reason" in detail) {
      const code = (detail as Record<string, unknown>).code;
      const reason = (detail as Record<string, unknown>).reason;
      if (code === "RESET_PASSWORD_INVALID_PASSWORD" && typeof reason === "string") {
        return `La contraseña no cumple los requisitos: ${reason}`;
      }
    }

    if (error.status >= 500) {
      return "No pudimos restablecer la contraseña por un error del servidor. Intentá nuevamente.";
    }
  }

  return "No pudimos restablecer la contraseña. Verificá el enlace e intentá nuevamente.";
}

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormValues>({
    defaultValues: {
      password: "",
      confirmPassword: "",
    },
  });

  const onSubmit = handleSubmit(async (formValues) => {
    setSubmitError(null);

    if (!token) {
      setSubmitError("Falta el token de recuperación en el enlace.");
      return;
    }

    if (formValues.password !== formValues.confirmPassword) {
      setError("confirmPassword", {
        type: "validate",
        message: "Las contraseñas no coinciden.",
      });
      return;
    }

    try {
      await authApi.resetPassword(token, formValues.password);
      navigate("/iniciar-sesion?passwordReset=1", { replace: true });
    } catch (error) {
      setSubmitError(mapResetPasswordErrorToMessage(error));
    }
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/20 px-4 py-10">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">Restablecer contraseña</CardTitle>
          <CardDescription className="text-center">
            Elegí una nueva contraseña para tu cuenta.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!token ? (
            <div className="space-y-4">
              <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                El enlace es inválido porque no contiene token.
              </p>
              <p className="text-center text-sm text-muted-foreground">
                <Link className="text-primary underline-offset-4 hover:underline" to="/recuperar-contrasena">
                  Solicitar nuevo enlace
                </Link>
              </p>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="password">Nueva contraseña</Label>
                <Input
                  id="password"
                  placeholder="********"
                  type="password"
                  autoComplete="new-password"
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
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Usá al menos 8 caracteres, con mayúscula, minúscula, número y símbolo.
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirmar nueva contraseña</Label>
                <Input
                  id="confirmPassword"
                  placeholder="********"
                  type="password"
                  autoComplete="new-password"
                  {...register("confirmPassword", {
                    required: "Confirmá tu contraseña.",
                  })}
                />
                {errors.confirmPassword ? (
                  <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>
                ) : null}
              </div>

              {submitError ? (
                <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {submitError}
                </p>
              ) : null}

              <Button className="w-full" disabled={isSubmitting} type="submit">
                {isSubmitting ? "Actualizando..." : "Actualizar contraseña"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
