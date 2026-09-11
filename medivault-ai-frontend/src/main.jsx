import React from "react";
import ReactDOM from "react-dom/client";
import MediVaultApp from "./MediVaultApp.jsx";  // component is still named MediVaultApp internally
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <MediVaultApp />
  </React.StrictMode>
);
