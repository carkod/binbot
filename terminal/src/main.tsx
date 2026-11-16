import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";
import "@mantine/dates/styles.css";
import { MotionConfig } from "motion/react";
import React from "react";
import { createRoot } from "react-dom/client";
import "react-toastify/dist/ReactToastify.css";
import App from "./App";
import "./styles/terminal.css";
import { theme } from "./theme";
import { chartTransition } from "./utils/motion";
const container = document.getElementById("root");
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <MotionConfig reducedMotion="never" transition={chartTransition}>
        <MantineProvider theme={theme} forceColorScheme="light">
          <App />
        </MantineProvider>
      </MotionConfig>
    </React.StrictMode>,
  );
} else {
  throw new Error(
    "Root element with ID 'root' was not found in the document. Ensure there is a corresponding HTML element with the ID 'root' in your HTML file.",
  );
}
