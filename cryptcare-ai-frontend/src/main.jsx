import React from "react";
import ReactDOM from "react-dom/client";
import CryptcareApp from "./CryptcareApp.jsx";  // component is still named CryptcareApp internally
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <CryptcareApp />
  </React.StrictMode>
);
