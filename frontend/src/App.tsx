import { ProtectedLayout } from "@/components/layout/protected-layout";
import { AuthProvider } from "@/features/auth/auth-context";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { HomePage } from "@/pages/home-page";
import { LocationFormPage } from "@/pages/location-form-page";
import { LocationsListPage } from "@/pages/locations-list-page";
import { LoginPage } from "@/pages/login-page";
import { NewDeliveryPage } from "@/pages/new-delivery-page";
import { ProductFormPage } from "@/pages/product-form-page";
import { ProductsListPage } from "@/pages/products-list-page";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<ProtectedLayout />}>
              <Route path="/" element={<HomePage />} />

              <Route path="/deliveries/nueva" element={<NewDeliveryPage />} />

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
