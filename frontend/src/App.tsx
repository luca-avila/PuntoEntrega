import { ProtectedLayout } from "@/components/layout/protected-layout";
import { AuthProvider } from "@/features/auth/auth-context";
import {
  OnboardingOnlyRoute,
  OwnerOnlyRoute,
  OrganizationRequiredRoute,
} from "@/features/auth/organization-route";
import { AcceptInvitationPage } from "@/pages/accept-invitation-page";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { DeliveriesHistoryPage } from "@/pages/deliveries-history-page";
import { DeliveryDetailPage } from "@/pages/delivery-detail-page";
import { HomePage } from "@/pages/home-page";
import { LocationFormPage } from "@/pages/location-form-page";
import { LocationsListPage } from "@/pages/locations-list-page";
import { LoginPage } from "@/pages/login-page";
import { NewDeliveryPage } from "@/pages/new-delivery-page";
import { OrganizationOnboardingPage } from "@/pages/organization-onboarding-page";
import { ProductFormPage } from "@/pages/product-form-page";
import { ProductsListPage } from "@/pages/products-list-page";
import { RegisterPage } from "@/pages/register-page";
import { ForgotPasswordPage } from "@/pages/forgot-password-page";
import { ResetPasswordPage } from "@/pages/reset-password-page";
import { TeamPage } from "@/pages/team-page";
import { VerifyEmailPage } from "@/pages/verify-email-page";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/iniciar-sesion" element={<LoginPage />} />
          <Route path="/registro" element={<RegisterPage />} />
          <Route path="/recuperar-contrasena" element={<ForgotPasswordPage />} />
          <Route path="/restablecer-contrasena" element={<ResetPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/verificar-email" element={<VerifyEmailPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/aceptar-invitacion" element={<AcceptInvitationPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<ProtectedLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route element={<OnboardingOnlyRoute />}>
                <Route
                  path="/organizacion/crear"
                  element={<OrganizationOnboardingPage />}
                />
                <Route
                  path="/onboarding/organizacion"
                  element={<Navigate replace to="/organizacion/crear" />}
                />
              </Route>

              <Route element={<OrganizationRequiredRoute />}>
                <Route path="/entregas" element={<DeliveriesHistoryPage />} />
                <Route path="/entregas/:deliveryId" element={<DeliveryDetailPage />} />

                <Route path="/ubicaciones" element={<LocationsListPage />} />
                <Route path="/productos" element={<ProductsListPage />} />
                <Route element={<OwnerOnlyRoute />}>
                  <Route path="/entregas/nueva" element={<NewDeliveryPage />} />
                  <Route
                    path="/ubicaciones/nueva"
                    element={<LocationFormPage mode="create" />}
                  />
                  <Route
                    path="/ubicaciones/:locationId/editar"
                    element={<LocationFormPage mode="edit" />}
                  />
                  <Route
                    path="/productos/nuevo"
                    element={<ProductFormPage mode="create" />}
                  />
                  <Route
                    path="/productos/:productId/editar"
                    element={<ProductFormPage mode="edit" />}
                  />
                  <Route path="/equipo" element={<TeamPage />} />
                </Route>
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate replace to="/" />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
