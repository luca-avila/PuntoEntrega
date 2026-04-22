import { ApiError } from "@/api/http-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";

interface LoginFormValues {
  email: string;
  password: string;
}

const LOGIN_ERROR_MESSAGES: Record<string, string> = {
  LOGIN_BAD_CREDENTIALS: "Email o contraseña inválidos.",
  LOGIN_USER_NOT_VERIFIED:
    "Tu cuenta todavía no está verificada. Revisá tu correo para activarla.",
};

const DISALLOWED_NEXT_PATHS = [
  "/iniciar-sesion",
  "/registro",
  "/recuperar-contrasena",
  "/restablecer-contrasena",
  "/reset-password",
];

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

function sanitizeNextPath(nextPath: string | null): string | null {
  if (!nextPath) {
    return null;
  }

  if (!nextPath.startsWith("/") || nextPath.startsWith("//")) {
    return null;
  }

  const lowerCasedPath = nextPath.toLowerCase();
  const pointsToAuthRoute = DISALLOWED_NEXT_PATHS.some(
    (path) => lowerCasedPath === path || lowerCasedPath.startsWith(`${path}?`),
  );
  if (pointsToAuthRoute) {
    return null;
  }

  return nextPath;
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { status, login } = useAuth();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const isRegistered = searchParams.get("registered") === "1";
  const isVerified = searchParams.get("verified") === "1";
  const isPasswordReset = searchParams.get("passwordReset") === "1";
  const nextPath = sanitizeNextPath(searchParams.get("next"));
  const fromState = (
    location.state as
      | {
          from?: {
            pathname?: string;
            search?: string;
          };
        }
      | undefined
  )?.from;
  const redirectTarget = nextPath
    ? nextPath
    : fromState?.pathname
      ? `${fromState.pathname}${fromState.search ?? ""}`
      : "/";

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
      navigate(redirectTarget, { replace: true });
    }
  }, [status, navigate, redirectTarget]);

  const onSubmit = handleSubmit(async (formValues) => {
    setSubmitError(null);
    try {
      await login(formValues);
      navigate(redirectTarget, { replace: true });
    } catch (error) {
      setSubmitError(mapLoginErrorToMessage(error));
    }
  });

  return (
    <div className="auth-shell">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">Iniciar sesión</CardTitle>
          <CardDescription className="text-center">
            Accedé a tu organización para continuar.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" noValidate onSubmit={onSubmit}>
            {isRegistered ? (
              <p className="feedback-success">
                Cuenta creada. Revisá tu correo para verificarla y después iniciá sesión.
              </p>
            ) : null}

            {isVerified ? (
              <p className="feedback-success">
                Cuenta verificada. Ya podés iniciar sesión.
              </p>
            ) : null}

            {isPasswordReset ? (
              <p className="feedback-success">
                Contraseña actualizada. Ya podés iniciar sesión.
              </p>
            ) : null}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                autoFocus
                id="email"
                placeholder="nombre@empresa.com"
                type="email"
                autoComplete="email"
                {...register("email", {
                  required: "El email es obligatorio.",
                  setValueAs: (value: string) => value.trim(),
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
              <p className="text-right text-sm">
                <Link className="text-primary underline-offset-4 hover:underline" to="/recuperar-contrasena">
                  Olvidé mi contraseña
                </Link>
              </p>
            </div>

            {submitError ? (
              <p className="feedback-error">
                {submitError}
              </p>
            ) : null}

            <Button className="w-full" disabled={isSubmitting || status === "loading"} type="submit">
              {isSubmitting ? "Ingresando..." : "Entrar"}
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            ¿No tenés cuenta?{" "}
            <Link className="text-primary underline-offset-4 hover:underline" to="/registro">
              Crear cuenta
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
