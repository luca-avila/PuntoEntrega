import { authApi } from "@/api/auth-api";
import { ApiError } from "@/api/http-client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

type VerificationStatus = "verifying" | "success" | "error";

function mapVerificationError(error: unknown): string {
  if (error instanceof ApiError) {
    const detail =
      typeof error.payload === "object" && error.payload !== null && "detail" in error.payload
        ? (error.payload as Record<string, unknown>).detail
        : null;

    if (detail === "VERIFY_USER_BAD_TOKEN") {
      return "El enlace de verificación es inválido o venció.";
    }

    if (detail === "VERIFY_USER_ALREADY_VERIFIED") {
      return "La cuenta ya estaba verificada. Podés iniciar sesión.";
    }

    if (error.status >= 500) {
      return "No pudimos verificar la cuenta por un error del servidor. Intentá nuevamente.";
    }
  }

  return "No pudimos verificar tu cuenta. Revisá el enlace e intentá nuevamente.";
}

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<VerificationStatus>(
    token ? "verifying" : "error",
  );
  const [message, setMessage] = useState(
    token
      ? "Estamos verificando tu cuenta..."
      : "Falta el token de verificación en el enlace.",
  );

  useEffect(() => {
    let isCancelled = false;

    if (!token) {
      return;
    }

    void (async () => {
      try {
        await authApi.verifyEmail(token);
        if (isCancelled) {
          return;
        }
        setStatus("success");
        setMessage("Tu cuenta fue verificada correctamente.");
      } catch (error) {
        if (isCancelled) {
          return;
        }
        setStatus("error");
        setMessage(mapVerificationError(error));
      }
    })();

    return () => {
      isCancelled = true;
    };
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/20 px-4 py-10">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">Verificación de cuenta</CardTitle>
          <CardDescription className="text-center">{message}</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          {status === "verifying" ? (
            <p className="text-sm text-muted-foreground">Aguardá un instante...</p>
          ) : (
            <Link
              to={status === "success" ? "/login?verified=1" : "/login"}
              className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Ir a iniciar sesión
            </Link>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
