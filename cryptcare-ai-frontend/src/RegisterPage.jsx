import React, { useState, useEffect } from "react";
import {
  User, Mail, Phone, Lock, Eye, EyeOff, ArrowRight,
  ShieldCheck, RefreshCw, Send, AlertCircle, KeyRound,
  Stethoscope, HeartPulse, FlaskRound, FlaskConical,
  Building2, Droplet, CircleUser, ChevronDown
} from "lucide-react";
import { authService } from "./api";
import AuthVisualHero from "./AuthVisualHero";
import { AuthNavBar, AuthBottomWaves } from "./AuthNavBar";
import LegalModal from "./LegalModal";

const REGISTER_ROLES = [
  { id: "PATIENT", label: "Patient", icon: CircleUser, desc: "Personal health records & vault" },
  { id: "DOCTOR", label: "Doctor", icon: Stethoscope, desc: "Clinical access · TOTP MFA" },
  { id: "NURSE", label: "Nurse", icon: HeartPulse, desc: "Vitals & medication administration" },
  { id: "PHARMACIST", label: "Pharmacist", icon: FlaskRound, desc: "Dispense prescriptions" },
  { id: "LAB", label: "Lab Technician", icon: FlaskConical, desc: "Upload diagnostic lab reports" },
  { id: "INSURER", label: "Insurance Provider", icon: Building2, desc: "Claims & anomaly reviews" },
  { id: "BLOOD_BANK", label: "Blood Bank", icon: Droplet, desc: "Inventory & donor fulfillment" },
  { id: "HOSPITAL_ADMIN", label: "Hospital Admin", icon: Building2, desc: "Manage clinic staff" },
];

const PROFESSIONAL_ROLES = ["DOCTOR", "NURSE", "PHARMACIST", "LAB", "INSURER", "BLOOD_BANK", "HOSPITAL_ADMIN"];

export default function RegisterPage({
  onRegistered,
  onBackToLogin,
  onBackToLanding,
}) {
  // Step: "form" | "otp"
  const [step, setStep] = useState("form");
  const [selectedRole, setSelectedRole] = useState("PATIENT");
  const [showRoleSelector, setShowRoleSelector] = useState(false);

  // Form Fields
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agreeTerms, setAgreeTerms] = useState(false);

  // Professional-specific Fields (optional if selectedRole !== "PATIENT")
  const [licenseNumber, setLicenseNumber] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [hospitalName, setHospitalName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [department, setDepartment] = useState("");

  // UI state
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // OTP Verification state
  const [pendingUserId, setPendingUserId] = useState(null);
  const [pendingPreauthToken, setPendingPreauthToken] = useState(null);
  const [otpCode, setOtpCode] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendSuccess, setResendSuccess] = useState("");
  const [showMfaUri, setShowMfaUri] = useState(null);

  // Legal Modal
  const [legalModalType, setLegalModalType] = useState(null); // "terms" | "privacy" | null

  const isProfessional = PROFESSIONAL_ROLES.includes(selectedRole);

  useEffect(() => {
    let timer;
    if (resendCooldown > 0) {
      timer = setTimeout(() => setResendCooldown((c) => c - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [resendCooldown]);

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");

    // Validations
    if (!agreeTerms) {
      setError("Please agree to the Terms of Service and Privacy Policy to proceed.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match. Please re-enter.");
      return;
    }
    if (password.length < 10) {
      setError("Password must be at least 10 characters long.");
      return;
    }
    if (!/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
      setError("Password must contain at least one uppercase letter and one numeric digit.");
      return;
    }
    if (phone.trim().length < 8) {
      setError("Please enter a valid phone number with area code.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        email: email.trim(),
        phone: phone.trim(),
        password: password,
        full_name: fullName.trim(),
        role: selectedRole,
      };

      if (isProfessional) {
        if (selectedRole !== "HOSPITAL_ADMIN") {
          payload.license_number = licenseNumber.trim();
        }
        if (selectedRole === "DOCTOR") {
          payload.specialization = specialization.trim() || "General Medicine";
          payload.hospital_name = hospitalName.trim() || "City General Hospital";
        }
        if (selectedRole === "NURSE") {
          payload.hospital_name = hospitalName.trim() || "City General Hospital";
          payload.department = department.trim() || "General Ward";
        }
        if (selectedRole === "HOSPITAL_ADMIN") {
          payload.hospital_name = hospitalName.trim() || "Metropolitan Health System";
        }
        if (["LAB", "PHARMACIST", "INSURER", "BLOOD_BANK"].includes(selectedRole)) {
          payload.organization_name = organizationName.trim() || "Authorized Facility";
        }
      }

      const data = await authService.register(payload);
      setPendingUserId(data.user_id);
      if (data.preauth_token) setPendingPreauthToken(data.preauth_token);
      if (data.mfa_provisioning_uri) setShowMfaUri(data.mfa_provisioning_uri);
      setOtpCode("");
      setResendCooldown(60);
      setStep("otp");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map((m) => m.msg).join("; "));
      } else {
        setError("Registration could not be completed. Please check the entered fields.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await authService.verifyOtp(pendingUserId, otpCode.trim(), pendingPreauthToken);
      onRegistered(email.trim(), password);
    } catch (err) {
      setError(err?.response?.data?.detail || "Invalid or expired verification code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (resendCooldown > 0 || !pendingPreauthToken) return;
    setLoading(true);
    setError("");
    setResendSuccess("");
    try {
      await authService.resendOtp(pendingPreauthToken);
      setResendSuccess("A new 6-digit verification code has been dispatched to your inbox.");
      setResendCooldown(60);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to resend verification code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-[#F0F6FA] via-[#E9F3F9] to-[#DCEEF8] text-[#0B1E33] relative overflow-x-hidden">
      {/* Decorative Wave Background */}
      <AuthBottomWaves />

      {/* Top Header */}
      <AuthNavBar onBackToLanding={onBackToLanding} />

      {/* Main Container */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-12 py-6 lg:py-10 relative z-10">
        <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-14 items-center">
          
          {/* Left Column: Brand Hero + Patient Orbit Graphic + Feature Highlights */}
          <div className="lg:col-span-6 flex flex-col justify-center">
            <AuthVisualHero isRegister={true} onBackToLanding={onBackToLanding} />
          </div>

          {/* Right Column: Clean White Register Card */}
          <div className="lg:col-span-6 w-full flex justify-center">
            <div className="w-full max-w-lg bg-white rounded-3xl p-7 sm:p-9 shadow-[0_20px_50px_rgba(11,32,56,0.08)] border border-slate-100/90 relative z-20">
              
              {step === "form" ? (
                <>
                  {/* Card Header */}
                  <div className="mb-5">
                    <h2 className="text-2xl sm:text-[28px] font-extrabold text-[#0B2038] font-display tracking-tight leading-tight">
                      Create an Account
                    </h2>
                    <p className="text-sm text-slate-500 mt-1 font-medium">
                      Join CryptCare and take control of your health data.
                    </p>
                  </div>

                  {/* Error Banner */}
                  {error && (
                    <div className="flex items-start gap-2.5 p-3.5 mb-5 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-800 animate-fade-in font-medium">
                      <AlertCircle size={17} className="text-rose-600 shrink-0 mt-0.5" />
                      <span>{error}</span>
                    </div>
                  )}

                  {/* Role Selector Trigger (Default: Patient) */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between p-2.5 rounded-2xl bg-slate-50 border border-slate-200/70">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-500">Account Type:</span>
                        <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-white text-[#1D64EC] border border-blue-100 shadow-sm flex items-center gap-1.5">
                          <CircleUser size={13} className="text-[#0FB6AA]" />
                          {REGISTER_ROLES.find((r) => r.id === selectedRole)?.label || "Patient"}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowRoleSelector(!showRoleSelector)}
                        className="text-xs font-semibold text-[#1D64EC] hover:text-[#0FB6AA] hover:underline flex items-center gap-1"
                      >
                        <span>Change</span>
                        <ChevronDown size={14} className={`transform transition-transform ${showRoleSelector ? "rotate-180" : ""}`} />
                      </button>
                    </div>

                    {showRoleSelector && (
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2 p-2.5 rounded-2xl bg-slate-100/70 border border-slate-200 animate-fade-in">
                        {REGISTER_ROLES.map((r) => {
                          const RIcon = r.icon;
                          const isSel = selectedRole === r.id;
                          return (
                            <button
                              key={r.id}
                              type="button"
                              onClick={() => {
                                setSelectedRole(r.id);
                                setShowRoleSelector(false);
                              }}
                              className={`p-2 rounded-xl text-left transition-all flex flex-col items-center gap-1.5 ${
                                isSel
                                  ? "bg-white border-2 border-[#0FB6AA] shadow-sm text-[#0B2038]"
                                  : "bg-white/60 hover:bg-white text-slate-600 border border-transparent"
                              }`}
                            >
                              <div className="w-7 h-7 rounded-lg bg-teal-50 text-[#0A8A82] flex items-center justify-center">
                                <RIcon size={15} />
                              </div>
                              <span className="text-[11px] font-bold text-center leading-tight">{r.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Form */}
                  <form onSubmit={handleRegister} className="space-y-3.5">
                    
                    {/* Full Name */}
                    <div>
                      <label htmlFor="reg-name" className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                        Full Name
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                          <User size={18} />
                        </div>
                        <input
                          id="reg-name"
                          type="text"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          placeholder="Full Name"
                          required
                          className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/40 text-slate-800 text-sm placeholder-slate-400 outline-none focus:bg-white focus:border-[#0FB6AA] focus:ring-2 focus:ring-[#0FB6AA]/15 transition-all"
                        />
                      </div>
                    </div>

                    {/* Email Address */}
                    <div>
                      <label htmlFor="reg-email" className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                        Email address
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                          <Mail size={18} />
                        </div>
                        <input
                          id="reg-email"
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="Email address"
                          required
                          className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/40 text-slate-800 text-sm placeholder-slate-400 outline-none focus:bg-white focus:border-[#0FB6AA] focus:ring-2 focus:ring-[#0FB6AA]/15 transition-all"
                        />
                      </div>
                    </div>

                    {/* Phone Number */}
                    <div>
                      <label htmlFor="reg-phone" className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                        Phone Number
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                          <Phone size={18} />
                        </div>
                        <input
                          id="reg-phone"
                          type="tel"
                          value={phone}
                          onChange={(e) => setPhone(e.target.value)}
                          placeholder="Phone Number"
                          required
                          className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/40 text-slate-800 text-sm placeholder-slate-400 outline-none focus:bg-white focus:border-[#0FB6AA] focus:ring-2 focus:ring-[#0FB6AA]/15 transition-all"
                        />
                      </div>
                    </div>

                    {/* Professional Role Fields (Only rendered if Provider role selected) */}
                    {isProfessional && (
                      <div className="p-3 rounded-2xl bg-teal-50/50 border border-teal-100 space-y-2.5 animate-fade-in text-xs">
                        <div className="font-bold text-[#0B2038] flex items-center gap-1.5">
                          <ShieldCheck size={14} className="text-[#0FB6AA]" />
                          <span>Provider Verification Details</span>
                        </div>

                        {selectedRole !== "HOSPITAL_ADMIN" && (
                          <div>
                            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                              Medical License / Registry Number *
                            </label>
                            <input
                              type="text"
                              value={licenseNumber}
                              onChange={(e) => setLicenseNumber(e.target.value)}
                              placeholder={selectedRole === "DOCTOR" ? "e.g. MD-10001" : "e.g. RN-20001"}
                              required
                              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-xs outline-none focus:border-[#0FB6AA]"
                            />
                          </div>
                        )}

                        {selectedRole === "DOCTOR" && (
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Specialization</label>
                              <input
                                type="text"
                                value={specialization}
                                onChange={(e) => setSpecialization(e.target.value)}
                                placeholder="e.g. Cardiology"
                                className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-xs outline-none focus:border-[#0FB6AA]"
                              />
                            </div>
                            <div>
                              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Hospital / Clinic</label>
                              <input
                                type="text"
                                value={hospitalName}
                                onChange={(e) => setHospitalName(e.target.value)}
                                placeholder="e.g. City Hospital"
                                className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-xs outline-none focus:border-[#0FB6AA]"
                              />
                            </div>
                          </div>
                        )}

                        {["LAB", "PHARMACIST", "INSURER", "BLOOD_BANK"].includes(selectedRole) && (
                          <div>
                            <label className="block text-[11px] font-semibold text-slate-600 mb-1">Facility Name</label>
                            <input
                              type="text"
                              value={organizationName}
                              onChange={(e) => setOrganizationName(e.target.value)}
                              placeholder="e.g. Central Diagnostics"
                              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-xs outline-none focus:border-[#0FB6AA]"
                            />
                          </div>
                        )}
                      </div>
                    )}

                    {/* Password Field */}
                    <div>
                      <label htmlFor="reg-password" className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                        Password
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                          <Lock size={18} />
                        </div>
                        <input
                          id="reg-password"
                          type={showPassword ? "text" : "password"}
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="Password"
                          required
                          minLength={10}
                          className="w-full pl-10 pr-11 py-2.5 rounded-xl border border-slate-200 bg-slate-50/40 text-slate-800 text-sm placeholder-slate-400 outline-none focus:bg-white focus:border-[#0FB6AA] focus:ring-2 focus:ring-[#0FB6AA]/15 transition-all"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 focus:outline-none"
                        >
                          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                      </div>
                    </div>

                    {/* Confirm Password Field */}
                    <div>
                      <label htmlFor="reg-confirm-pw" className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                        Confirm Password
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                          <Lock size={18} />
                        </div>
                        <input
                          id="reg-confirm-pw"
                          type={showConfirmPassword ? "text" : "password"}
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          placeholder="Confirm Password"
                          required
                          className="w-full pl-10 pr-11 py-2.5 rounded-xl border border-slate-200 bg-slate-50/40 text-slate-800 text-sm placeholder-slate-400 outline-none focus:bg-white focus:border-[#0FB6AA] focus:ring-2 focus:ring-[#0FB6AA]/15 transition-all"
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 focus:outline-none"
                        >
                          {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                      </div>
                    </div>

                    {/* Terms & Privacy Agreement Checkbox */}
                    <div className="pt-1">
                      <label className="flex items-start gap-2.5 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={agreeTerms}
                          onChange={(e) => setAgreeTerms(e.target.checked)}
                          className="mt-0.5 w-4 h-4 rounded border-slate-300 text-[#1D64EC] focus:ring-[#1D64EC]/20 cursor-pointer shrink-0"
                          required
                        />
                        <span className="text-xs text-slate-600 leading-snug">
                          I agree to the{" "}
                          <button
                            type="button"
                            onClick={() => setLegalModalType("terms")}
                            className="font-bold text-[#1D64EC] hover:underline cursor-pointer"
                          >
                            Terms of Service
                          </button>{" "}
                          and{" "}
                          <button
                            type="button"
                            onClick={() => setLegalModalType("privacy")}
                            className="font-bold text-[#1D64EC] hover:underline cursor-pointer"
                          >
                            Privacy Policy
                          </button>
                        </span>
                      </label>
                    </div>

                    {/* Primary Submit Button */}
                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full mt-3 py-3.5 px-6 rounded-xl font-bold text-white text-sm sm:text-base flex items-center justify-center gap-2 bg-gradient-to-r from-[#1D64EC] to-[#2563EB] hover:from-[#1A56CC] hover:to-[#1E40AF] active:scale-[0.99] shadow-lg shadow-blue-600/25 transition-all cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed"
                    >
                      {loading ? (
                        <>
                          <RefreshCw size={18} className="animate-spin" />
                          <span>Creating Account...</span>
                        </>
                      ) : (
                        <>
                          <span>Create Account</span>
                          <ArrowRight size={18} />
                        </>
                      )}
                    </button>
                  </form>

                  {/* Already have an account */}
                  <div className="mt-5 pt-4 border-t border-slate-100 text-center">
                    <p className="text-xs sm:text-sm text-slate-500">
                      Already have an account?{" "}
                      <button
                        type="button"
                        onClick={onBackToLogin}
                        className="font-bold text-[#1D64EC] hover:text-[#0FB6AA] hover:underline transition-colors cursor-pointer focus:outline-none"
                      >
                        Login here
                      </button>
                    </p>
                  </div>
                </>
              ) : (
                /* Step 3: OTP Verification Card */
                <div className="animate-fade-in text-center">
                  <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-3 bg-gradient-to-br from-teal-50 to-blue-50 border border-teal-100 text-[#0A8A82]">
                    <Send size={24} />
                  </div>

                  <h2 className="text-2xl font-extrabold text-[#0B2038] font-display">
                    Check your email
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-sm mx-auto">
                    We sent a 6-digit verification code to<br />
                    <span className="font-bold text-[#0B2038]">{email}</span>
                  </p>

                  {resendSuccess && (
                    <div className="my-3 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium">
                      {resendSuccess}
                    </div>
                  )}

                  {showMfaUri && (
                    <div className="my-3 p-3 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-900 text-left flex items-start gap-2">
                      <KeyRound size={16} className="text-[#0FB6AA] shrink-0 mt-0.5" />
                      <span>Privileged Provider Account: Multi-factor authenticator setup will be prompted on your first sign-in.</span>
                    </div>
                  )}

                  {error && (
                    <div className="my-3 p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 text-left flex items-start gap-2">
                      <AlertCircle size={16} className="text-rose-600 shrink-0 mt-0.5" />
                      <span>{error}</span>
                    </div>
                  )}

                  <form onSubmit={handleVerifyOtp} className="space-y-4 mt-4">
                    <div>
                      <label htmlFor="reg-otp" className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                        6-Digit Verification Code
                      </label>
                      <input
                        id="reg-otp"
                        type="text"
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        placeholder="000000"
                        value={otpCode}
                        onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        maxLength={6}
                        required
                        autoFocus
                        className="w-full py-3.5 text-center text-2xl font-mono font-bold tracking-[0.4em] rounded-xl border-2 border-[#0FB6AA] bg-teal-50/20 text-[#0B2038] outline-none focus:ring-2 focus:ring-[#0FB6AA]/25"
                      />
                    </div>

                    <p className="text-xs text-slate-400">
                      Code expires in 5 minutes. Check your spam folder if you do not see it.
                    </p>

                    <button
                      type="submit"
                      disabled={loading || otpCode.length < 6}
                      className="w-full py-3.5 px-6 rounded-xl font-bold text-white text-sm sm:text-base flex items-center justify-center gap-2 bg-gradient-to-r from-[#1D64EC] to-[#2563EB] hover:from-[#1A56CC] hover:to-[#1E40AF] shadow-lg shadow-blue-600/25 transition-all cursor-pointer disabled:opacity-60"
                    >
                      {loading ? (
                        <>
                          <RefreshCw size={18} className="animate-spin" />
                          <span>Verifying & Activating...</span>
                        </>
                      ) : (
                        <>
                          <span>Verify & Activate Account</span>
                          <ArrowRight size={18} />
                        </>
                      )}
                    </button>
                  </form>

                  <div className="mt-5 flex items-center justify-between text-xs text-slate-500">
                    <button
                      type="button"
                      disabled={loading || resendCooldown > 0}
                      onClick={handleResendOtp}
                      className="font-bold text-[#1D64EC] hover:underline disabled:text-slate-400 cursor-pointer"
                    >
                      {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : "Resend code"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setStep("form");
                        setError("");
                        setOtpCode("");
                      }}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      ← Change details
                    </button>
                  </div>
                </div>
              )}

            </div>
          </div>
        </div>
      </main>

      {/* Legal Modal (Terms / Privacy) */}
      <LegalModal
        type={legalModalType}
        onClose={() => setLegalModalType(null)}
      />
    </div>
  );
}
