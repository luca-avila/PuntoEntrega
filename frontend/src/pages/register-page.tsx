import { authApi } from "@/api/auth-api";
import { ApiError } from "@/api/http-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";

interface RegisterFormValues {
  email: string;
  password: string;
  confirmPassword: string;
}

function mapRegisterErrorToMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const detail =
      typeof error.payload === "object" && error.payload !== null && "detail" in error.payload
        ? (error.payload as Record<string, unknown>).detail
        : null;

    if (detail === "REGISTER_USER_ALREADY_EXISTS") {
      return "Ya existe una cuenta con ese email.";
    }

    if (typeof detail === "object" && detail !== null && "code" in detail && "reason" in detail) {
      const code = (detail as Record<string, unknown>).code;
      const reason = (detail as Record<string, unknown>).reason;

      if (code === "REGISTER_INVALID_PASSWORD" && typeof reason === "string") {
        return `La contraseña no cumple los requisitos: ${reason}`;
      }
    }

    if (error.status >= 500) {
      return "No pudimos registrar la cuenta por un error del servidor. Intentá nuevamente.";
    }
  }

  return "No pudimos crear la cuenta. Verificá los datos e intentá nuevamente.";
}

export function RegisterPage() {
  const navigate = useNavigate();
  const { status } = useAuth();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  useEffect(() => {
    if (status === "authenticated") {
      navigate("/", { replace: true });
    }
  }, [status, navigate]);

  const onSubmit = handleSubmit(async (formValues) => {
    setSubmitError(null);

    if (formValues.password !== formValues.confirmPassword) {
      setError("confirmPassword", {
        type: "validate",
        message: "Las contraseñas no coinciden.",
      });
      return;
    }

    try {
      await authApi.register({
        email: formValues.email,
        password: formValues.password,
      });
      const nextSearch = new URLSearchParams({
        registered: "1",
        email: formValues.email,
      });
      navigate(`/login?${nextSearch.toString()}`, { replace: true });
    } catch (error) {
      setSubmitError(mapRegisterErrorToMessage(error));
    }
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/20 px-4 py-10">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">Crear cuenta</CardTitle>
          <CardDescription className="text-center">
            Registrá tu organización para empezar a usar PuntoEntrega.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                placeholder="nombre@empresa.com"
                type="email"
                autoComplete="email"
                {...register("email", {
                  required: "El email es obligatorio.",
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

            <div className="space-y-2">
              <Label htmlFor="password">Contraseña</Label>
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
              <Label htmlFor="confirmPassword">Confirmar contraseña</Label>
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

            <Button className="w-full" disabled={isSubmitting || status === "loading"} type="submit">
              {isSubmitting ? "Creando cuenta..." : "Crear cuenta"}
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            ¿Ya tenés cuenta?{" "}
            <Link className="text-primary underline-offset-4 hover:underline" to="/login">
              Iniciar sesión
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
