import React, { useState, useEffect } from "react";
import {
  Mail, Lock, Eye, EyeOff, ArrowRight, ShieldCheck,
  KeyRound, Inbox, RefreshCw, X, Check, AlertCircle, ChevronDown
} from "lucide-react";
import { authService } from "./api";
import AuthVisualHero from "./AuthVisualHero";
import { AuthNavBar, AuthBottomWaves } from "./AuthNavBar";

export default function LoginPage({
  onLogin,
  onShowRegister,
  onBackToLanding,
  registeredSuccess = false,
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [infoMessage, setInfoMessage] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // MFA & OTP state
  const [needsOtp, setNeedsOtp] = useState(false);
  const [isMfaStep, setIsMfaStep] = useState(false);
  const [mfaEnrollPreauth, setMfaEnrollPreauth] = useState(null);
  const [devMfaSecret, setDevMfaSecret] = useState(null);
  const [mfaUri, setMfaUri] = useState(null);
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [canResendOtp, setCanResendOtp] = useState(true);
  const [resendCooldown, setResendCooldown] = useState(0);

  // Forgot password modal
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotPasswordStep, setForgotPasswordStep] = useState("email"); // "email" | "reset" | "done"
  const [forgotPasswordEmail, setForgotPasswordEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState("");
  const [forgotSuccessMsg, setForgotSuccessMsg] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);

  // Collapsible demo quick-fill drawer
  const [showDemoAccounts, setShowDemoAccounts] = useState(false);

  // Check URL parameters for password reset token
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      setResetToken(token);
      setForgotPasswordStep("reset");
      setShowForgotPassword(true);
    }
  }, []);

  // Cooldown timer for resend OTP
  useEffect(() => {
    let timer;
    if (resendCooldown > 0) {
      timer = setTimeout(() => setResendCooldown((c) => c - 1), 1000);
    } else {
      setCanResendOtp(true);
    }
    return () => clearTimeout(timer);
  }, [resendCooldown]);

  const handleCopySecret = (secret) => {
    navigator.clipboard.writeText(secret);
    setCopiedSecret(true);
    setTimeout(() => setCopiedSecret(false), 2000);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setInfoMessage("");

    try {
      if (mfaEnrollPreauth && otpCode) {
        await authService.enrollMfa(otpCode.trim(), mfaEnrollPreauth);
        const me = await authService.getMe();
        onLogin(me);
        return;
      }

      const response = await authService.login(email, password, otpCode ? otpCode.trim() : null);

      if (response.requires_otp) {
        setNeedsOtp(true);
        setIsMfaStep(false);
        setMfaEnrollPreauth(null);
        setOtpCode("");
        setError("");
        setInfoMessage("Verification code sent to your email. Please enter the 6-digit code below.");
      } else if (response.requires_mfa_enrollment) {
        setNeedsOtp(true);
        setIsMfaStep(true);
        setMfaEnrollPreauth(response.preauth_token);
        setOtpCode("");
        setError("");
        setInfoMessage("First-time MFA setup: Scan the QR code or enter the key into your authenticator app (Google Authenticator / Authy), then enter the 6-digit code.");
        if (response.dev_mfa_secret) setDevMfaSecret(response.dev_mfa_secret);
        if (response.mfa_provisioning_uri) setMfaUri(response.mfa_provisioning_uri);
      } else {
        const me = await authService.getMe();
        onLogin(me);
      }
    } catch (err) {
      setInfoMessage("");
      if (err?.response?.data?.detail === "MFA code required") {
        setNeedsOtp(true);
        setIsMfaStep(true);
        setMfaEnrollPreauth(null);
        setOtpCode("");
        setError("");
        setInfoMessage("Multi-Factor Authentication (MFA) required. Enter the 6-digit code from your authenticator app.");
      } else {
        setError(err?.response?.data?.detail || "Invalid email or password. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (!canResendOtp) return;
    setLoading(true);
    setError("");
    setInfoMessage("");
    try {
      await authService.login(email, password);
      setOtpCode("");
      setError("");
      setInfoMessage("A new verification code has been sent to your email.");
      setCanResendOtp(false);
      setResendCooldown(60);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to resend code");
    } finally {
      setLoading(false);
    }
  };

  const fillDemoAccount = (demoEmail) => {
    setEmail(demoEmail);
    setPassword("Password123");
    setNeedsOtp(false);
    setIsMfaStep(false);
    setMfaEnrollPreauth(null);
    setOtpCode("");
    setDevMfaSecret(null);
    setMfaUri(null);
    setError("");
    setInfoMessage("");
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setForgotLoading(true);
    setForgotError("");
    setForgotSuccessMsg("");
    try {
      await authService.forgotPassword(forgotPasswordEmail.trim());
      setForgotSuccessMsg("A password reset link has been dispatched to your email address.");
      setForgotPasswordStep("reset");
    } catch (err) {
      setForgotError(err?.response?.data?.detail || "Could not dispatch reset link. Please check the email.");
    } finally {
      setForgotLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setForgotError("Passwords do not match.");
      return;
    }
    if (newPassword.length < 10) {
      setForgotError("Password must be at least 10 characters long.");
      return;
    }
    setForgotLoading(true);
    setForgotError("");
    try {
      await authService.resetPassword(resetToken.trim(), newPassword);
      setForgotSuccessMsg("Password updated successfully! You can now sign in.");
      setForgotPasswordStep("done");
    } catch (err) {
      setForgotError(err?.response?.data?.detail || "Password reset failed. Token may be invalid or expired.");
    } finally {
      setForgotLoading(false);
    }
  };

  const closeForgotPasswordModal = () => {
    setShowForgotPassword(false);
    setForgotPasswordStep("email");
    setForgotPasswordEmail("");
    setResetToken("");
    setNewPassword("");
    setConfirmPassword("");
    setForgotError("");
    setForgotSuccessMsg("");
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-[#F0F6FA] via-[#E9F3F9] to-[#DCEEF8] text-[#0B1E33] relative overflow-x-hidden">
      {/* Decorative Wave Background */}
      <AuthBottomWaves />

      {/* Top Header */}
      <AuthNavBar onBackToLanding={onBackToLanding} />

      {/* Main Two-Column Container */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-12 py-6 lg:py-10 relative z-10">
        <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-14 items-center">
          
          {/* Left Column: Brand Hero + Patient Orbit Graphic + Feature Highlights */}
          <div className="lg:col-span-7 flex flex-col justify-center">
            <AuthVisualHero isRegister={false} onBackToLanding={onBackToLanding} />
          </div>

          {/* Right Column: Clean White Login Card */}
          <div className="lg:col-span-5 w-full flex justify-center">
            <div className="w-full max-w-md bg-white rounded-3xl p-7 sm:p-9 shadow-[0_20px_50px_rgba(11,32,56,0.08)] border border-slate-100/90 relative z-20">
              
              {/* Card Header */}
              <div className="mb-6">
                <h2 className="text-2xl sm:text-[28px] font-extrabold text-[#0B2038] font-display tracking-tight leading-tight">
                  Welcome Back
                </h2>
                <p className="text-sm text-slate-500 mt-1 font-medium">
                  Sign in to your CryptCare account
                </p>
              </div>

              {/* Status Banners */}
              {registeredSuccess && (
                <div className="flex items-center gap-2.5 p-3.5 mb-5 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 animate-fade-in font-medium">
                  <ShieldCheck size={17} className="text-emerald-600 shrink-0" />
                  <span>Account successfully verified! You can now sign in.</span>
                </div>
              )}

              {infoMessage && (
                <div className="flex items-start gap-2.5 p-3.5 mb-5 rounded-2xl bg-teal-50 border border-teal-200 text-xs text-teal-800 animate-fade-in font-medium">
                  <Inbox size={17} className="text-[#0FB6AA] shrink-0 mt-0.5" />
                  <span>{infoMessage}</span>
                </div>
              )}

              {error && (
                <div className="flex items-start gap-2.5 p-3.5 mb-5 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-800 animate-fade-in font-medium">
                  <AlertCircle size={17} className="text-rose-600 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              {/* Login Form */}
              <form onSubmit={handleLogin} className="space-y-4">
                
                {/* Email Address */}
                <div>
                  <label htmlFor="login-email" className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                    Email address
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <Mail size={18} />
                    </div>
                    <input
                      id="login-email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="Email address"
                      disabled={loading || needsOtp}
                      required
                      className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 bg-slate-50/40 text-slate-800 text-sm placeholder-slate-400 outline-none focus:bg-white focus:border-[#0FB6AA] focus:ring-2 focus:ring-[#0FB6AA]/15 transition-all"
                    />
                  </div>
                </div>

                {/* Password Field */}
                <div>
                  <label htmlFor="login-password" className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                    Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <Lock size={18} />
                    </div>
                    <input
                      id="login-password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Password"
                      disabled={loading || needsOtp}
                      required
                      className="w-full pl-10 pr-11 py-3 rounded-xl border border-slate-200 bg-slate-50/40 text-slate-800 text-sm placeholder-slate-400 outline-none focus:bg-white focus:border-[#0FB6AA] focus:ring-2 focus:ring-[#0FB6AA]/15 transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition-colors focus:outline-none"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                {/* OTP / MFA Verification Row (Dynamic Inline Challenge) */}
                {needsOtp && (
                  <div className="pt-2 animate-fade-in space-y-3">
                    <div className="flex items-center justify-between">
                      <label htmlFor="login-otp" className="block text-xs font-bold text-[#0FB6AA] uppercase tracking-wider">
                        {isMfaStep ? "6-Digit Authenticator Code" : "6-Digit Email Code"}
                      </label>
                      <button
                        type="button"
                        onClick={() => {
                          setNeedsOtp(false);
                          setIsMfaStep(false);
                          setOtpCode("");
                          setInfoMessage("");
                          setError("");
                        }}
                        className="text-xs text-slate-400 hover:text-slate-600"
                      >
                        Cancel
                      </button>
                    </div>

                    <div className="relative">
                      <input
                        id="login-otp"
                        type="text"
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        value={otpCode}
                        onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        placeholder="000000"
                        maxLength={6}
                        autoFocus
                        required
                        className="w-full py-3 text-center text-xl font-mono font-bold tracking-[0.4em] rounded-xl border-2 border-[#0FB6AA] bg-teal-50/30 text-[#0B2038] outline-none focus:ring-2 focus:ring-[#0FB6AA]/20"
                      />
                    </div>

                    <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                      <span>
                        {isMfaStep
                          ? (mfaEnrollPreauth ? "Scan QR code or enter secret" : "Open Google Authenticator / Authy")
                          : "Code sent to your email"}
                      </span>
                      {!isMfaStep && !mfaEnrollPreauth && (
                        <button
                          type="button"
                          onClick={handleResendOtp}
                          disabled={!canResendOtp || loading}
                          className="font-semibold text-[#1D64EC] hover:underline disabled:text-slate-400 cursor-pointer"
                        >
                          {canResendOtp ? "Resend code" : `Resend in ${resendCooldown}s`}
                        </button>
                      )}
                    </div>

                    {/* First-time MFA QR Enrollment */}
                    {mfaEnrollPreauth && (devMfaSecret || mfaUri) && (
                      <div className="mt-2 p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200 text-xs text-blue-900 space-y-2">
                        <div className="flex items-center justify-between font-semibold">
                          <span className="flex items-center gap-1.5">
                            <KeyRound size={15} className="text-[#0FB6AA]" />
                            <span>Link Authenticator App</span>
                          </span>
                          {devMfaSecret && (
                            <button
                              type="button"
                              onClick={() => handleCopySecret(devMfaSecret)}
                              className="text-[11px] font-bold text-[#0FB6AA] hover:underline cursor-pointer"
                            >
                              {copiedSecret ? "Copied!" : "Copy Key"}
                            </button>
                          )}
                        </div>

                        {mfaUri && (
                          <div className="flex flex-col items-center justify-center p-3 bg-white rounded-xl border border-blue-100 shadow-sm">
                            <img
                              src={`https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(mfaUri)}`}
                              alt="Scan QR code with Google Authenticator or Authy"
                              className="w-36 h-36 object-contain rounded-lg"
                            />
                            <p className="text-[11px] text-slate-500 mt-2 font-medium text-center">
                              Scan with Google Authenticator or Authy
                            </p>
                          </div>
                        )}

                        {devMfaSecret && (
                          <div>
                            <p className="text-[11px] text-slate-600 mb-1">Manual setup key:</p>
                            <div className="p-2 rounded-lg bg-white border border-blue-200 font-mono text-center text-xs tracking-wider font-bold text-[#0FB6AA] select-all break-all">
                              {devMfaSecret}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Remember Me and Forgot Password Row */}
                {!needsOtp && (
                  <div className="flex items-center justify-between pt-1">
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        className="w-4 h-4 rounded border-slate-300 text-[#1D64EC] focus:ring-[#1D64EC]/20 cursor-pointer"
                      />
                      <span className="text-xs text-slate-600 font-medium">Remember me</span>
                    </label>

                    <button
                      type="button"
                      onClick={() => setShowForgotPassword(true)}
                      className="text-xs font-semibold text-[#1D64EC] hover:text-[#0FB6AA] hover:underline transition-colors focus:outline-none"
                    >
                      Forgot password?
                    </button>
                  </div>
                )}

                {/* Primary Login Button */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full mt-2 py-3.5 px-6 rounded-xl font-bold text-white text-sm sm:text-base flex items-center justify-center gap-2 bg-gradient-to-r from-[#1D64EC] to-[#2563EB] hover:from-[#1A56CC] hover:to-[#1E40AF] active:scale-[0.99] shadow-lg shadow-blue-600/25 transition-all cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <RefreshCw size={18} className="animate-spin" />
                      <span>Signing in...</span>
                    </>
                  ) : needsOtp ? (
                    isMfaStep ? (
                      mfaEnrollPreauth ? (
                        <>
                          <span>Enroll MFA & Sign In</span>
                          <ArrowRight size={18} />
                        </>
                      ) : (
                        <>
                          <span>Verify MFA & Sign In</span>
                          <ArrowRight size={18} />
                        </>
                      )
                    ) : (
                      <>
                        <span>Verify & Sign In</span>
                        <ArrowRight size={18} />
                      </>
                    )
                  ) : (
                    <>
                      <span>Login</span>
                      <ArrowRight size={18} />
                    </>
                  )}
                </button>
              </form>

              {/* Bottom Register Redirect Link */}
              <div className="mt-6 pt-5 border-t border-slate-100 text-center">
                <p className="text-xs sm:text-sm text-slate-500">
                  Don&apos;t have an account?{" "}
                  <button
                    type="button"
                    onClick={onShowRegister}
                    className="font-bold text-[#1D64EC] hover:text-[#0FB6AA] hover:underline transition-colors cursor-pointer focus:outline-none"
                  >
                    Register here
                  </button>
                </p>
              </div>

              {/* Collapsible Demo Quick-Selector (For Testing) */}
              <div className="mt-4 pt-3 border-t border-dashed border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowDemoAccounts(!showDemoAccounts)}
                  className="w-full flex items-center justify-between text-[11px] font-semibold text-slate-400 hover:text-slate-600 uppercase tracking-wider py-1 focus:outline-none"
                >
                  <span>Quick Demo Accounts</span>
                  <ChevronDown size={14} className={`transform transition-transform ${showDemoAccounts ? "rotate-180" : ""}`} />
                </button>

                {showDemoAccounts && (
                  <div className="grid grid-cols-2 gap-1.5 mt-2.5 text-xs animate-fade-in">
                    <button
                      type="button"
                      onClick={() => fillDemoAccount("patient@example.com")}
                      className="p-2 rounded-xl bg-sky-50/70 hover:bg-sky-100/70 text-sky-800 font-medium text-left border border-sky-100 transition-colors flex items-center justify-between"
                    >
                      <span>🧑 Patient</span>
                      <span className="text-[9px] bg-sky-200/80 px-1 py-0.5 rounded font-mono font-bold">OTP</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => fillDemoAccount("doctor@example.com")}
                      className="p-2 rounded-xl bg-teal-50/70 hover:bg-teal-100/70 text-teal-800 font-medium text-left border border-teal-100 transition-colors flex items-center justify-between"
                    >
                      <span>👨‍⚕️ Doctor</span>
                      <span className="text-[9px] bg-teal-200/80 px-1 py-0.5 rounded font-mono font-bold">MFA</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => fillDemoAccount("admin@example.com")}
                      className="p-2 rounded-xl bg-blue-50/70 hover:bg-blue-100/70 text-blue-800 font-medium text-left border border-blue-100 transition-colors flex items-center justify-between"
                    >
                      <span>🏥 Admin</span>
                      <span className="text-[9px] bg-blue-200/80 px-1 py-0.5 rounded font-mono font-bold">MFA</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => fillDemoAccount("nurse@example.com")}
                      className="p-2 rounded-xl bg-emerald-50/70 hover:bg-emerald-100/70 text-emerald-800 font-medium text-left border border-emerald-100 transition-colors flex items-center justify-between"
                    >
                      <span>👩‍⚕️ Nurse</span>
                      <span className="text-[9px] bg-emerald-200/80 px-1 py-0.5 rounded font-mono font-bold">MFA</span>
                    </button>
                  </div>
                )}
              </div>

            </div>
          </div>
        </div>
      </main>

      {/* Forgot Password Modal */}
      {showForgotPassword && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white border border-slate-100 rounded-3xl p-7 w-full max-w-md shadow-2xl relative">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
              <h3 className="text-lg font-bold text-[#0B2038] font-display">
                {forgotPasswordStep === "reset" ? "Set New Password" : "Reset Password"}
              </h3>
              <button
                type="button"
                onClick={closeForgotPasswordModal}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition"
              >
                <X size={18} />
              </button>
            </div>

            {forgotError && (
              <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 mb-4 text-xs text-rose-700 flex items-start gap-2">
                <AlertCircle size={15} className="shrink-0 mt-0.5" />
                <span>{forgotError}</span>
              </div>
            )}

            {forgotSuccessMsg && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 mb-4 text-xs text-emerald-700 flex items-start gap-2">
                <Check size={15} className="shrink-0 mt-0.5" />
                <span>{forgotSuccessMsg}</span>
              </div>
            )}

            {forgotPasswordStep === "email" && (
              <form onSubmit={handleForgotPassword} className="space-y-4">
                <p className="text-xs text-slate-500 leading-relaxed">
                  Enter your registered CryptCare email address and we will dispatch a password reset token.
                </p>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={forgotPasswordEmail}
                    onChange={(e) => setForgotPasswordEmail(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-800 text-sm outline-none focus:bg-white focus:border-[#0FB6AA]"
                    placeholder="patient@example.com"
                    required
                  />
                </div>
                <div className="flex gap-2 justify-end pt-2">
                  <button
                    type="button"
                    onClick={closeForgotPasswordModal}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-500 hover:bg-slate-100"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={forgotLoading}
                    className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-[#1D64EC] to-[#0FB6AA] shadow-md hover:brightness-105 disabled:opacity-60"
                  >
                    {forgotLoading ? "Sending..." : "Send Reset Token"}
                  </button>
                </div>
              </form>
            )}

            {forgotPasswordStep === "reset" && (
              <form onSubmit={handleResetPassword} className="space-y-3">
                <p className="text-xs text-slate-500 leading-relaxed">
                  Enter the reset token sent to your email along with your new secure password.
                </p>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                    Reset Token
                  </label>
                  <input
                    type="text"
                    value={resetToken}
                    onChange={(e) => setResetToken(e.target.value)}
                    placeholder="Paste reset token"
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-800 text-sm font-mono outline-none focus:bg-white focus:border-[#0FB6AA]"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showNewPassword ? "text" : "password"}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Min 10 chars, 1 upper, 1 digit"
                      className="w-full px-3.5 py-2 pr-10 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-800 text-sm outline-none focus:bg-white focus:border-[#0FB6AA]"
                      required
                      minLength={10}
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
                    >
                      {showNewPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter new password"
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-800 text-sm outline-none focus:bg-white focus:border-[#0FB6AA]"
                    required
                  />
                </div>
                <div className="flex gap-2 justify-end pt-2">
                  <button
                    type="button"
                    onClick={closeForgotPasswordModal}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-500 hover:bg-slate-100"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={forgotLoading}
                    className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-[#1D64EC] to-[#0FB6AA] shadow-md hover:brightness-105 disabled:opacity-60"
                  >
                    {forgotLoading ? "Resetting..." : "Save New Password"}
                  </button>
                </div>
              </form>
            )}

            {forgotPasswordStep === "done" && (
              <div className="text-center py-4 space-y-3">
                <p className="text-sm text-slate-600">Your credentials have been securely updated.</p>
                <button
                  type="button"
                  onClick={closeForgotPasswordModal}
                  className="px-6 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-[#1D64EC] to-[#0FB6AA] shadow-md"
                >
                  Return to Sign In
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
