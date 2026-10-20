import React, { useState } from "react";
import { Menu, X } from "lucide-react";
import cryptcareIcon from "./assets/cryptcare_icon.png";

export function AuthNavBar({ onBackToLanding }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: "Home", onClick: onBackToLanding },
    { label: "About", onClick: onBackToLanding },
    { label: "Features", onClick: onBackToLanding },
    { label: "Contact", onClick: onBackToLanding },
  ];

  return (
    <header className="w-full relative z-30 py-4 px-4 sm:px-8 lg:px-12 flex items-center justify-between">
      {/* Brand on mobile/tablet if hero is stacked */}
      <button
        type="button"
        onClick={onBackToLanding}
        className="flex items-center gap-2.5 focus:outline-none lg:invisible"
      >
        <img src={cryptcareIcon} alt="CryptCare" className="w-8 h-8 object-contain" />
        <span className="text-xl font-extrabold font-display text-[#0B2038]">
          Crypt<span className="text-[#0FB6AA]">Care</span>
        </span>
      </button>

      {/* Desktop Navigation Links */}
      <nav className="hidden lg:flex items-center gap-8 ml-auto">
        {navLinks.map((item, idx) => (
          <button
            key={idx}
            onClick={item.onClick}
            className="text-sm font-medium text-slate-600 hover:text-[#0FB6AA] transition-colors focus:outline-none cursor-pointer"
          >
            {item.label}
          </button>
        ))}
      </nav>

      {/* Mobile Hamburger Button */}
      <div className="lg:hidden ml-auto">
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 rounded-xl text-slate-600 hover:text-[#0FB6AA] hover:bg-white/60 transition-colors focus:outline-none"
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="absolute top-full left-4 right-4 mt-2 p-4 bg-white/95 backdrop-blur-xl border border-slate-100 rounded-2xl shadow-xl lg:hidden flex flex-col gap-3 z-50 animate-fade-in">
          {navLinks.map((item, idx) => (
            <button
              key={idx}
              onClick={() => {
                setMobileMenuOpen(false);
                item.onClick();
              }}
              className="text-left text-sm font-semibold text-slate-700 hover:text-[#0FB6AA] p-2 rounded-lg hover:bg-slate-50 transition-colors"
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </header>
  );
}

export function AuthBottomWaves() {
  return (
    <div className="fixed bottom-0 left-0 right-0 pointer-events-none z-0 overflow-hidden leading-none h-32 sm:h-44 md:h-52">
      <svg
        className="absolute bottom-0 w-full h-full"
        viewBox="0 0 1440 320"
        preserveAspectRatio="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="waveGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0FB6AA" stopOpacity="0.18" />
            <stop offset="50%" stopColor="#38BDF8" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#2F6FE0" stopOpacity="0.25" />
          </linearGradient>
          <linearGradient id="waveGrad2" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.30" />
            <stop offset="60%" stopColor="#0FB6AA" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#60A5FA" stopOpacity="0.32" />
          </linearGradient>
        </defs>

        {/* Back Wave */}
        <path
          fill="url(#waveGrad1)"
          d="M0,160L48,176C96,192,192,224,288,218.7C384,213,480,171,576,165.3C672,160,768,192,864,208C960,224,1056,224,1152,202.7C1248,181,1344,139,1392,117.3L1440,96L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"
        />

        {/* Front Wave */}
        <path
          fill="url(#waveGrad2)"
          d="M0,224L48,208C96,192,192,160,288,165.3C384,171,480,213,576,213.3C672,213,768,171,864,160C960,149,1056,171,1152,186.7C1248,203,1344,213,1392,218.7L1440,224L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"
        />
      </svg>
    </div>
  );
}
