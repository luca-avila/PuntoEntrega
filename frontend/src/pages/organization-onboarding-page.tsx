import { organizationsApi } from "@/api/organizations-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/errors";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

interface OrganizationOnboardingFormValues {
  name: string;
}

export function OrganizationOnboardingPage() {
  const navigate = useNavigate();
  const { status, user, refreshSession } = useAuth();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<OrganizationOnboardingFormValues>({
    defaultValues: {
      name: "",
    },
  });

  useEffect(() => {
    if (status === "authenticated" && user?.organization_id) {
      navigate("/", { replace: true });
    }
  }, [status, user, navigate]);

  const onSubmit = handleSubmit(async (formValues) => {
    setSubmitError(null);
    try {
      await organizationsApi.create({
        name: formValues.name,
      });
      await refreshSession();
      navigate("/", { replace: true });
    } catch (error) {
      setSubmitError(
        getApiErrorMessage(
          error,
          "No pudimos crear tu organización. Revisá el nombre e intentá nuevamente.",
        ),
      );
    }
  });

  return (
    <div className="auth-shell">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">Creá tu organización</CardTitle>
          <CardDescription className="text-center">
            Para continuar, configurá el nombre de tu organización.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" noValidate onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="organization-name">Nombre de la organización</Label>
              <Input
                id="organization-name"
                placeholder="Ej: PuntoEntrega Centro"
                autoComplete="organization"
                {...register("name", {
                  required: "El nombre de la organización es obligatorio.",
                  setValueAs: (value: string) => value.trim(),
                  minLength: {
                    value: 1,
                    message: "El nombre de la organización es obligatorio.",
                  },
                  maxLength: {
                    value: 255,
                    message: "El nombre no puede superar los 255 caracteres.",
                  },
                })}
              />
              {errors.name ? (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              ) : null}
            </div>

            {submitError ? (
              <p className="feedback-error">
                {submitError}
              </p>
            ) : null}

            <Button className="w-full" disabled={isSubmitting || status === "loading"} type="submit">
              {isSubmitting ? "Creando organización..." : "Crear organización"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
