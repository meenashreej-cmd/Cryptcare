import React from "react";
import {
  ShieldCheck, Lock, FileText, BadgeCheck, Users,
  Stethoscope, FlaskConical, Pill, User
} from "lucide-react";
import cryptcareIcon from "./assets/cryptcare_icon.png";
import authPatientArt from "./assets/auth_patient_art.jpg";

export default function AuthVisualHero({
  isRegister = false,
  onBackToLanding,
}) {
  const features = isRegister
    ? [
        {
          icon: Lock,
          title: "End-to-End Encryption",
          desc: "AES-256-GCM hardware vault security"
        },
        {
          icon: FileText,
          title: "Your Consent. Your Control.",
          desc: "Time-bounded granular permissions"
        },
        {
          icon: BadgeCheck,
          title: "Secure Access for Trusted Providers",
          desc: "Cryptographically verified doctor credentials"
        },
        {
          icon: Users,
          title: "A Safer, More Connected Healthcare Ecosystem",
          desc: "Zero-knowledge decentralized sharing"
        }
      ]
    : [
        {
          icon: Lock,
          title: "End-to-End Encryption",
          desc: "AES-256-GCM hardware vault security"
        },
        {
          icon: FileText,
          title: "Your Consent. Your Control.",
          desc: "Time-bounded granular permissions"
        },
        {
          icon: BadgeCheck,
          title: "Secure Access for Trusted Providers",
          desc: "Cryptographically verified doctor credentials"
        },
        {
          icon: Users,
          title: "A Safer, More Connected Healthcare Ecosystem",
          desc: "Zero-knowledge decentralized sharing"
        }
      ];

  return (
    <div className="flex flex-col justify-between h-full relative z-10 py-2">
      {/* Brand & Wordmark */}
      <div className="mb-6 lg:mb-8">
        <button
          type="button"
          onClick={onBackToLanding}
          className="group inline-flex items-center gap-3 text-left focus:outline-none transition-transform hover:scale-[1.01]"
        >
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-[#0FB6AA] to-[#2F6FE0] p-0.5 shadow-md shadow-teal-500/15 flex items-center justify-center">
            <div className="w-full h-full bg-white rounded-[14px] flex items-center justify-center p-1.5">
              <img src={cryptcareIcon} alt="CryptCare" className="w-full h-full object-contain" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black tracking-tight font-display text-[#0B2038] flex items-center leading-none">
              Crypt<span className="text-[#0FB6AA]">Care</span>
            </div>
            <div className="text-[11px] font-medium text-slate-500 mt-1 tracking-wide">
              Where Healthcare Meets Privacy
            </div>
          </div>
        </button>
      </div>

      {/* Main Heading & Subtitle */}
      <div className="mb-6 lg:mb-8">
        <h1 className="text-3xl sm:text-4xl lg:text-[42px] font-extrabold text-[#0B2038] font-display leading-[1.15] tracking-tight">
          {isRegister ? (
            <>
              Join <span className="text-[#0FB6AA]">CryptCare.</span>
            </>
          ) : (
            <>
              Your Health Data.<br />
              <span className="text-[#0FB6AA]">Your Control.</span>
            </>
          )}
        </h1>
        <p className="text-sm sm:text-base text-slate-500 font-medium mt-2.5 max-w-md">
          {isRegister
            ? "Take control of your health data with a secure and trusted platform."
            : "Secure. Private. Patient-Owned."}
        </p>
      </div>

      {/* Illustration with Orbit Badges (Centerpiece) */}
      <div className="relative my-4 lg:my-6 flex items-center justify-center">
        {/* Soft Ambient Radial Glow */}
        <div className="absolute inset-0 bg-gradient-to-r from-teal-400/15 via-sky-400/20 to-blue-500/15 rounded-full blur-3xl -z-10 scale-95" />

        {/* Orbit Wrapper */}
        <div className="relative w-64 h-64 sm:w-80 sm:h-80 md:w-88 md:h-88 flex items-center justify-center">
          {/* Dashed Orbital Rings */}
          <div className="absolute inset-0 rounded-full border border-dashed border-[#0FB6AA]/35 animate-spin-slow pointer-events-none" />
          <div className="absolute inset-6 rounded-full border border-dotted border-[#2F6FE0]/25 pointer-events-none" />

          {/* Central Portrait Container */}
          <div className="w-48 h-48 sm:w-60 sm:h-60 rounded-full p-1.5 bg-gradient-to-tr from-[#0FB6AA]/40 via-white to-[#2F6FE0]/40 shadow-2xl shadow-sky-900/10 overflow-hidden">
            <div className="w-full h-full rounded-full overflow-hidden bg-white">
              <img
                src={authPatientArt}
                alt="CryptCare Patient with Health Security App"
                className="w-full h-full object-cover object-top hover:scale-105 transition-transform duration-500"
              />
            </div>
          </div>

          {/* Floating Badge 1: User Profile (Top Left) */}
          <div
            className="absolute top-2 left-6 sm:left-8 w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-[#38BDF8] text-white flex items-center justify-center shadow-lg shadow-sky-500/30 ring-4 ring-white/80 animate-bounce-gentle"
            title="Sovereign Patient Identity"
          >
            <User size={18} />
          </div>

          {/* Floating Badge 2: Lab Science (Top Right) */}
          <div
            className="absolute top-6 right-5 sm:right-7 w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-[#2F6FE0] text-white flex items-center justify-center shadow-lg shadow-blue-600/30 ring-4 ring-white/80"
            style={{ animation: "floatSlow 4s ease-in-out infinite" }}
            title="Encrypted Lab & Diagnostic Reports"
          >
            <FlaskConical size={18} />
          </div>

          {/* Floating Badge 3: Clinical Stethoscope (Middle Left) */}
          <div
            className="absolute top-1/2 -left-3 sm:-left-4 -translate-y-1/2 w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-[#0FB6AA] text-white flex items-center justify-center shadow-lg shadow-teal-500/30 ring-4 ring-white/80"
            style={{ animation: "floatSlow 3.5s ease-in-out infinite 0.5s" }}
            title="Verified Provider Access"
          >
            <Stethoscope size={18} />
          </div>

          {/* Floating Badge 4: Rx Pill (Middle Right) */}
          <div
            className="absolute top-1/2 -right-3 sm:-right-4 -translate-y-1/2 w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-[#8B5CF6] text-white flex items-center justify-center shadow-lg shadow-purple-500/30 ring-4 ring-white/80"
            style={{ animation: "floatSlow 4.2s ease-in-out infinite 1s" }}
            title="Signed Digital Prescriptions"
          >
            <Pill size={18} />
          </div>

          {/* Floating Badge 5: Security Shield (Bottom Right) */}
          <div
            className="absolute bottom-4 right-8 sm:right-10 w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-[#0A8A82] text-white flex items-center justify-center shadow-lg shadow-teal-600/30 ring-4 ring-white/80"
            style={{ animation: "floatSlow 3.8s ease-in-out infinite 1.5s" }}
            title="Hardware Sealed Health Vault"
          >
            <ShieldCheck size={18} />
          </div>
        </div>
      </div>

      {/* Feature Highlights Grid / List */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 mt-4 lg:mt-6">
        {features.map((feat, idx) => {
          const FIcon = feat.icon;
          return (
            <div
              key={idx}
              className="flex items-center gap-3 p-2.5 rounded-2xl bg-white/60 backdrop-blur-sm border border-slate-200/50 hover:bg-white/90 hover:border-teal-200 transition-all shadow-sm"
            >
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-teal-50 to-blue-50 text-[#0A8A82] border border-teal-200/60 flex items-center justify-center shrink-0">
                <FIcon size={16} />
              </div>
              <div className="min-w-0">
                <div className="text-xs font-bold text-[#0B2038] truncate">{feat.title}</div>
                <div className="text-[10px] text-slate-500 truncate">{feat.desc}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
