import { ApiError } from "@/api/http-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

interface LoginFormValues {
  email: string;
  password: string;
}

const LOGIN_ERROR_MESSAGES: Record<string, string> = {
  LOGIN_BAD_CREDENTIALS: "Email o contraseña inválidos.",
  LOGIN_USER_NOT_VERIFIED:
    "Tu cuenta todavía no está verificada. Revisá tu correo para activarla.",
};

function mapLoginErrorToMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const detail =
      typeof error.payload === "object" && error.payload !== null && "detail" in error.payload
        ? (error.payload as Record<string, unknown>).detail
        : null;

    if (typeof detail === "string" && detail in LOGIN_ERROR_MESSAGES) {
      return LOGIN_ERROR_MESSAGES[detail];
    }

    if (error.status >= 500) {
      return "No pudimos iniciar sesión por un error del servidor. Intentá nuevamente.";
    }
  }

  return "No pudimos iniciar sesión. Verificá tus datos e intentá nuevamente.";
}

export function LoginPage() {
  const navigate = useNavigate();
  const { status, login } = useAuth();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    defaultValues: {
      email: "",
      password: "",
    },
  });

  useEffect(() => {
    if (status === "authenticated") {
      navigate("/", { replace: true });
    }
  }, [status, navigate]);

  const onSubmit = handleSubmit(async (formValues) => {
    setSubmitError(null);
    try {
      await login(formValues);
      navigate("/", { replace: true });
    } catch (error) {
      setSubmitError(mapLoginErrorToMessage(error));
    }
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/20 px-4 py-10">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">Iniciar sesión</CardTitle>
          <CardDescription className="text-center">
            Accedé a tu organización para continuar.
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
                autoComplete="current-password"
                {...register("password", {
                  required: "La contraseña es obligatoria.",
                })}
              />
              {errors.password ? (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              ) : null}
            </div>

            {submitError ? (
              <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {submitError}
              </p>
            ) : null}

            <Button className="w-full" disabled={isSubmitting || status === "loading"} type="submit">
              {isSubmitting ? "Ingresando..." : "Entrar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
