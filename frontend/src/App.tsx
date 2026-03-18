import { ProtectedLayout } from "@/components/layout/protected-layout";
import { AuthProvider } from "@/features/auth/auth-context";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { DeliveriesHistoryPage } from "@/pages/deliveries-history-page";
import { DeliveryDetailPage } from "@/pages/delivery-detail-page";
import { HomePage } from "@/pages/home-page";
import { LocationFormPage } from "@/pages/location-form-page";
import { LocationsListPage } from "@/pages/locations-list-page";
import { LoginPage } from "@/pages/login-page";
import { NewDeliveryPage } from "@/pages/new-delivery-page";
import { ProductFormPage } from "@/pages/product-form-page";
import { ProductsListPage } from "@/pages/products-list-page";
import { RegisterPage } from "@/pages/register-page";
import { VerifyEmailPage } from "@/pages/verify-email-page";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<ProtectedLayout />}>
              <Route path="/" element={<HomePage />} />

              <Route path="/deliveries" element={<DeliveriesHistoryPage />} />
              <Route path="/deliveries/nueva" element={<NewDeliveryPage />} />
              <Route path="/deliveries/:deliveryId" element={<DeliveryDetailPage />} />

              <Route path="/locations" element={<LocationsListPage />} />
              <Route
                path="/locations/nueva"
                element={<LocationFormPage mode="create" />}
              />
              <Route
                path="/locations/:locationId/editar"
                element={<LocationFormPage mode="edit" />}
              />

              <Route path="/products" element={<ProductsListPage />} />
              <Route
                path="/products/nuevo"
                element={<ProductFormPage mode="create" />}
              />
              <Route
                path="/products/:productId/editar"
                element={<ProductFormPage mode="edit" />}
              />
            </Route>
          </Route>

          <Route path="*" element={<Navigate replace to="/" />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
