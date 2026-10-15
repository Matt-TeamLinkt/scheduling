import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "../../design-system/colors_and_type.css";
import "./styles.css";
import { App } from "./App";

async function start() {
  // Preview builds (VITE_DEMO=1) answer /api calls in the browser with precomputed data.
  if (import.meta.env.VITE_DEMO === "1") await (await import("./demo/mock")).installMockApi();
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
start();
