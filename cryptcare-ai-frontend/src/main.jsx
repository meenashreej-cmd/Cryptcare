import React, { Component } from "react";
import ReactDOM from "react-dom/client";
import CryptcareApp from "./CryptcareApp.jsx";
import "./index.css";

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("CryptCare Uncaught UI Error:", error, errorInfo);
  }

  handleReset = () => {
    localStorage.clear();
    window.location.href = "/";
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#050D17",
          color: "#E7F1F5",
          fontFamily: "system-ui, sans-serif",
          padding: "24px"
        }}>
          <div style={{
            maxWidth: "480px",
            width: "100%",
            background: "#0F1C2A",
            border: "1px solid rgba(120,190,200,0.2)",
            borderRadius: "16px",
            padding: "32px",
            textAlign: "center"
          }}>
            <h2 style={{ fontSize: "20px", fontWeight: "bold", marginBottom: "12px", color: "#0FB6AA" }}>
              Something went wrong
            </h2>
            <p style={{ fontSize: "14px", color: "#90A8B8", marginBottom: "20px" }}>
              {this.state.error?.message || "An unexpected error occurred in the vault interface."}
            </p>
            <button
              onClick={this.handleReset}
              style={{
                background: "linear-gradient(135deg, #0FB6AA, #2F6FE0)",
                color: "#fff",
                border: "none",
                borderRadius: "10px",
                padding: "10px 20px",
                fontWeight: "600",
                cursor: "pointer"
              }}
            >
              Reset Session & Go to Login
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <CryptcareApp />
    </ErrorBoundary>
  </React.StrictMode>
);
