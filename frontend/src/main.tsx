import App from "@/App";
import "@/index.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("No se encontró el elemento root para montar la aplicación.");
}

document.documentElement.classList.add("dark");

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
