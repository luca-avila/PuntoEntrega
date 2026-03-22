import { authApi } from "@/api/auth-api";
import { ApiError } from "@/api/http-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";

interface ForgotPasswordFormValues {
  email: string;
}

function mapForgotPasswordErrorToMessage(error: unknown): string {
  if (error instanceof ApiError && error.status >= 500) {
    return "No pudimos procesar la solicitud por un error del servidor. Intentá nuevamente.";
  }

  return "No pudimos procesar la solicitud. Verificá el email e intentá nuevamente.";
}

export function ForgotPasswordPage() {
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormValues>({
    defaultValues: {
      email: "",
    },
  });

  const onSubmit = handleSubmit(async (formValues) => {
    setSubmitError(null);

    try {
      await authApi.requestPasswordReset(formValues.email);
      setIsSuccess(true);
    } catch (error) {
      setSubmitError(mapForgotPasswordErrorToMessage(error));
    }
  });

  return (
    <div className="auth-shell">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">Recuperar contraseña</CardTitle>
          <CardDescription className="text-center">
            Ingresá tu email y te enviaremos un enlace para restablecerla.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" noValidate onSubmit={onSubmit}>
            {isSuccess ? (
              <p className="feedback-success">
                Si el email existe, enviamos un enlace para restablecer la contraseña.
              </p>
            ) : null}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
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

            {submitError ? (
              <p className="feedback-error">
                {submitError}
              </p>
            ) : null}

            <Button className="w-full" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Enviando..." : "Enviar enlace"}
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            <Link className="text-primary underline-offset-4 hover:underline" to="/iniciar-sesion">
              Volver a iniciar sesión
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
