import React, { useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import {
  Shield, ShieldCheck, Lock, FileSignature, Bot, Eye, KeyRound,
  ChevronRight, Play, X, Users, Stethoscope, Activity, Pill,
  FlaskConical, Building2, CheckCircle2, ArrowRight, ShieldAlert,
  Sparkles, Layers, Smartphone, Check, HelpCircle, FileText,
  AlertTriangle, LockKeyhole, HeartPulse, Menu
} from "lucide-react";

import heroIllustration from "./assets/hero_illustration.png";
import heroVideo from "./assets/hero_video.mp4";
import cryptcareIcon from "./assets/cryptcare_icon.png";
import cryptcareLogoBadge from "./assets/cryptcare_logo_badge.png";
import cardTomorrow from "./assets/card_tomorrow.png";
import cardControl from "./assets/card_control.png";
import cardMobile from "./assets/card_mobile.png";
import cardAi from "./assets/card_ai.png";
import cardCollab from "./assets/card_collab.png";
import videoExplainer from "./assets/video_explainer.mp4";

export default function LandingPage({ onLogin, onGetStarted }) {
  const prefersReducedMotion = useReducedMotion();
  const [activeNav, setActiveNav] = useState("home");
  const [hoveredNav, setHoveredNav] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);

  // Animation variants
  const fadeIn = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { duration: prefersReducedMotion ? 0 : 0.6, ease: "easeOut" }
    }
  };

  const slideUp = {
    hidden: { opacity: 0, y: prefersReducedMotion ? 0 : 28 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: prefersReducedMotion ? 0 : 0.6, ease: [0.16, 1, 0.3, 1] }
    }
  };

  const staggerContainer = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: prefersReducedMotion ? 0 : 0.12,
        delayChildren: prefersReducedMotion ? 0 : 0.15
      }
    }
  };

  const cardVariants = {
    hidden: { opacity: 0, y: prefersReducedMotion ? 0 : 35 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: prefersReducedMotion ? 0 : 0.6, ease: [0.16, 1, 0.3, 1] }
    }
  };

  const navItems = [
    { id: "home", label: "Home", href: "#hero" },
    { id: "features", label: "Features", href: "#features" },
    { id: "how-it-works", label: "How It Works", href: "#how-it-works" },
    { id: "ecosystem", label: "For Providers", href: "#ecosystem" },
    { id: "security", label: "Security", href: "#security" },
  ];

  const heroFeatures = [
    {
      title: "End-to-End Encryption",
      desc: "Client-side AES-256-GCM vault sharding",
      icon: Lock,
      color: "teal",
      bgClass: "bg-teal-500/10 text-[#0FB6AA] border-teal-500/20"
    },
    {
      title: "Digital Consent & Signatures",
      desc: "Cryptographic RSA-PSS authorization",
      icon: FileSignature,
      color: "blue",
      bgClass: "bg-blue-500/10 text-[#2F6FE0] border-blue-500/20"
    },
    {
      title: "AI-Powered Safety & Fraud",
      desc: "Real-time drug & anomaly detection",
      icon: Bot,
      color: "purple",
      bgClass: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
    },
    {
      title: "Transparent & Secure Access",
      desc: "Tamper-evident immutable audit logs",
      icon: Shield,
      color: "amber",
      bgClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20"
    }
  ];

  const workflowSteps = [
    {
      num: "01",
      title: "Create Your Sovereign Vault",
      desc: "Your records are encrypted locally with zero-knowledge keys before leaving your device.",
      icon: LockKeyhole,
      tag: "Zero-Knowledge"
    },
    {
      num: "02",
      title: "Provider Requests Access",
      desc: "Doctors, clinics, and labs send granular, time-bound access requests for specific records.",
      icon: Stethoscope,
      tag: "Granular Scope"
    },
    {
      num: "03",
      title: "Sign & Grant Consent",
      desc: "Approve with a cryptographic signature. Revoke permissions anytime with a single tap.",
      icon: FileSignature,
      tag: "RSA-PSS Verified"
    },
    {
      num: "04",
      title: "AI Prescription Guardian",
      desc: "Autonomous clinical AI checks for lethal drug interactions and duplicate prescriptions.",
      icon: Bot,
      tag: "Safety Intelligence"
    },
    {
      num: "05",
      title: "Immutable Audit Ledger",
      desc: "Every interaction is timestamped into an append-only, tamper-evident cryptographic trail.",
      icon: ShieldCheck,
      tag: "Audit Verified"
    }
  ];

  const roles = [
    {
      title: "Patients",
      role: "Sovereign Owners",
      desc: "Full ownership of personal medical history with instantaneous one-tap consent revocation.",
      icon: Users,
      color: "from-teal-500/20 to-blue-500/20",
      border: "border-teal-500/30",
      accent: "#0FB6AA"
    },
    {
      title: "Doctors",
      role: "Care Providers",
      desc: "Access verified patient records with patient consent and write digitally-signed prescriptions.",
      icon: Stethoscope,
      color: "from-blue-500/20 to-indigo-500/20",
      border: "border-blue-500/30",
      accent: "#2F6FE0"
    },
    {
      title: "Nurses",
      role: "Care Coordinators",
      desc: "Scan patient QR codes for emergency vitals and log bedside medication administrations safely.",
      icon: Activity,
      color: "from-emerald-500/20 to-teal-500/20",
      border: "border-emerald-500/30",
      accent: "#22C58B"
    },
    {
      title: "Pharmacies",
      role: "Dispense Network",
      desc: "Verify cryptographically signed prescriptions and prevent dangerous drug-drug interactions.",
      icon: Pill,
      color: "from-purple-500/20 to-pink-500/20",
      border: "border-purple-500/30",
      accent: "#A855F7"
    },
    {
      title: "Laboratories",
      role: "Diagnostic Hubs",
      desc: "Deliver tamper-evident, hash-verified diagnostic lab results straight to the patient vault.",
      icon: FlaskConical,
      color: "from-amber-500/20 to-orange-500/20",
      border: "border-amber-500/30",
      accent: "#F2A93B"
    },
    {
      title: "Insurers",
      role: "Claims Processors",
      desc: "Validate claims cryptographically without inspecting sensitive, unrelated medical records.",
      icon: Building2,
      color: "from-cyan-500/20 to-blue-500/20",
      border: "border-cyan-500/30",
      accent: "#06B6D4"
    }
  ];

  return (
    <div className="min-h-screen bg-[#EEF4F7] dark:bg-[#050D17] text-[#0B1E33] dark:text-[#E7F1F5] font-sans selection:bg-[#0FB6AA]/20 selection:text-[#0A8A82]">
      {/* ------------------------------------------------------------------ */}
      {/* 2. NAVIGATION BAR                                                  */}
      {/* ------------------------------------------------------------------ */}
      <motion.nav
        initial={{ y: prefersReducedMotion ? 0 : -25, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: prefersReducedMotion ? 0 : 0.6, ease: "easeOut" }}
        className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 dark:bg-[#050D17]/85 border-b border-[#0F283C]/08 dark:border-[#78BEC8]/15"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-gradient-to-br from-[#0FB6AA] to-[#2F6FE0] shadow-md shadow-[#0FB6AA]/25">
              <ShieldCheck size={24} className="text-white" />
            </div>
            <div>
              <span className="text-xl font-extrabold tracking-tight font-display text-[#0B1E33] dark:text-[#E7F1F5] block leading-none">
                Crypt<span className="text-[#0FB6AA]">Care</span>
              </span>
              <span className="text-[10px] tracking-wider text-slate-500 dark:text-slate-400 font-medium block leading-none mt-1">
                Your Health. Your Data. Your Control.
              </span>
            </div>
          </div>

          {/* Desktop Nav Links */}
          <div className="hidden md:flex items-center gap-1 bg-white/50 dark:bg-[#0F1C2A]/40 p-1.5 rounded-full border border-slate-200/60 dark:border-slate-800/60">
            {navItems.map((item) => {
              const isActive = activeNav === item.id;
              return (
                <a
                  key={item.id}
                  href={item.href}
                  onClick={() => setActiveNav(item.id)}
                  onMouseEnter={() => setHoveredNav(item.id)}
                  onMouseLeave={() => setHoveredNav(null)}
                  className="relative px-4 py-1.5 text-xs font-semibold rounded-full transition-colors text-slate-600 hover:text-[#0B1E33] dark:text-slate-300 dark:hover:text-white"
                >
                  <span className="relative z-10">{item.label}</span>
                  {/* Clean animated underline / indicator on hover or active */}
                  {isActive && (
                    <motion.div
                      layoutId="nav-active-pill"
                      className="absolute inset-0 bg-white dark:bg-[#0F1C2A] shadow-sm rounded-full -z-0 border border-slate-200/80 dark:border-teal-500/30"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    />
                  )}
                  {isActive && (
                    <motion.div
                      layoutId="nav-active-line"
                      className="absolute bottom-0 left-4 right-4 h-0.5 bg-gradient-to-r from-[#0FB6AA] to-[#2F6FE0] rounded-full"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    />
                  )}
                </a>
              );
            })}
          </div>

          {/* Action Buttons */}
          <div className="hidden sm:flex items-center gap-3">
            <motion.button
              whileHover={prefersReducedMotion ? {} : { scale: 1.04, boxShadow: "0 8px 20px -6px rgba(47, 111, 224, 0.25)" }}
              whileTap={prefersReducedMotion ? {} : { scale: 0.97 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
              onClick={onLogin}
              className="px-5 py-2 rounded-full text-xs font-bold text-[#0B1E33] dark:text-[#E7F1F5] bg-white dark:bg-[#0B1A28] border border-slate-300 dark:border-slate-700 hover:border-[#0FB6AA] transition-colors shadow-sm cursor-pointer"
            >
              Login
            </motion.button>
            <motion.button
              whileHover={prefersReducedMotion ? {} : { scale: 1.04, boxShadow: "0 10px 25px -6px rgba(15, 182, 170, 0.45)" }}
              whileTap={prefersReducedMotion ? {} : { scale: 0.97 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
              onClick={onGetStarted}
              className="px-5 py-2 rounded-full text-xs font-bold text-white bg-gradient-to-r from-[#0FB6AA] to-[#2F6FE0] shadow-md shadow-[#0FB6AA]/25 hover:brightness-105 transition-all cursor-pointer"
            >
              Get Started
            </motion.button>
          </div>

          {/* Mobile Menu Toggle */}
          <div className="md:hidden flex items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-xl bg-white/70 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="md:hidden overflow-hidden border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#08131F] px-4 py-4 space-y-3"
            >
              {navItems.map((item) => (
                <a
                  key={item.id}
                  href={item.href}
                  onClick={() => {
                    setActiveNav(item.id);
                    setMobileMenuOpen(false);
                  }}
                  className="block px-3 py-2 rounded-lg text-sm font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60"
                >
                  {item.label}
                </a>
              ))}
              <div className="pt-2 flex flex-col gap-2">
                <button
                  onClick={() => { setMobileMenuOpen(false); onLogin(); }}
                  className="w-full py-2.5 rounded-xl text-sm font-bold border border-slate-300 dark:border-slate-700"
                >
                  Login
                </button>
                <button
                  onClick={() => { setMobileMenuOpen(false); onGetStarted(); }}
                  className="w-full py-2.5 rounded-xl text-sm font-bold text-white bg-gradient-to-r from-[#0FB6AA] to-[#2F6FE0]"
                >
                  Get Started
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.nav>

      {/* ------------------------------------------------------------------ */}
      {/* 1. HERO SECTION                                                    */}
      {/* ------------------------------------------------------------------ */}
      <section id="hero" className="relative pt-8 pb-16 lg:pt-14 lg:pb-24 overflow-hidden">
        {/* Subtle Ambient Background Gradients */}
        <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-[520px] h-[520px] bg-gradient-to-br from-[#0FB6AA]/12 to-transparent rounded-full blur-3xl pointer-events-none -z-10" />
        <div className="absolute top-1/3 right-1/4 translate-x-1/3 w-[600px] h-[600px] bg-gradient-to-bl from-[#2F6FE0]/12 to-transparent rounded-full blur-3xl pointer-events-none -z-10" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">

            {/* Left Column: Headings, Descriptions, Actions, Highlights */}
            <div className="lg:col-span-6 space-y-6 lg:space-y-8">

              {/* 1.1 Introductory Small Tag */}
              <motion.div
                initial={{ opacity: 0, y: prefersReducedMotion ? 0 : -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: prefersReducedMotion ? 0 : 0.7, ease: "easeOut" }}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-[10.5px] sm:text-xs font-bold tracking-wider uppercase bg-white/80 dark:bg-[#0F1C2A]/80 border border-teal-500/30 text-[#0A8A82] dark:text-[#0FB6AA] shadow-sm backdrop-blur-md"
              >
                <span className="w-2 h-2 rounded-full bg-[#0FB6AA] animate-pulse" />
                <span>Patient-Sovereign, Signature-Verified Prescription Intelligence Network</span>
              </motion.div>

              {/* 1.2 Main Heading Revealed Line by Line with Smooth Upward Motion */}
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.08] font-display">
                <div className="overflow-hidden py-1">
                  <motion.span
                    className="block text-[#0B1E33] dark:text-[#E7F1F5]"
                    initial={{ y: prefersReducedMotion ? 0 : "100%", opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ duration: prefersReducedMotion ? 0 : 0.8, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
                  >
                    Your Health Data.
                  </motion.span>
                </div>
                <div className="overflow-hidden py-1">
                  <motion.span
                    className="block bg-gradient-to-r from-[#0FB6AA] via-[#1A9BE4] to-[#2F6FE0] bg-clip-text text-transparent"
                    initial={{ y: prefersReducedMotion ? 0 : "100%", opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ duration: prefersReducedMotion ? 0 : 0.8, delay: 0.35, ease: [0.16, 1, 0.3, 1] }}
                  >
                    Your Control.
                  </motion.span>
                </div>
              </h1>

              {/* 1.3 Supporting Paragraph with Slight Delay */}
              <motion.p
                initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: prefersReducedMotion ? 0 : 0.7, delay: 0.55, ease: "easeOut" }}
                className="text-base sm:text-lg text-slate-600 dark:text-slate-300 leading-relaxed max-w-xl"
              >
                A secure, AI-powered healthcare platform where patients own their medical data,
                authorize every access with digital signatures, and collaborate safely with hospitals,
                pharmacies, laboratories, and insurance providers.
              </motion.p>

              {/* 1.4 Get Started and Learn More Buttons with Hover Scale & Shadow */}
              <motion.div
                initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: prefersReducedMotion ? 0 : 0.6, delay: 0.75, ease: "easeOut" }}
                className="flex flex-wrap items-center gap-4 pt-1"
              >
                <motion.button
                  whileHover={prefersReducedMotion ? {} : { scale: 1.04, boxShadow: "0 12px 30px -6px rgba(15, 182, 170, 0.5)" }}
                  whileTap={prefersReducedMotion ? {} : { scale: 0.98 }}
                  transition={{ type: "spring", stiffness: 400, damping: 25 }}
                  onClick={onGetStarted}
                  className="px-7 py-3.5 rounded-full font-bold text-white bg-gradient-to-r from-[#0FB6AA] via-[#1E7AE8] to-[#2F6FE0] shadow-lg shadow-[#0FB6AA]/25 flex items-center gap-2 group cursor-pointer text-sm sm:text-base"
                >
                  <span>Get Started</span>
                  <ChevronRight size={18} className="transition-transform group-hover:translate-x-1" />
                </motion.button>

                <motion.button
                  whileHover={prefersReducedMotion ? {} : { scale: 1.04, boxShadow: "0 10px 24px -6px rgba(47, 111, 224, 0.25)" }}
                  whileTap={prefersReducedMotion ? {} : { scale: 0.98 }}
                  transition={{ type: "spring", stiffness: 400, damping: 25 }}
                  onClick={() => setShowVideoModal(true)}
                  className="px-6 py-3.5 rounded-full font-bold text-[#0B1E33] dark:text-[#E7F1F5] bg-white/80 dark:bg-[#0F1C2A]/80 border border-slate-300 dark:border-slate-700 hover:border-[#0FB6AA] backdrop-blur-md shadow-sm flex items-center gap-2.5 cursor-pointer text-sm sm:text-base transition-colors"
                >
                  <div className="w-6 h-6 rounded-full bg-[#0FB6AA]/15 flex items-center justify-center text-[#0FB6AA]">
                    <Play size={12} className="fill-current ml-0.5" />
                  </div>
                  <span>Watch Video</span>
                </motion.button>
              </motion.div>

              {/* 1.5 Four Feature Highlights with Staggered Entrance */}
              <motion.div
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
                className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 pt-4 border-t border-slate-200/80 dark:border-slate-800/80"
              >
                {heroFeatures.map((f, idx) => {
                  const Icon = f.icon;
                  return (
                    <motion.div
                      key={idx}
                      variants={slideUp}
                      whileHover={prefersReducedMotion ? {} : { y: -4 }}
                      transition={{ duration: 0.2 }}
                      className="p-3 rounded-2xl bg-white/70 dark:bg-[#0F1C2A]/50 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-sm shadow-xs group"
                    >
                      <motion.div
                        whileHover={prefersReducedMotion ? {} : { scale: 1.15 }}
                        transition={{ type: "spring", stiffness: 400, damping: 20 }}
                        className={`w-9 h-9 rounded-xl flex items-center justify-center border mb-2 ${f.bgClass}`}
                      >
                        <Icon size={18} />
                      </motion.div>
                      <h4 className="text-xs font-bold leading-tight text-[#0B1E33] dark:text-[#E7F1F5] group-hover:text-[#0FB6AA] transition-colors">
                        {f.title}
                      </h4>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 leading-snug line-clamp-2">
                        {f.desc}
                      </p>
                    </motion.div>
                  );
                })}
              </motion.div>

            </div>

            {/* Right Column: Hero Illustration Artwork (Stationary artwork with subtle float) */}
            <div className="lg:col-span-6 flex items-center justify-center">
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{
                  opacity: 1,
                  scale: 1,
                  y: prefersReducedMotion ? 0 : [0, -8, 0],
                }}
                transition={{
                  opacity: { duration: 0.8, delay: 0.3 },
                  scale: { duration: 0.8, delay: 0.3, ease: "easeOut" },
                  y: { duration: 6, repeat: Infinity, ease: "easeInOut" },
                }}
                className="relative w-full max-w-[620px] lg:max-w-none flex items-center justify-center"
              >
                {/* Soft ambient back-glow behind artwork */}
                <div className="absolute inset-0 bg-gradient-to-tr from-[#0FB6AA]/25 via-[#2F6FE0]/20 to-transparent rounded-full filter blur-3xl transform scale-105 -z-10 pointer-events-none" />

                {/* Hero Animated Video with Seamless Background Blend */}
                <div className="relative w-full flex items-center justify-center">
                  <video
                    src={heroVideo}
                    autoPlay
                    loop
                    muted
                    playsInline
                    className="w-full h-auto object-contain select-none"
                    style={{
                      WebkitMaskImage:
                        "radial-gradient(ellipse 85% 80% at 50% 50%, black 40%, rgba(0,0,0,0.8) 58%, transparent 82%)",
                      maskImage:
                        "radial-gradient(ellipse 85% 80% at 50% 50%, black 40%, rgba(0,0,0,0.8) 58%, transparent 82%)",
                    }}
                  />
                </div>
              </motion.div>
            </div>

          </div>
        </div>

        {/* Bottom Banner Wave Strip */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mt-14 max-w-6xl mx-auto px-4"
        >
          <div className="py-3 px-6 rounded-2xl bg-gradient-to-r from-[#0FB6AA]/15 via-[#2F6FE0]/15 to-[#0FB6AA]/15 border border-[#0FB6AA]/25 backdrop-blur-md flex flex-wrap items-center justify-around gap-4 text-xs font-semibold text-slate-700 dark:text-slate-200">
            <span className="flex items-center gap-2">
              <ShieldCheck size={16} className="text-[#0FB6AA]" />
              End-to-End Privacy
            </span>
            <span className="hidden sm:inline text-slate-400">•</span>
            <span className="flex items-center gap-2">
              <Lock size={16} className="text-[#2F6FE0]" />
              True Patient Ownership
            </span>
            <span className="hidden sm:inline text-slate-400">•</span>
            <span className="flex items-center gap-2">
              <HeartPulse size={16} className="text-[#0FB6AA]" />
              Better Medication Safety
            </span>
            <span className="hidden sm:inline text-slate-400">•</span>
            <span className="flex items-center gap-2">
              <Layers size={16} className="text-[#2F6FE0]" />
              Zero-Knowledge Healthcare Ecosystem
            </span>
          </div>
        </motion.div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* 3 & 4. FEATURE CARDS & VISUAL HIGHLIGHTS                            */}
      {/* ------------------------------------------------------------------ */}
      <section id="features" className="py-20 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

          {/* Section Heading Revealed with Upward Motion */}
          <motion.div
            initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: prefersReducedMotion ? 0 : 0.6 }}
            className="text-center max-w-3xl mx-auto mb-16 space-y-3"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider text-[#0FB6AA] bg-[#0FB6AA]/10 border border-[#0FB6AA]/20">
              <Sparkles size={14} /> Comprehensive Sovereign Features
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight font-display text-[#0B1E33] dark:text-[#E7F1F5]">
              Engineered for Absolute Privacy & Clinical Excellence
            </h2>
            <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400">
              Explore how CryptCare unites cutting-edge cryptographic security with clinical AI to keep you safe.
            </p>
          </motion.div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">

            {/* Card 1: Secure Healthcare for a Healthier Tomorrow */}
            <motion.div
              variants={cardVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.2 }}
              whileHover={prefersReducedMotion ? {} : { y: -6, boxShadow: "0 20px 35px -15px rgba(15, 182, 170, 0.22)" }}
              className="rounded-3xl overflow-hidden bg-white/70 dark:bg-[#0F1C2A]/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-xl shadow-md transition-all flex flex-col justify-between group"
            >
              <div className="overflow-hidden">
                <motion.img
                  whileHover={prefersReducedMotion ? {} : { scale: 1.03 }}
                  transition={{ duration: 0.4 }}
                  src={cardTomorrow}
                  alt="Secure Healthcare for a Healthier Tomorrow"
                  className="w-full h-52 object-cover object-center"
                />
              </div>
              <div className="p-6 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-[#0FB6AA]">
                  <ShieldCheck size={15} /> Proactive Family Protection
                </div>
                <h3 className="text-xl font-bold text-[#0B1E33] dark:text-[#E7F1F5] group-hover:text-[#0FB6AA] transition-colors">
                  Secure Healthcare for a Healthier Tomorrow
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  Strong privacy today ensures safer, coordinated care for generations. Maintain generational medical records safely locked.
                </p>
              </div>
            </motion.div>

            {/* Card 2: Your Records. Your Control. */}
            <motion.div
              variants={cardVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.2 }}
              whileHover={prefersReducedMotion ? {} : { y: -6, boxShadow: "0 20px 35px -15px rgba(47, 111, 224, 0.25)" }}
              className="rounded-3xl overflow-hidden bg-white/70 dark:bg-[#0F1C2A]/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-xl shadow-md transition-all flex flex-col justify-between group"
            >
              <div className="overflow-hidden">
                <motion.img
                  whileHover={prefersReducedMotion ? {} : { scale: 1.03 }}
                  transition={{ duration: 0.4 }}
                  src={cardControl}
                  alt="Your Records. Your Control."
                  className="w-full h-52 object-cover object-center"
                />
              </div>
              <div className="p-6 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-[#2F6FE0]">
                  <Lock size={15} /> Holographic Health Vault
                </div>
                <h3 className="text-xl font-bold text-[#0B1E33] dark:text-[#E7F1F5] group-hover:text-[#2F6FE0] transition-colors">
                  Your Records. Your Control.
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  Access, share, and manage medical prescriptions, lab reports, and imaging history with absolute transparency and consent verification.
                </p>
              </div>
            </motion.div>

            {/* Card 3: AI for Safer Prescriptions */}
            <motion.div
              variants={cardVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.2 }}
              whileHover={prefersReducedMotion ? {} : { y: -6, boxShadow: "0 20px 35px -15px rgba(15, 182, 170, 0.22)" }}
              className="rounded-3xl overflow-hidden bg-white/70 dark:bg-[#0F1C2A]/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-xl shadow-md transition-all flex flex-col justify-between group"
            >
              <div className="overflow-hidden">
                <motion.img
                  whileHover={prefersReducedMotion ? {} : { scale: 1.03 }}
                  transition={{ duration: 0.4 }}
                  src={cardAi}
                  alt="AI for Safer Prescriptions"
                  className="w-full h-52 object-cover object-center"
                />
              </div>
              <div className="p-6 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-purple-500">
                  <Bot size={15} /> Real-Time Clinical Guardian
                </div>
                <h3 className="text-xl font-bold text-[#0B1E33] dark:text-[#E7F1F5] group-hover:text-purple-500 transition-colors">
                  AI for Safer Prescriptions
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  Automatically flags dangerous drug interactions, duplicate medications, and allergy contraindications before fulfillment.
                </p>
              </div>
            </motion.div>

            {/* Card 4: All Your Health Information in One Secure Place */}
            <motion.div
              variants={cardVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.2 }}
              whileHover={prefersReducedMotion ? {} : { y: -6, boxShadow: "0 20px 35px -15px rgba(15, 182, 170, 0.22)" }}
              className="rounded-3xl overflow-hidden bg-white/70 dark:bg-[#0F1C2A]/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-xl shadow-md transition-all flex flex-col justify-between group md:col-span-2 lg:col-span-1"
            >
              <div className="overflow-hidden">
                <motion.img
                  whileHover={prefersReducedMotion ? {} : { scale: 1.03 }}
                  transition={{ duration: 0.4 }}
                  src={cardMobile}
                  alt="All Your Health Information in One Secure Place"
                  className="w-full h-52 object-cover object-center"
                />
              </div>
              <div className="p-6 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-teal-600 dark:text-teal-400">
                  <Smartphone size={15} /> Mobile Sovereign Access
                </div>
                <h3 className="text-xl font-bold text-[#0B1E33] dark:text-[#E7F1F5] group-hover:text-[#0FB6AA] transition-colors">
                  Personal Vault in Your Pocket
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  A personal health vault designed for your privacy and peace of mind. Review consent requests on mobile with biometric approval.
                </p>
              </div>
            </motion.div>

            {/* Card 5: Better Collaboration for Better Care */}
            <motion.div
              variants={cardVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.2 }}
              whileHover={prefersReducedMotion ? {} : { y: -6, boxShadow: "0 20px 35px -15px rgba(47, 111, 224, 0.25)" }}
              className="rounded-3xl overflow-hidden bg-white/70 dark:bg-[#0F1C2A]/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-xl shadow-md transition-all flex flex-col justify-between group md:col-span-2 lg:col-span-2"
            >
              <div className="overflow-hidden">
                <motion.img
                  whileHover={prefersReducedMotion ? {} : { scale: 1.02 }}
                  transition={{ duration: 0.4 }}
                  src={cardCollab}
                  alt="Better Collaboration for Better Care"
                  className="w-full h-52 object-cover object-center"
                />
              </div>
              <div className="p-6 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-blue-600 dark:text-blue-400">
                  <HeartPulse size={15} /> Unified Ecosystem
                </div>
                <h3 className="text-xl font-bold text-[#0B1E33] dark:text-[#E7F1F5] group-hover:text-[#2F6FE0] transition-colors">
                  Better Collaboration for Better Care
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  Bringing together patients, doctors, pharmacies, laboratories, and insurance providers in a unified, mathematically trusted network.
                </p>
              </div>
            </motion.div>

          </div>

        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* 5. HOW IT WORKS SECTION (Sequential Step Reveals)                  */}
      {/* ------------------------------------------------------------------ */}
      <section id="how-it-works" className="py-20 relative bg-slate-100/60 dark:bg-[#08131F]/50 border-y border-slate-200/80 dark:border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

          <motion.div
            initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: prefersReducedMotion ? 0 : 0.6 }}
            className="text-center max-w-3xl mx-auto mb-16 space-y-3"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider text-[#2F6FE0] bg-[#2F6FE0]/10 border border-[#2F6FE0]/20">
              <Layers size={14} /> Cryptographic Lifecycle
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight font-display text-[#0B1E33] dark:text-[#E7F1F5]">
              How CryptCare Works
            </h2>
            <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400">
              Five clear steps from initial sovereign vault creation to append-only tamper-evident verification.
            </p>
          </motion.div>

          {/* Sequential Step Timeline */}
          <div className="relative">
            {/* Connecting line between steps */}
            <div className="hidden lg:block absolute top-1/2 left-8 right-8 h-0.5 bg-gradient-to-r from-[#0FB6AA] via-[#2F6FE0] to-[#0FB6AA] -translate-y-8 -z-0 opacity-40" />

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 relative z-10">
              {workflowSteps.map((step, idx) => {
                const Icon = step.icon;
                return (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 35 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.2 }}
                    transition={{
                      duration: prefersReducedMotion ? 0 : 0.6,
                      delay: prefersReducedMotion ? 0 : idx * 0.12,
                      ease: [0.16, 1, 0.3, 1]
                    }}
                    whileHover={prefersReducedMotion ? {} : { y: -8, boxShadow: "0 18px 30px -12px rgba(15, 182, 170, 0.25)" }}
                    className="p-6 rounded-2xl bg-white/80 dark:bg-[#0F1C2A]/75 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-md shadow-sm transition-all group flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <span className="text-2xl font-black font-display text-[#0FB6AA]/80 group-hover:text-[#0FB6AA] transition-colors">
                          {step.num}
                        </span>
                        <motion.div
                          whileHover={prefersReducedMotion ? {} : { scale: 1.15 }}
                          className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#0FB6AA]/15 to-[#2F6FE0]/15 flex items-center justify-center text-[#0FB6AA]"
                        >
                          <Icon size={20} />
                        </motion.div>
                      </div>
                      <h4 className="text-base font-bold text-[#0B1E33] dark:text-[#E7F1F5] mb-2 group-hover:text-[#0FB6AA] transition-colors">
                        {step.title}
                      </h4>
                      <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                        {step.desc}
                      </p>
                    </div>
                    <div>
                      <span className="inline-block text-[10px] font-mono font-bold tracking-wider uppercase px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                        {step.tag}
                      </span>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>

        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* 6. HEALTHCARE ECOSYSTEM ROLES                                      */}
      {/* ------------------------------------------------------------------ */}
      <section id="ecosystem" className="py-20 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

          <motion.div
            initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: prefersReducedMotion ? 0 : 0.6 }}
            className="text-center max-w-3xl mx-auto mb-16 space-y-3"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider text-[#0FB6AA] bg-[#0FB6AA]/10 border border-[#0FB6AA]/20">
              <Users size={14} /> Multi-Stakeholder Platform
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight font-display text-[#0B1E33] dark:text-[#E7F1F5]">
              Tailored Workflows for Every Healthcare Role
            </h2>
            <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400">
              Role-based cryptography guarantees everyone gets exactly the scope they need—and nothing more.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {roles.map((r, idx) => {
              const Icon = r.icon;
              return (
                <motion.div
                  key={idx}
                  variants={cardVariants}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ delay: prefersReducedMotion ? 0 : idx * 0.08 }}
                  whileHover={prefersReducedMotion ? {} : { y: -6, boxShadow: "0 18px 30px -12px rgba(15, 182, 170, 0.25)" }}
                  className="p-6 rounded-3xl bg-white/70 dark:bg-[#0F1C2A]/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-xl shadow-xs transition-all group"
                >
                  <div className="flex items-center gap-4 mb-4">
                    <motion.div
                      whileHover={prefersReducedMotion ? {} : { scale: 1.12 }}
                      className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${r.color} flex items-center justify-center shadow-xs border ${r.border}`}
                    >
                      <Icon size={24} style={{ color: r.accent }} />
                    </motion.div>
                    <div>
                      <h4 className="text-lg font-bold text-[#0B1E33] dark:text-[#E7F1F5] leading-tight">
                        {r.title}
                      </h4>
                      <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                        {r.role}
                      </span>
                    </div>
                  </div>
                  <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                    {r.desc}
                  </p>
                </motion.div>
              );
            })}
          </div>

        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* 7. LIVE SECURITY METRICS & CALL TO ACTION                          */}
      {/* ------------------------------------------------------------------ */}
      <section id="security" className="py-20 relative bg-gradient-to-b from-transparent via-[#0FB6AA]/05 to-transparent">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

          {/* Security Stats Bar */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="p-8 sm:p-10 rounded-3xl bg-gradient-to-r from-white/90 via-white/80 to-white/90 dark:from-[#0B1A28]/90 dark:via-[#0F1C2A]/80 dark:to-[#0B1A28]/90 border border-teal-500/30 backdrop-blur-xl shadow-xl shadow-[#0FB6AA]/10"
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center divide-y md:divide-y-0 md:divide-x divide-slate-200/80 dark:divide-slate-800">
              <div className="pt-4 md:pt-0">
                <div className="text-3xl sm:text-4xl font-extrabold font-display bg-gradient-to-r from-[#0FB6AA] to-[#2F6FE0] bg-clip-text text-transparent">
                  2,481+
                </div>
                <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 mt-1 uppercase tracking-wider">
                  Active Verified Users
                </div>
              </div>
              <div className="pt-4 md:pt-0">
                <div className="text-3xl sm:text-4xl font-extrabold font-display text-[#0FB6AA]">
                  99.98%
                </div>
                <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 mt-1 uppercase tracking-wider">
                  System Uptime
                </div>
              </div>
              <div className="pt-4 md:pt-0">
                <div className="text-3xl sm:text-4xl font-extrabold font-display text-emerald-500">
                  0
                </div>
                <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 mt-1 uppercase tracking-wider">
                  Open Threats Detected
                </div>
              </div>
              <div className="pt-4 md:pt-0">
                <div className="text-3xl sm:text-4xl font-extrabold font-display text-[#2F6FE0]">
                  64
                </div>
                <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 mt-1 uppercase tracking-wider">
                  Distributed Vault Shards
                </div>
              </div>
            </div>
          </motion.div>

          {/* Bottom Call to Action Card */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7 }}
            className="mt-16 text-center max-w-3xl mx-auto space-y-6"
          >
            <h3 className="text-2xl sm:text-3xl font-extrabold font-display text-[#0B1E33] dark:text-[#E7F1F5]">
              Ready to Take Sovereign Control of Your Health Data?
            </h3>
            <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300">
              Join thousands of patients, doctors, and healthcare institutions operating on the world's most secure patient-centric intelligence network.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <motion.button
                whileHover={prefersReducedMotion ? {} : { scale: 1.05, boxShadow: "0 12px 30px -6px rgba(15, 182, 170, 0.5)" }}
                whileTap={prefersReducedMotion ? {} : { scale: 0.98 }}
                onClick={onGetStarted}
                className="px-8 py-3.5 rounded-full font-bold text-white bg-gradient-to-r from-[#0FB6AA] to-[#2F6FE0] shadow-lg shadow-[#0FB6AA]/30 text-sm sm:text-base cursor-pointer"
              >
                Create Free Sovereign Vault
              </motion.button>
              <motion.button
                whileHover={prefersReducedMotion ? {} : { scale: 1.05 }}
                whileTap={prefersReducedMotion ? {} : { scale: 0.98 }}
                onClick={onLogin}
                className="px-8 py-3.5 rounded-full font-bold text-[#0B1E33] dark:text-[#E7F1F5] bg-white dark:bg-[#0B1A28] border border-slate-300 dark:border-slate-700 hover:border-[#0FB6AA] shadow-sm text-sm sm:text-base cursor-pointer transition-colors"
              >
                Sign In to Vault
              </motion.button>
            </div>
          </motion.div>

        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* 8. FOOTER                                                          */}
      {/* ------------------------------------------------------------------ */}
      <footer className="border-t border-slate-200/80 dark:border-slate-800/80 bg-white/70 dark:bg-[#050D17]/90 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-[#0FB6AA] to-[#2F6FE0] text-white">
              <ShieldCheck size={20} />
            </div>
            <div>
              <span className="font-extrabold font-display text-sm">
                Crypt<span className="text-[#0FB6AA]">Care</span>
              </span>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">
                Sovereign Healthcare Intelligence & Prescription Network
              </p>
            </div>
          </div>

          <div className="flex items-center gap-6 text-xs text-slate-500 dark:text-slate-400">
            <span>HIPAA Compliant Architecture</span>
            <span>•</span>
            <span>Zero-Knowledge AES-256-GCM</span>
            <span>•</span>
            <span>RSA-PSS Signatures</span>
          </div>

          <p className="text-xs text-slate-400">
            © {new Date().getFullYear()} CryptCare. All rights reserved.
          </p>
        </div>
      </footer>

      {/* ------------------------------------------------------------------ */}
      {/* 9. VIDEO MODAL (Watch Video / Explainer)                           */}
      {/* ------------------------------------------------------------------ */}
      <AnimatePresence>
        {showVideoModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4"
            onClick={() => setShowVideoModal(false)}
          >
            <motion.div
              initial={{ scale: 0.92, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.92, opacity: 0 }}
              transition={{ type: "spring", stiffness: 350, damping: 28 }}
              className="w-full max-w-4xl bg-slate-900 border border-teal-500/30 rounded-2xl overflow-hidden shadow-2xl relative"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-950/80">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#0FB6AA]">
                  <Play size={14} className="fill-current" /> CryptCare Platform Explainer
                </div>
                <button
                  onClick={() => setShowVideoModal(false)}
                  className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="aspect-video bg-black flex items-center justify-center">
                <video
                  src={videoExplainer}
                  controls
                  autoPlay
                  className="w-full h-full object-contain"
                />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
