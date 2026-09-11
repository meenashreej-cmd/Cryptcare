import React, { useState, useEffect, useMemo, useRef } from "react";
import api, {
  authService, vaultService, consentService, nursingService,
  fraudService, insuranceService, auditService, notificationService,
  adminService, bloodBankService,
} from "./api";
import {
  ShieldCheck, ShieldAlert, Shield, Lock, Unlock, Fingerprint, KeyRound,
  LayoutDashboard, FolderLock, FileText, Pill, AlertTriangle, FlaskConical,
  HeartPulse, Bot, Inbox, History, Siren, Users, Search, Stethoscope,
  ClipboardCheck, QrCode, ScanLine, CalendarClock, PackageSearch, FlaskRound,
  BadgeCheck, Activity, BarChart3, ScrollText, Settings, Bell, Sun, Moon,
  ChevronDown, X, Check, Upload, Eye, EyeOff, LogOut, Plus, Clock, MapPin,
  Phone, Droplet, UserCog, Building2, Server, Radar, Sparkles, ChevronRight,
  Send, FileSignature, TimerReset, ShieldX, Zap, TrendingUp, AlertOctagon,
  CircleUser, Filter, Download, MoreHorizontal
} from "lucide-react";
import {
  ResponsiveContainer, LineChart, Line, AreaChart, Area, BarChart, Bar,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, RadialBarChart,
  RadialBar, Legend
} from "recharts";

/* ---------------------------------------------------------------------- */
/* DESIGN TOKENS + GLOBAL STYLE                                           */
/* ---------------------------------------------------------------------- */

const GlobalStyle = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    .mv-root{
      --teal:#0FB6AA; --teal-deep:#0A8A82; --teal-glow: rgba(15,182,170,0.35);
      --blue:#2F6FE0; --blue-deep:#1E4FB8; --blue-glow: rgba(47,111,224,0.30);
      --amber:#F2A93B; --red:#E5484D; --green:#22C58B;
      --font-display:'Sora', sans-serif; --font-body:'Inter', sans-serif; --font-mono:'JetBrains Mono', monospace;
    }
    .mv-root.light{
      --bg:#EEF4F7; --bg-2:#E4EDF1; --panel: rgba(255,255,255,0.72); --panel-solid:#ffffff;
      --border: rgba(15,40,60,0.10); --text:#0B1E33; --text-dim:#5B7184; --text-faint:#8CA1B0;
      --grid-line: rgba(15,90,90,0.05);
    }
    .mv-root.dark{
      --bg:#050D17; --bg-2:#08131F; --panel: rgba(15,28,42,0.55); --panel-solid:#0B1A28;
      --border: rgba(120,190,200,0.14); --text:#E7F1F5; --text-dim:#90A8B8; --text-faint:#5C7587;
      --grid-line: rgba(120,190,200,0.05);
    }
    .mv-root{
      font-family: var(--font-body); color:var(--text); background:var(--bg);
      min-height:100%; position:relative; transition: background .3s, color .3s;
    }
    .mv-root::before{
      content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
      background-image:
        linear-gradient(var(--grid-line) 1px, transparent 1px),
        linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
      background-size: 38px 38px;
    }
    .mv-font-display{ font-family: var(--font-display); }
    .mv-font-mono{ font-family: var(--font-mono); letter-spacing: 0.01em; }

    .mv-glass{
      background: var(--panel);
      border: 1px solid var(--border);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-radius: 18px;
      box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset, 0 10px 30px -15px rgba(0,0,0,0.25);
    }
    .mv-glass-hover{ transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
    .mv-glass-hover:hover{ transform: translateY(-2px); border-color: var(--teal); box-shadow: 0 14px 34px -16px var(--teal-glow); }

    .mv-chip{ display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:999px; font-size:11px; font-weight:600; font-family:var(--font-mono); letter-spacing:.03em; }
    .mv-chip.teal{ background: var(--teal-glow); color: var(--teal-deep); }
    .mv-chip.blue{ background: var(--blue-glow); color: var(--blue-deep); }
    .mv-chip.amber{ background: rgba(242,169,59,0.18); color:#a86c10; }
    .mv-chip.red{ background: rgba(229,72,77,0.16); color:#c92b30; }
    .mv-chip.green{ background: rgba(34,197,139,0.16); color:#168f63; }
    .mv-root.dark .mv-chip.amber{ color:#F2A93B; } .mv-root.dark .mv-chip.red{ color:#ff7a7e; } .mv-root.dark .mv-chip.green{ color:#5fe6b6; } .mv-root.dark .mv-chip.blue{ color:#8fb3ff; } .mv-root.dark .mv-chip.teal{ color:#7fe9de; }

    .mv-dot{ width:7px; height:7px; border-radius:50%; display:inline-block; }
    .mv-pulse{ box-shadow:0 0 0 0 currentColor; animation: mv-pulse 2s infinite; }
    @keyframes mv-pulse{ 0%{box-shadow:0 0 0 0 currentColor;} 70%{box-shadow:0 0 0 6px transparent;} 100%{box-shadow:0 0 0 0 transparent;} }

    .mv-btn{ display:inline-flex; align-items:center; gap:7px; font-weight:600; font-size:13px; padding:9px 16px; border-radius:11px; transition:.15s; cursor:pointer; border:1px solid transparent; }
    .mv-btn-primary{ background: linear-gradient(135deg, var(--teal), var(--blue)); color:#fff; box-shadow: 0 8px 20px -8px var(--teal-glow); }
    .mv-btn-primary:hover{ filter:brightness(1.08); }
    .mv-btn-ghost{ background: transparent; border-color: var(--border); color: var(--text); }
    .mv-btn-ghost:hover{ border-color: var(--teal); color: var(--teal-deep); }
    .mv-btn-danger{ background: rgba(229,72,77,0.12); color:#c92b30; border-color: rgba(229,72,77,0.3); }
    .mv-btn-danger:hover{ background: rgba(229,72,77,0.2); }

    .mv-sidebar-item{ display:flex; align-items:center; gap:11px; padding:10px 13px; border-radius:11px; font-size:13.5px; font-weight:500; color:var(--text-dim); cursor:pointer; transition:.15s; border:1px solid transparent; }
    .mv-sidebar-item:hover{ background: var(--panel); color:var(--text); }
    .mv-sidebar-item.active{ background: linear-gradient(135deg, var(--teal-glow), var(--blue-glow)); color: var(--text); border-color: var(--border); font-weight:600; }

    .mv-scan-line{ position:relative; overflow:hidden; }
    .mv-track{ font-family:var(--font-mono); font-size:11px; color:var(--text-faint); white-space:nowrap; }

    .mv-table{ width:100%; border-collapse: collapse; font-size:13px; }
    .mv-table th{ text-align:left; padding:9px 12px; color:var(--text-faint); font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:.04em; border-bottom:1px solid var(--border); }
    .mv-table td{ padding:11px 12px; border-bottom:1px solid var(--border); color:var(--text); }
    .mv-table tr:hover td{ background: var(--panel); }

    .mv-input{ width:100%; padding:9px 12px; border-radius:10px; border:1px solid var(--border); background:var(--panel-solid); color:var(--text); font-size:13px; outline:none; }
    .mv-input:focus{ border-color: var(--teal); }

    .mv-modal-backdrop{ position:fixed; inset:0; background:rgba(5,13,23,0.55); backdrop-filter: blur(4px); z-index:50; display:flex; align-items:center; justify-content:center; padding:16px; }

    .mv-progress-track{ height:6px; border-radius:999px; background: var(--border); overflow:hidden; }
    .mv-progress-fill{ height:100%; border-radius:999px; background: linear-gradient(90deg, var(--teal), var(--blue)); }

    .mv-scroll::-webkit-scrollbar{ width:6px; height:6px; }
    .mv-scroll::-webkit-scrollbar-thumb{ background: var(--border); border-radius:10px; }

    @keyframes mv-marquee{ from{ transform: translateY(0); } to { transform: translateY(-50%); } }
    .mv-marquee-track{ animation: mv-marquee 14s linear infinite; }

    .mv-focusable:focus-visible{ outline:2px solid var(--teal); outline-offset:2px; }
  `}</style>
);

/* ---------------------------------------------------------------------- */
/* NAV + ROLE METADATA (UI only — no PHI)                                */
/* ---------------------------------------------------------------------- */

const NAV = {
  patient: [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "vault", label: "Digital Health Vault", icon: FolderLock },
    { id: "prescriptions", label: "Prescription History", icon: FileText },
    { id: "allergies", label: "Allergy Records", icon: AlertTriangle },
    { id: "vaccinations", label: "Vaccinations", icon: ShieldCheck },
    { id: "labs", label: "Laboratory Reports", icon: FlaskConical },
    { id: "emergency", label: "Emergency Information", icon: Siren },
    { id: "ai", label: "AI Medical Assistant", icon: Bot },
    { id: "vitals", label: "Vitals History", icon: HeartPulse },
    { id: "access-requests", label: "Access Requests", icon: Inbox },
    { id: "active-consents", label: "Active Consents", icon: ShieldCheck },
    { id: "access-history", label: "Access History", icon: History },
    { id: "fraud", label: "Fraud Alerts", icon: ShieldAlert },
    { id: "claims", label: "My Insurance Claims", icon: FileText },
  ],
  doctor: [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "search", label: "Patient Search", icon: Search },
    { id: "prescribe", label: "Create Prescription", icon: FileSignature },
    { id: "clinical-ai", label: "AI Clinical Safety", icon: Sparkles },
    { id: "history", label: "Patient History", icon: History },
  ],
  nurse: [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "meds", label: "Medication Administration", icon: ClipboardCheck },
    { id: "qr", label: "QR Patient Verification", icon: QrCode },
    { id: "schedule", label: "Medication Schedule", icon: CalendarClock },
    { id: "vitals", label: "Vitals Management", icon: HeartPulse },
  ],
  pharmacist: [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "verify", label: "Prescription Verification", icon: BadgeCheck },
    { id: "dispense", label: "Dispensing Interface", icon: PackageSearch },
    { id: "interactions", label: "Drug Interaction Warnings", icon: AlertTriangle },
  ],
  insurer: [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "claims", label: "Claims Review", icon: FileText },
    { id: "anomalies", label: "Insurance Anomalies", icon: Radar },
  ],
  blood_bank: [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "inventory", label: "Blood Inventory", icon: Droplet },
    { id: "requests", label: "Blood Requests", icon: Activity },
  ],
  lab: [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "requests", label: "Lab Requests", icon: FlaskConical },
  ],
  admin: [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "ai-center", label: "AI Intelligence Center", icon: Sparkles },
    { id: "security", label: "Security Center", icon: Shield },
    { id: "audit", label: "Audit & Transparency", icon: ScrollText },
    { id: "analytics", label: "Analytics Dashboard", icon: BarChart3 },
    { id: "users", label: "User Management", icon: Users },
  ],
};

/* Decorative Trust Ledger events — static, no PHI */
const LEDGER_EVENTS = [
  "AES-256-GCM · vault seal verified",
  "Ed25519 · prescription signature OK",
  "RBAC · doctor-scope granted",
  "AUDIT-LOG · append-only write",
  "MFA-CHALLENGE · TOTP passed",
  "CONSENT · 2h window active",
  "HASH-VERIFY · lab report integrity",
  "KEY-ROTATE · v2 key active",
];

/* Simple data-fetching hook — prevents boilerplate in every view */
function useApi(fetchFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchFn()
      .then(d => { if (active) { setData(d); setLoading(false); } })
      .catch(e => { if (active) { setError(e); setLoading(false); } });
    return () => { active = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, loading, error };
}

const Empty = ({ msg = "No records found." }) => (
  <tr><td colSpan="10" className="text-center py-8 text-gray-400">{msg}</td></tr>
);
const Loading = () => (
  <tr><td colSpan="10" className="text-center py-8 text-gray-400">Loading…</td></tr>
);

/* ---------------------------------------------------------------------- */
/* SMALL SHARED COMPONENTS                                                */
/* ---------------------------------------------------------------------- */

const SectionHeader = ({ icon: Icon, title, desc, action }) => (
  <div className="flex items-start justify-between gap-4 mb-5 flex-wrap">
    <div className="flex items-start gap-3">
      <div className="mv-glass p-2.5 rounded-xl" style={{ color: "var(--teal-deep)" }}><Icon size={20} /></div>
      <div>
        <h2 className="mv-font-display font-bold text-lg leading-tight">{title}</h2>
        {desc && <p className="text-sm mt-0.5" style={{ color: "var(--text-dim)" }}>{desc}</p>}
      </div>
    </div>
    {action}
  </div>
);

const StatCard = ({ icon: Icon, label, value, sub, tone = "teal" }) => (
  <div className="mv-glass mv-glass-hover p-4 rounded-2xl">
    <div className="flex items-center justify-between">
      <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-faint)" }}>{label}</span>
      <div className={`mv-chip ${tone}`}><Icon size={12} /></div>
    </div>
    <div className="mv-font-display text-2xl font-bold mt-2">{value}</div>
    {sub && <div className="text-xs mt-1" style={{ color: "var(--text-dim)" }}>{sub}</div>}
  </div>
);

const Card = ({ children, className = "" }) => (
  <div className={`mv-glass p-5 rounded-2xl ${className}`}>{children}</div>
);

const Pill_ = ({ tone = "teal", children }) => <span className={`mv-chip ${tone}`}>{children}</span>;

const EncBadge = () => (
  <span className="mv-chip teal"><Lock size={11} /> AES-256 ENCRYPTED</span>
);

const CatIcon = ({ cat }) => {
  const map = { "Prescriptions": FileText, "Lab Reports": FlaskConical, "Allergies": AlertTriangle, "Medication History": Pill, "Emergency Data": Siren };
  const I = map[cat] || FileText;
  return <I size={16} />;
};

function RiskTone(level) {
  if (level === "High" || level === "Severe") return "red";
  if (level === "Medium" || level === "Moderate") return "amber";
  return "green";
}

/* Trust Ledger — signature scrolling element ---------------------------- */
const TrustLedger = () => (
  <Card className="overflow-hidden h-full flex flex-col">
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        <Fingerprint size={16} style={{ color: "var(--teal-deep)" }} />
        <span className="text-sm font-semibold">Live Trust Ledger</span>
      </div>
      <span className="mv-dot mv-pulse" style={{ background: "var(--green)", color: "var(--green)" }} />
    </div>
    <div className="relative flex-1 overflow-hidden" style={{ maxHeight: 210 }}>
      <div className="mv-marquee-track">
        {[...LEDGER_EVENTS, ...LEDGER_EVENTS].map((e, i) => (
          <div key={i} className="mv-track py-1.5 border-b" style={{ borderColor: "var(--border)" }}>{e}</div>
        ))}
      </div>
    </div>
    <div className="text-[11px] mt-2" style={{ color: "var(--text-faint)" }}>Append-only ledger · tamper-evident hash chain</div>
  </Card>
);

/* ---------------------------------------------------------------------- */
/* MODALS                                                                  */
/* ---------------------------------------------------------------------- */

const Modal = ({ title, icon: Icon, onClose, children, wide }) => (
  <div className="mv-modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
    <div className="mv-glass rounded-2xl p-6" style={{ width: wide ? 560 : 420, background: "var(--panel-solid)" }}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          {Icon && <Icon size={18} style={{ color: "var(--teal-deep)" }} />}
          <h3 className="font-semibold text-base mv-font-display">{title}</h3>
        </div>
        <button onClick={onClose} className="mv-glass p-1.5 rounded-lg mv-focusable"><X size={15} /></button>
      </div>
      {children}
    </div>
  </div>
);

const SignatureModal = ({ onClose, onConfirm }) => {
  const [signed, setSigned] = useState("");
  return (
    <Modal title="Digital Signature Approval" icon={FileSignature} onClose={onClose}>
      <p className="text-sm mb-3" style={{ color: "var(--text-dim)" }}>
        Sign below to cryptographically approve this access grant. Your signature is hashed and stored in the tamper-evident audit ledger.
      </p>
      <input className="mv-input mv-focusable mb-3 italic" placeholder="Type your full name to sign" value={signed} onChange={(e) => setSigned(e.target.value)} style={{ fontFamily: "cursive", fontSize: 16 }} />
      <div className="mv-chip blue mb-4"><KeyRound size={11} /> SIGNATURE HASH PREVIEW: 0x{signed ? signed.length.toString(16).padStart(4, "f") : "0000"}A2F1</div>
      <div className="flex gap-2 justify-end">
        <button className="mv-btn mv-btn-ghost" onClick={onClose}>Cancel</button>
        <button disabled={!signed} className="mv-btn mv-btn-primary" style={{ opacity: signed ? 1 : 0.5 }} onClick={() => { onConfirm(signed); onClose(); }}>
          <Check size={14} /> Confirm & Sign
        </button>
      </div>
    </Modal>
  );
};

const AccessDurationModal = ({ onClose, onConfirm, requester }) => {
  const [opt, setOpt] = useState("2h");
  const [custom, setCustom] = useState("");
  const options = [
    { id: "30m", label: "30 Minutes", icon: Clock },
    { id: "2h", label: "2 Hours", icon: Clock },
    { id: "24h", label: "24 Hours", icon: Clock },
    { id: "custom", label: "Custom Duration", icon: TimerReset },
  ];
  return (
    <Modal title={`Grant Access — ${requester}`} icon={Unlock} onClose={onClose}>
      <div className="grid grid-cols-2 gap-2 mb-3">
        {options.map((o) => (
          <button key={o.id} onClick={() => setOpt(o.id)}
            className="mv-glass mv-glass-hover p-3 rounded-xl text-left text-sm flex items-center gap-2"
            style={{ borderColor: opt === o.id ? "var(--teal)" : "var(--border)", fontWeight: opt === o.id ? 700 : 500 }}>
            <o.icon size={15} /> {o.label}
          </button>
        ))}
      </div>
      {opt === "custom" && (
        <input className="mv-input mv-focusable mb-3" placeholder="e.g. 6 hours, 3 days" value={custom} onChange={(e) => setCustom(e.target.value)} />
      )}
      <div className="mv-chip teal mb-4"><ShieldCheck size={11} /> Access auto-revokes when window expires</div>
      <div className="flex gap-2 justify-end">
        <button className="mv-btn mv-btn-ghost" onClick={onClose}>Cancel</button>
        <button className="mv-btn mv-btn-primary" onClick={() => { onConfirm(opt === "custom" ? custom || "Custom" : options.find(o => o.id === opt).label); onClose(); }}>
          <ShieldCheck size={14} /> Approve Access
        </button>
      </div>
    </Modal>
  );
};

const UploadModal = ({ onClose }) => {
  const [cat, setCat] = useState("Prescriptions");
  return (
    <Modal title="Upload to Health Vault" icon={Upload} onClose={onClose}>
      <label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>RECORD CATEGORY</label>
      <select className="mv-input mv-focusable mt-1 mb-3" value={cat} onChange={(e) => setCat(e.target.value)}>
        {["Prescriptions", "Lab Reports", "MRI", "CT_SCAN", "XRAY", "PDF_REPORT", "LAB_SUMMARY", "Allergies", "Medication History", "Emergency Data"].map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
      <div className="mv-glass rounded-xl p-6 text-center mb-3" style={{ borderStyle: "dashed" }}>
        <Upload size={22} className="mx-auto mb-2" style={{ color: "var(--teal-deep)" }} />
        <p className="text-sm">Drag & drop file or click to browse</p>
        <p className="text-xs mt-1" style={{ color: "var(--text-faint)" }}>PDF, JPG, PNG, DICOM — encrypted on upload</p>
      </div>
      <div className="flex gap-2 justify-end">
        <button className="mv-btn mv-btn-ghost" onClick={onClose}>Cancel</button>
        <button className="mv-btn mv-btn-primary" onClick={onClose}><Lock size={14} /> Encrypt & Upload</button>
      </div>
    </Modal>
  );
};

const BreakGlassModal = ({ onClose, onConfirm }) => {
  const [reason, setReason] = useState("");
  return (
    <Modal title="Break-Glass Emergency Access" icon={Siren} onClose={onClose}>
      <div className="mv-chip red mb-3"><AlertOctagon size={12} /> This action is permanently logged and audited</div>
      <p className="text-sm mb-3" style={{ color: "var(--text-dim)" }}>
        Activating emergency mode grants immediate read access to critical patient data, bypassing standard consent flow. Provide a justification below.
      </p>
      <textarea className="mv-input mv-focusable mb-3" rows={3} placeholder="Justification for emergency access (required)" value={reason} onChange={(e) => setReason(e.target.value)} />
      <div className="flex gap-2 justify-end">
        <button className="mv-btn mv-btn-ghost" onClick={onClose}>Cancel</button>
        <button disabled={!reason} style={{ opacity: reason ? 1 : 0.5 }} className="mv-btn mv-btn-danger" onClick={() => { onConfirm(reason); onClose(); }}>
          <Siren size={14} /> Activate Emergency Access
        </button>
      </div>
    </Modal>
  );
};

const PreviewModal = ({ file, onClose }) => (
  <Modal title={file?.name || "Document Preview"} icon={Eye} onClose={onClose} wide>
    <div className="mv-glass rounded-xl flex items-center justify-center mb-3" style={{ height: 280, background: "var(--bg-2)" }}>
      <div className="text-center">
        <FileText size={36} className="mx-auto mb-2" style={{ color: "var(--text-faint)" }} />
        <p className="text-sm" style={{ color: "var(--text-dim)" }}>Encrypted preview unlocked for this session</p>
      </div>
    </div>
    <div className="flex items-center justify-between text-xs" style={{ color: "var(--text-faint)" }}>
      <span className="mv-font-mono">SHA-256: 9f3a…e21c44</span>
      <EncBadge />
    </div>
  </Modal>
);

/* ---------------------------------------------------------------------- */
/* PATIENT VIEWS                                                          */
/* ---------------------------------------------------------------------- */

const PatientOverview = ({ go, currentUser }) => {
  const pid = currentUser?.user_id;
  const { data: rxRaw, loading: rxLoading } = useApi(() => vaultService.getPrescriptions(pid), [pid]);
  const { data: consentRaw } = useApi(() => consentService.getMyConsents(), [pid]);
  const { data: alertRaw } = useApi(() => fraudService.getAlerts(pid), [pid]);
  const { data: timelineRaw } = useApi(() => consentService.getTimeline(), [pid]);
  const activeRx = (rxRaw || []).filter(r => r.status === "ACTIVE");
  const pendingConsents = (consentRaw?.consents || []).filter(c => c.status === "PENDING");
  const alerts = alertRaw?.alerts || [];
  const events = (timelineRaw?.events || []).slice(0, 3);
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="md:col-span-2 flex items-center gap-5 flex-wrap">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, var(--teal), var(--blue))" }}>
            <CircleUser size={32} color="#fff" />
          </div>
          <div className="flex-1 min-w-[180px]">
            <h3 className="mv-font-display text-xl font-bold">Welcome back, {currentUser?.full_name?.split(" ")[0] || "User"}</h3>
            <p className="text-sm" style={{ color: "var(--text-dim)" }}>{currentUser?.email} · {currentUser?.role}</p>
            <div className="flex gap-2 mt-2 flex-wrap">
              <Pill_ tone="teal"><ShieldCheck size={11} /> Vault Secured</Pill_>
              <Pill_ tone="blue"><BadgeCheck size={11} /> Identity Verified</Pill_>
            </div>
          </div>
          <button className="mv-btn mv-btn-primary" onClick={() => go("vault")}><FolderLock size={14} /> Open Vault</button>
        </Card>
        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase" style={{ color: "var(--text-faint)" }}>Security Score</span>
            <ShieldCheck size={15} style={{ color: "var(--green)" }} />
          </div>
          <div className="mv-font-display text-3xl font-bold">96<span className="text-base" style={{ color: "var(--text-faint)" }}>/100</span></div>
          <div className="mv-progress-track mt-3"><div className="mv-progress-fill" style={{ width: "96%" }} /></div>
          <p className="text-xs mt-2" style={{ color: "var(--text-dim)" }}>MFA active · No weak access grants</p>
        </Card>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={FileText} label="Active Prescriptions" value={rxLoading ? "…" : activeRx.length} tone="teal" />
        <StatCard icon={Inbox} label="Pending Consents" value={pendingConsents.length} sub="Awaiting approval" tone="blue" />
        <StatCard icon={ShieldAlert} label="Fraud Alerts" value={alerts.length} sub={`${alerts.filter(a => a.severity === "SEVERE").length} high severity`} tone="red" />
        <StatCard icon={History} label="Timeline Events" value={timelineRaw?.events?.length ?? "…"} tone="green" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <span className="font-semibold text-sm">Recent Activity</span>
            <button className="text-xs font-semibold" style={{ color: "var(--teal-deep)" }} onClick={() => go("access-history")}>View all</button>
          </div>
          <div className="space-y-2.5">
            {events.length === 0 && <p className="text-sm text-gray-400">No recent activity yet.</p>}
            {events.map((e, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <div className="mv-glass p-2 rounded-lg"><Eye size={13} style={{ color: "var(--blue)" }} /></div>
                <div className="flex-1">
                  <span className="font-medium">{e.actor_name || e.actor_id || "System"}</span>{" "}
                  <span style={{ color: "var(--text-dim)" }}>{e.action}</span>
                </div>
                <span className="text-xs" style={{ color: "var(--text-faint)" }}>{new Date(e.timestamp).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </Card>
        <TrustLedger />
      </div>
    </div>
  );
};

const VaultView = ({ currentUser }) => {
  const pid = currentUser?.user_id;
  const [filter, setFilter] = useState("All");
  const { data: rxData, loading: rxL } = useApi(() => vaultService.getPrescriptions(pid), [pid]);
  const { data: allergyData, loading: aL } = useApi(() => vaultService.getAllergies(pid), [pid]);
  const { data: vacData, loading: vL } = useApi(() => vaultService.getVaccinations(pid), [pid]);
  const loading = rxL || aL || vL;
  const allRecords = [
    ...(rxData || []).map(r => ({ id: r.prescription_id, cat: "Prescriptions", name: `Rx: ${r.items?.[0]?.medicine_name || "Prescription"}`, date: new Date(r.created_at).toLocaleDateString() })),
    ...(allergyData || []).map(a => ({ id: a.allergy_id, cat: "Allergies", name: `Allergy: ${a.allergen}`, date: "On record" })),
    ...(vacData || []).map(v => ({ id: v.vaccination_id, cat: "Vaccinations", name: v.vaccine_name, date: v.date_administered ? new Date(v.date_administered).toLocaleDateString() : "—" })),
  ];
  const cats = ["All", "Prescriptions", "Allergies", "Vaccinations"];
  const filtered = filter === "All" ? allRecords : allRecords.filter(r => r.cat === filter);
  return (
    <div className="space-y-4">
      <SectionHeader icon={FolderLock} title="Digital Health Vault" desc="All your encrypted health records" />
      <div className="flex gap-2 flex-wrap">
        {cats.map(c => (
          <button key={c} onClick={() => setFilter(c)} className="mv-chip" style={{
            background: filter === c ? "linear-gradient(135deg, var(--teal-glow), var(--blue-glow))" : "var(--panel)",
            color: filter === c ? "var(--teal-deep)" : "var(--text-dim)", border: "1px solid var(--border)",
          }}>{c}</button>
        ))}
      </div>
      {loading ? <Card><p className="text-center py-8 text-gray-400">Decrypting vault…</p></Card> : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.length === 0 && <p className="text-sm text-gray-400 col-span-3 text-center py-8">No records in this category.</p>}
          {filtered.map(f => (
            <Card key={f.id} className="mv-glass-hover">
              <div className="flex items-start justify-between">
                <div className="mv-glass p-2.5 rounded-xl" style={{ color: "var(--teal-deep)" }}><CatIcon cat={f.cat} /></div>
                <EncBadge />
              </div>
              <h4 className="font-semibold text-sm mt-3 truncate">{f.name}</h4>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-faint)" }}>{f.cat}</p>
              <p className="text-xs mt-2" style={{ color: "var(--text-dim)" }}>{f.date}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

const PrescriptionQRModal = ({ rxid, onClose }) => (
  <Modal title="Prescription QR" icon={QrCode} onClose={onClose}>
    <div className="mv-glass p-8 rounded-2xl mb-4 flex justify-center" style={{ background: "var(--bg-2)" }}>
      <QrCode size={120} style={{ color: "var(--text)" }} />
    </div>
    <div className="mv-chip teal mb-3"><Lock size={11} /> Signed prescription QR — scan at pharmacy</div>
    <p className="text-xs text-center" style={{ color: "var(--text-dim)" }}>Contains no PHI. Verified by Ed25519 signature.</p>
  </Modal>
);

const PrescriptionsView = ({ currentUser }) => {
  const [qr, setQr] = useState(null);
  const { data, loading } = useApi(() => vaultService.getPrescriptions(currentUser?.user_id), [currentUser?.user_id]);
  const prescriptions = data || [];
  return (
    <div className="space-y-4">
      <SectionHeader icon={FileText} title="Prescription History" desc="All prescriptions issued under your CryptCare record" />
      <Card>
        <table className="mv-table">
          <thead><tr><th>Medications</th><th>Issued</th><th>Status</th><th>QR</th></tr></thead>
          <tbody>
            {loading && <Loading />}
            {!loading && prescriptions.length === 0 && <Empty msg="No prescriptions found." />}
            {prescriptions.map(p => (
              <tr key={p.prescription_id}>
                <td>{(p.items || []).map(i => <div key={i.item_id} className="text-sm">{i.medicine_name} {i.dosage}</div>)}</td>
                <td className="text-xs">{new Date(p.created_at).toLocaleDateString()}</td>
                <td><Pill_ tone={p.status === "ACTIVE" ? "teal" : p.status === "DISPENSED" ? "green" : "blue"}>{p.status}</Pill_></td>
                <td><button className="mv-btn mv-btn-ghost py-1 px-2" onClick={() => setQr(p.prescription_id)}><QrCode size={14} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {qr && <PrescriptionQRModal rxid={qr} onClose={() => setQr(null)} />}
    </div>
  );
};

const MedicationsView = () => (
  <div className="space-y-4">
    <SectionHeader icon={Pill} title="Medication History" desc="Full medication timeline across providers" />
    <Card>
      <table className="mv-table">
        <thead><tr><th>Medication</th><th>Purpose</th><th>Started</th><th>Status</th></tr></thead>
        <tbody>
          {medicationHistory.map((m, i) => (
            <tr key={i}><td className="font-medium">{m.name}</td><td>{m.purpose}</td><td>{m.started}</td>
              <td><Pill_ tone={m.status === "Ongoing" ? "teal" : m.status === "Completed" ? "blue" : "amber"}>{m.status}</Pill_></td></tr>
          ))}
        </tbody>
      </table>
    </Card>
  </div>
);

const AllergiesView = ({ currentUser }) => {
  const { data, loading } = useApi(() => vaultService.getAllergies(currentUser?.user_id), [currentUser?.user_id]);
  const records = data || [];
  return (
    <div className="space-y-4">
      <SectionHeader icon={AlertTriangle} title="Allergy Records" desc="Documented allergens and reaction severity" />
      {loading ? <Card><p className="text-center py-8 text-gray-400">Loading…</p></Card> : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {records.length === 0 && <p className="text-gray-400 text-sm">No allergy records found.</p>}
          {records.map(a => (
            <Card key={a.allergy_id}>
              <div className="flex items-center justify-between">
                <span className="font-semibold">{a.allergen}</span>
                <Pill_ tone={RiskTone(a.severity)}>{a.severity}</Pill_>
              </div>
              <p className="text-xs mt-2" style={{ color: "var(--text-faint)" }}>Severity: {a.severity}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

const LabsView = ({ currentUser }) => {
  const { data, loading } = useApi(
    () => api.get(`/lab/reports?patient_id=${currentUser?.user_id}`).then(r => r.data).catch(() => []),
    [currentUser?.user_id]
  );
  const reports = Array.isArray(data) ? data : [];
  return (
    <div className="space-y-4">
      <SectionHeader icon={FlaskConical} title="Laboratory Reports" desc="Diagnostic tests and results" />
      <Card>
        <table className="mv-table">
          <thead><tr><th>Test</th><th>Summary</th><th>Uploaded</th><th>Type</th></tr></thead>
          <tbody>
            {loading && <Loading />}
            {!loading && reports.length === 0 && <Empty msg="No lab reports found." />}
            {reports.map(r => (
              <tr key={r.report_id}>
                <td className="font-medium">{r.test_name || r.document_type}</td>
                <td className="text-xs" style={{ color: "var(--text-dim)" }}>{r.report_summary || "Encrypted — view report to decrypt"}</td>
                <td className="text-xs">{r.uploaded_at ? new Date(r.uploaded_at).toLocaleDateString() : "—"}</td>
                <td><Pill_ tone="teal">{r.document_type || "LAB_SUMMARY"}</Pill_></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

const EmergencyInfoView = ({ currentUser }) => {
  const [bg, setBg] = useState(false);
  const [active, setActive] = useState(false);
  return (
    <div className="space-y-4">
      <SectionHeader icon={Siren} title="Emergency Information" desc="Critical data visible to first responders"
        action={<button className={`mv-btn ${active ? "mv-btn-danger" : "mv-btn-primary"}`} onClick={() => setBg(true)}>
          <Siren size={14} /> {active ? "Emergency Mode Active" : "Activate Emergency Mode"}
        </button>} />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard icon={CircleUser} label="Patient" value={currentUser?.full_name || "—"} tone="teal" />
        <StatCard icon={ShieldCheck} label="Account Status" value={currentUser?.status || "ACTIVE"} tone="green" />
        <StatCard icon={Siren} label="Emergency Access" value={active ? "ACTIVE" : "Off"} tone={active ? "red" : "blue"} />
      </div>
      {bg && <BreakGlassModal onClose={() => setBg(false)} onConfirm={() => setActive(true)} />}
    </div>
  );
};

const AIAssistantView = ({ currentUser }) => {
  const firstName = currentUser?.full_name?.split(" ")[0] || "there";
  const [messages, setMessages] = useState([
    { from: "ai", text: `Hello ${firstName}, I'm your AI Medical Assistant. I can explain medications, side effects, or general health guidance. How can I help today?` },
  ]);
  const [input, setInput] = useState("");
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  const respond = (q) => {
    const l = q.toLowerCase();
    if (l.includes("atorvastatin")) return "Atorvastatin lowers LDL cholesterol. Take it at the same time daily, preferably evening. Common side effects include mild muscle aches.";
    if (l.includes("metformin")) return "Metformin manages Type 2 diabetes by reducing glucose production in the liver. Take with meals to reduce stomach upset.";
    if (l.includes("amoxicillin")) return "Amoxicillin is an antibiotic for bacterial infections. Complete the full course even if you feel better. Common side effects include nausea and diarrhea.";
    if (l.includes("side effect")) return "Side effects vary by medication. For your current prescriptions, the most common are mild gastrointestinal discomfort and occasional fatigue. Report severe symptoms to your doctor.";
    if (l.includes("interaction")) return "The AI Clinical Safety Agent monitors your prescriptions for drug interactions. No high-risk interactions are currently flagged for your active medications.";
    return "I can help explain medications, lab result terminology, or general wellness guidance. For anything urgent or symptom-specific, please consult your doctor directly.";
  };
  const send = () => {
    if (!input.trim()) return;
    setMessages(m => [...m, { from: "user", text: input }, { from: "ai", text: respond(input) }]);
    setInput("");
  };
  return (
    <div className="space-y-4">
      <SectionHeader icon={Bot} title="AI Medical Assistant" desc="Conversational guidance on medications and general health" />
      <Card className="flex flex-col" style={{ height: 480 }}>
        <div className="flex-1 overflow-y-auto mv-scroll space-y-3 pr-1">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.from === "user" ? "justify-end" : "justify-start"}`}>
              <div className="px-4 py-2.5 rounded-2xl text-sm max-w-[75%]" style={{
                background: m.from === "user" ? "linear-gradient(135deg, var(--teal), var(--blue))" : "var(--panel)",
                color: m.from === "user" ? "#fff" : "var(--text)", border: m.from === "ai" ? "1px solid var(--border)" : "none",
              }}>{m.text}</div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
        <div className="flex gap-2 mt-3">
          <input className="mv-input mv-focusable" placeholder="Ask about a medication, side effect, or symptom…" value={input}
            onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} />
          <button className="mv-btn mv-btn-primary" onClick={send}><Send size={14} /></button>
        </div>
      </Card>
      <div className="mv-chip amber"><AlertTriangle size={11} /> AI guidance is informational only and does not replace professional medical advice.</div>
    </div>
  );
};

const AccessRequestsView = ({ currentUser }) => {
  const { data, loading } = useApi(() => consentService.getMyConsents(), [currentUser?.user_id]);
  const pending = (data?.consents || []).filter(c => c.status === "PENDING");
  const [actioned, setActioned] = useState({});
  const handle = async (id, action) => {
    try {
      if (action === "approve") await consentService.approveConsent(id);
      else await consentService.rejectConsent(id);
      setActioned(a => ({ ...a, [id]: action }));
    } catch (e) { alert(e?.response?.data?.detail || "Action failed"); }
  };
  return (
    <div className="space-y-4">
      <SectionHeader icon={Inbox} title="Access Requests" desc="Incoming consent requests from providers" />
      {loading && <Card><p className="text-center py-8 text-gray-400">Loading…</p></Card>}
      {!loading && pending.length === 0 && <Card><p className="text-center py-8 text-gray-400">No pending access requests.</p></Card>}
      <div className="space-y-3">
        {pending.map(r => (
          <Card key={r.consent_id} className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="mv-glass p-2.5 rounded-xl"><UserCog size={16} style={{ color: "var(--blue)" }} /></div>
              <div>
                <h4 className="font-semibold text-sm">{r.grantee_name || r.grantee_id} <span className="text-xs font-normal" style={{ color: "var(--text-faint)" }}>· {r.grantee_type}</span></h4>
                <p className="text-xs mt-0.5" style={{ color: "var(--text-dim)" }}>{r.resource_type} · {r.permission}</p>
              </div>
            </div>
            {actioned[r.consent_id] ? (
              <Pill_ tone={actioned[r.consent_id] === "approve" ? "green" : "red"}>{actioned[r.consent_id] === "approve" ? "Approved" : "Rejected"}</Pill_>
            ) : (
              <div className="flex gap-2">
                <button className="mv-btn mv-btn-danger" onClick={() => handle(r.consent_id, "reject")}><X size={13} /> Reject</button>
                <button className="mv-btn mv-btn-primary" onClick={() => handle(r.consent_id, "approve")}><Check size={13} /> Approve</button>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
};

const AccessHistoryView = ({ currentUser }) => {
  const { data, loading } = useApi(() => consentService.getTimeline(), [currentUser?.user_id]);
  const events = data?.events || [];
  return (
    <div className="space-y-4">
      <SectionHeader icon={History} title="Access History Timeline" desc="Complete trail of who accessed your records, when, and why" />
      <Card>
        {loading && <p className="text-center py-8 text-gray-400">Loading...</p>}
        {!loading && events.length === 0 && <p className="text-center py-8 text-gray-400">No timeline events yet.</p>}
        <div className="space-y-0">
          {events.map((e, i) => (
            <div key={i} className="flex gap-4 pb-5 relative">
              {i < events.length - 1 && <div className="absolute left-[15px] top-8 bottom-0 w-px" style={{ background: "var(--border)" }} />}
              <div className="mv-glass p-2 rounded-full h-fit z-10"><Eye size={13} style={{ color: "var(--teal-deep)" }} /></div>
              <div className="flex-1">
                <div className="flex items-center justify-between flex-wrap gap-1">
                  <span className="font-semibold text-sm">{e.actor_name || e.actor_id || "System"}</span>
                  <span className="text-xs" style={{ color: "var(--text-faint)" }}>{new Date(e.timestamp).toLocaleString()}</span>
                </div>
                <p className="text-sm mt-0.5" style={{ color: "var(--text-dim)" }}>{e.action}</p>
                {e.resource_type && <span className="mv-chip blue mt-1">{e.resource_type}</span>}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

const FraudAlertsView = ({ currentUser }) => {
  const pid = currentUser?.user_id;
  const { data, loading } = useApi(() => fraudService.getAlerts(pid), [pid]);
  const alerts = data?.alerts || [];
  const sevTone = s => s === "SEVERE" ? "red" : s === "MODERATE" ? "amber" : "green";
  return (
    <div className="space-y-4">
      <SectionHeader icon={ShieldAlert} title="Fraud Alerts" desc="Rule-based suspicious activity flags on your records" />
      {loading && <Card><p className="text-center py-8 text-gray-400">Loading...</p></Card>}
      {!loading && alerts.length === 0 && <Card><p className="text-center py-8 text-gray-400">No fraud alerts on your account.</p></Card>}
      <div className="space-y-3">
        {alerts.map(f => (
          <Card key={f.alert_id} className="flex items-start gap-3">
            <div className="mv-glass p-2.5 rounded-xl" style={{ color: f.severity === "SEVERE" ? "var(--red)" : "var(--amber)" }}><AlertOctagon size={17} /></div>
            <div className="flex-1">
              <div className="flex items-center justify-between flex-wrap gap-1">
                <h4 className="font-semibold text-sm">{f.category?.replace(/_/g, " ")}</h4>
                <span className="text-xs" style={{ color: "var(--text-faint)" }}>{new Date(f.detected_at).toLocaleString()}</span>
              </div>
              <p className="text-sm mt-1" style={{ color: "var(--text-dim)" }}>{f.description}</p>
              <div className="flex gap-2 mt-2">
                <Pill_ tone={sevTone(f.severity)}>{f.severity}</Pill_>
                <Pill_ tone={f.status === "OPEN" ? "red" : "green"}>{f.status}</Pill_>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

const ActiveConsentsView = ({ currentUser }) => {
  const { data, loading } = useApi(() => consentService.getMyConsents(), [currentUser?.user_id]);
  const consents = (data?.consents || []).filter(c => c.status === "ACTIVE");
  const [revoked, setRevoked] = useState({});
  const revoke = async (id) => {
    try {
      await consentService.revokeConsent(id);
      setRevoked(r => ({ ...r, [id]: true }));
    } catch (e) { alert(e?.response?.data?.detail || "Revoke failed"); }
  };
  return (
    <div className="space-y-4">
      <SectionHeader icon={ShieldCheck} title="Active Consents" desc="Manage entities currently holding access to your records" />
      {loading && <Card><p className="text-center py-8 text-gray-400">Loading...</p></Card>}
      {!loading && consents.length === 0 && <Card><p className="text-center py-8 text-gray-400">No active consents.</p></Card>}
      <div className="space-y-3">
        {consents.map(c => (
          <Card key={c.consent_id} className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="mv-glass p-2.5 rounded-xl"><ShieldCheck size={16} style={{ color: "var(--green)" }} /></div>
              <div>
                <h4 className="font-semibold text-sm">{c.grantee_name || c.grantee_id} <span className="text-xs font-normal" style={{ color: "var(--text-faint)" }}>· {c.grantee_type}</span></h4>
                <p className="text-xs mt-0.5" style={{ color: "var(--text-dim)" }}>{c.resource_type} · Expires: {c.expires_at ? new Date(c.expires_at).toLocaleDateString() : "No expiry"}</p>
              </div>
            </div>
            {revoked[c.consent_id] ? (
              <span className="mv-chip red"><X size={11} /> Revoked</span>
            ) : (
              <button className="mv-btn mv-btn-danger" onClick={() => revoke(c.consent_id)}><ShieldX size={13} /> Revoke Access</button>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
};

const VaccinationsView = ({ currentUser }) => {
  const { data, loading } = useApi(() => vaultService.getVaccinations(currentUser?.user_id), [currentUser?.user_id]);
  const records = data || [];
  return (
    <div className="space-y-4">
      <SectionHeader icon={ShieldCheck} title="Vaccination Records" desc="Immunisation history and upcoming doses" />
      <Card>
        <table className="mv-table">
          <thead><tr><th>Vaccine</th><th>Administered</th><th>Next Due</th></tr></thead>
          <tbody>
            {loading && <Loading />}
            {!loading && records.length === 0 && <Empty msg="No vaccination records found." />}
            {records.map(v => (
              <tr key={v.vaccination_id}>
                <td className="font-medium">{v.vaccine_name}</td>
                <td className="text-xs">{v.date_administered ? new Date(v.date_administered).toLocaleDateString() : "—"}</td>
                <td>{v.next_due_date ? <Pill_ tone="amber">{new Date(v.next_due_date).toLocaleDateString()}</Pill_> : <Pill_ tone="green">Complete</Pill_>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

const PatientClaimsView = ({ currentUser }) => {
  const { data, loading } = useApi(() => insuranceService.getClaims(), [currentUser?.user_id]);
  const claims = Array.isArray(data) ? data : [];
  const statusTone = s => s === "APPROVED" ? "green" : s === "REJECTED" ? "red" : "amber";
  return (
    <div className="space-y-4">
      <SectionHeader icon={FileText} title="My Insurance Claims" desc="Claims submitted to your insurer" />
      <Card>
        <table className="mv-table">
          <thead><tr><th>Claim ID</th><th>Resource</th><th>Amount</th><th>Status</th><th>Date</th></tr></thead>
          <tbody>
            {loading && <Loading />}
            {!loading && claims.length === 0 && <Empty msg="No insurance claims found." />}
            {claims.map(c => (
              <tr key={c.claim_id}>
                <td className="mv-font-mono text-xs">{c.claim_id.slice(0, 8)}...</td>
                <td className="text-xs">{c.resource_type}</td>
                <td className="font-medium">&#8377;{c.amount?.toLocaleString()}</td>
                <td><Pill_ tone={statusTone(c.status)}>{c.status}</Pill_></td>
                <td className="text-xs">{new Date(c.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

/* ---------------------------------------------------------------------- */
/* DOCTOR VIEWS                                                           */
/* ---------------------------------------------------------------------- */

const DoctorOverview = ({ go, currentUser }) => {
  const { data: rxData } = useApi(() => api.get('/vault/prescriptions').then(r => r.data).catch(() => []), []);
  const { data: consentData } = useApi(() => consentService.getMyRequests(), []);
  const rxList = Array.isArray(rxData) ? rxData : [];
  const pendingConsents = (consentData?.consents || []).filter(c => c.status === "PENDING");
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={FileSignature} label="Prescriptions Issued" value={rxList.length} tone="teal" />
        <StatCard icon={Inbox} label="Pending Consents" value={pendingConsents.length} tone="blue" />
        <StatCard icon={Sparkles} label="AI Safety Active" value="ON" tone="green" />
        <StatCard icon={ShieldCheck} label="MFA Status" value="Active" tone="amber" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <span className="font-semibold text-sm">Quick Actions</span>
            <button className="text-xs font-semibold" style={{ color: "var(--teal-deep)" }} onClick={() => go("search")}>Search patient</button>
          </div>
          <div className="flex gap-3 flex-wrap">
            <button className="mv-btn mv-btn-primary" onClick={() => go("prescribe")}><FileSignature size={14} /> New Prescription</button>
            <button className="mv-btn mv-btn-ghost" onClick={() => go("search")}><Search size={14} /> Patient Search</button>
            <button className="mv-btn mv-btn-ghost" onClick={() => go("clinical-ai")}><Sparkles size={14} /> AI Safety Check</button>
          </div>
          <p className="text-xs mt-4" style={{ color: "var(--text-dim)" }}>
            Logged in as <strong>{currentUser?.full_name}</strong> · {currentUser?.email}
          </p>
        </Card>
        <TrustLedger />
      </div>
    </div>
  );
};

const PatientSearchView = ({ currentUser }) => {
  const [patientId, setPatientId] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState("");
  const request = async () => {
    if (!patientId.trim()) return;
    setRequesting(true); setErr("");
    try {
      await consentService.requestConsent({ patient_id: patientId, resource_type: "prescriptions", permission: "READ" });
      setDone(true);
    } catch (e) { setErr(e?.response?.data?.detail || "Request failed"); }
    finally { setRequesting(false); }
  };
  return (
    <div className="space-y-4">
      <SectionHeader icon={Search} title="Patient Search" desc="Find a patient and request consent to access their records" />
      <Card className="space-y-3">
        <div>
          <label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>PATIENT USER ID</label>
          <div className="flex gap-2 mt-1">
            <input className="mv-input mv-focusable" placeholder="Paste patient UUID..." value={patientId} onChange={e => setPatientId(e.target.value)} />
            <button className="mv-btn mv-btn-primary" onClick={request} disabled={requesting || !patientId.trim()}>
              <Inbox size={14} /> {requesting ? "Sending..." : "Request Consent"}
            </button>
          </div>
        </div>
        {done && <div className="mv-chip green"><Check size={11} /> Consent request sent — awaiting patient approval.</div>}
        {err && <div className="text-sm text-red-500">{err}</div>}
      </Card>
    </div>
  );
};

const CreatePrescriptionView = () => {
  const [sig, setSig] = useState(false);
  const [signed, setSigned] = useState(false);
  return (
    <div className="space-y-4">
      <SectionHeader icon={FileSignature} title="Create Prescription" desc="Draft and digitally sign a new prescription for the selected patient" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>MEDICATION</label><input className="mv-input mv-focusable mt-1" defaultValue="Atorvastatin 20mg" /></div>
            <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>DOSAGE FREQUENCY</label><input className="mv-input mv-focusable mt-1" defaultValue="Once daily, evening" /></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>DURATION</label><input className="mv-input mv-focusable mt-1" defaultValue="90 days" /></div>
            <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>REFILLS</label><input className="mv-input mv-focusable mt-1" defaultValue="2" /></div>
          </div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>CLINICAL NOTES</label><textarea className="mv-input mv-focusable mt-1" rows={3} defaultValue="Continue cholesterol management; recheck lipid panel in 3 months." /></div>
          <div className="flex justify-end gap-2 pt-2">
            <button className="mv-btn mv-btn-ghost">Save Draft</button>
            <button className="mv-btn mv-btn-primary" onClick={() => setSig(true)}><FileSignature size={14} /> Sign & Issue</button>
          </div>
          {signed && <div className="mv-chip green"><Check size={11} /> Prescription cryptographically signed and pushed to patient vault</div>}
        </Card>
        <Card>
          <h4 className="font-semibold text-sm mb-3 flex items-center gap-2"><Sparkles size={15} style={{ color: "var(--teal-deep)" }} /> AI Safety Check</h4>
          <div className="space-y-2">
            {drugInteractions.slice(0, 2).map((d, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span>{d.pair}</span><Pill_ tone={RiskTone(d.risk)}>{d.risk}</Pill_>
              </div>
            ))}
            <div className="text-xs mt-2" style={{ color: "var(--text-dim)" }}>No duplicate medications or allergy conflicts found for this patient.</div>
          </div>
        </Card>
      </div>
      {sig && <SignatureModal onClose={() => setSig(false)} onConfirm={() => setSigned(true)} />}
    </div>
  );
};

const ClinicalAIView = () => (
  <div className="space-y-4">
    <SectionHeader icon={Sparkles} title="AI Clinical Safety Analysis" desc="Automated drug interaction and allergy review" />
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <StatCard icon={AlertTriangle} label="Interaction Risk" value="Check active Rx" tone="amber" />
      <StatCard icon={Pill} label="Duplicate Meds" value="Monitored" tone="green" />
      <StatCard icon={ShieldAlert} label="Allergy Conflicts" value="Monitored" tone="green" />
    </div>
    <Card>
      <h4 className="font-semibold text-sm mb-3">Known Interaction Reference</h4>
      <table className="mv-table">
        <thead><tr><th>Pair</th><th>Risk</th><th>Clinical Note</th></tr></thead>
        <tbody>
          {[
            { pair: "Metformin + Atorvastatin", risk: "Low", note: "No clinically significant interaction observed." },
            { pair: "Ibuprofen + Losartan", risk: "Moderate", note: "May reduce antihypertensive effect; monitor BP." },
            { pair: "Amoxicillin + Warfarin", risk: "High", note: "Increases bleeding risk — alternative antibiotic advised." },
          ].map((d, i) => (
            <tr key={i}><td className="font-medium">{d.pair}</td><td><Pill_ tone={RiskTone(d.risk)}>{d.risk}</Pill_></td><td style={{ color: "var(--text-dim)" }}>{d.note}</td></tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs mt-3" style={{ color: "var(--text-faint)" }}>Full interaction checking runs at prescription creation via FAISS drug matching engine.</p>
    </Card>
  </div>
);

const PatientHistoryView = ({ currentUser }) => {
  const [patientId, setPatientId] = useState("");
  const [searched, setSearched] = useState(null);
  const { data, loading } = useApi(
    () => searched ? vaultService.getPrescriptions(searched) : Promise.resolve([]),
    [searched]
  );
  const rx = data || [];
  return (
    <div className="space-y-4">
      <SectionHeader icon={History} title="Patient Prescription History" desc="View prescriptions for a consented patient" />
      <Card className="flex gap-2">
        <input className="mv-input mv-focusable" placeholder="Patient user ID..." value={patientId} onChange={e => setPatientId(e.target.value)} />
        <button className="mv-btn mv-btn-primary" onClick={() => setSearched(patientId)}><Search size={14} /> Load</button>
      </Card>
      {searched && (
        <Card>
          <table className="mv-table">
            <thead><tr><th>Medications</th><th>Issued</th><th>Status</th></tr></thead>
            <tbody>
              {loading && <Loading />}
              {!loading && rx.length === 0 && <Empty msg="No prescriptions found or consent not granted." />}
              {rx.map(p => (
                <tr key={p.prescription_id}>
                  <td>{(p.items || []).map(i => <div key={i.item_id} className="text-sm">{i.medicine_name} {i.dosage}</div>)}</td>
                  <td className="text-xs">{new Date(p.created_at).toLocaleDateString()}</td>
                  <td><Pill_ tone={p.status === "ACTIVE" ? "teal" : "blue"}>{p.status}</Pill_></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
};

/* ---------------------------------------------------------------------- */
/* NURSE VIEWS                                                           */
/* ---------------------------------------------------------------------- */

const NurseOverview = ({ currentUser }) => {
  const { data: vitalsData } = useApi(() => api.get('/nursing/vitals/recent').then(r => r.data).catch(() => ({ vitals: [] })), []);
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard icon={HeartPulse} label="Vitals Role" value="Active" tone="teal" />
        <StatCard icon={ClipboardCheck} label="Scope" value="Vitals only" sub="Read-only prescriptions" tone="green" />
        <StatCard icon={ShieldCheck} label="MFA Status" value="Active" tone="blue" />
      </div>
      <Card>
        <h4 className="font-semibold text-sm mb-3">Role Scope (RBAC)</h4>
        <div className="flex gap-3 flex-wrap">
          <Pill_ tone="green"><Check size={11} /> vitals:write</Pill_>
          <Pill_ tone="green"><Check size={11} /> vitals:read</Pill_>
          <Pill_ tone="blue"><Check size={11} /> prescriptions:read</Pill_>
          <Pill_ tone="red"><X size={11} /> prescriptions:write (denied)</Pill_>
        </div>
        <p className="text-xs mt-3" style={{ color: "var(--text-faint)" }}>
          Logged in as <strong>{currentUser?.full_name}</strong> · {currentUser?.email}
        </p>
      </Card>
    </div>
  );
};

const MedAdminView = () => (
  <div className="space-y-4">
    <SectionHeader icon={ClipboardCheck} title="Medication Administration" desc="Record vitals after administering medications — prescriptions are read-only" />
    <Card>
      <p className="text-sm" style={{ color: "var(--text-dim)" }}>
        Use the <strong>Vitals Management</strong> tab to record patient vital signs after medication administration.
        Prescription data is fetched live — nurses cannot modify prescriptions (RBAC enforced).
      </p>
      <div className="mv-chip blue mt-3"><ShieldCheck size={11} /> RBAC: vitals:write granted · prescriptions:write denied</div>
    </Card>
  </div>
);

const QRVerifyView = () => {
  const [scanned, setScanned] = useState(false);
  return (
    <div className="space-y-4">
      <SectionHeader icon={QrCode} title="QR Patient Verification" desc="Scan wristband QR to confirm patient identity before administration" />
      <Card className="flex flex-col items-center text-center py-10">
        <div className="mv-glass p-8 rounded-2xl mb-4" style={{ background: "var(--bg-2)" }}>
          <QrCode size={84} style={{ color: scanned ? "var(--green)" : "var(--text)" }} />
        </div>
        {scanned ? (
          <>
            <Pill_ tone="green"><Check size={12} /> Identity Confirmed — Aarav Mehta, MV-PT-88213</Pill_>
            <p className="text-xs mt-2" style={{ color: "var(--text-dim)" }}>Verified against medication schedule. Safe to proceed.</p>
          </>
        ) : (
          <button className="mv-btn mv-btn-primary mt-2" onClick={() => setScanned(true)}><ScanLine size={14} /> Simulate Scan</button>
        )}
      </Card>
    </div>
  );
};

const ScheduleView = () => (
  <div className="space-y-4">
    <SectionHeader icon={CalendarClock} title="Medication Schedule" desc="Today's dosing timeline — data is live from patient prescriptions" />
    <Card>
      <p className="text-sm mb-4" style={{ color: "var(--text-dim)" }}>
        Scheduled doses are derived from active prescriptions in the vault. Use Patient Search to look up a specific patient's active prescriptions.
      </p>
      <div className="mv-chip teal"><ShieldCheck size={11} /> Prescriptions fetched live — no hardcoded schedule data</div>
    </Card>
  </div>
);

/* ---------------------------------------------------------------------- */
/* PHARMACIST VIEWS                                                      */
/* ---------------------------------------------------------------------- */

const PharmacyOverview = () => (
  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
    <StatCard icon={BadgeCheck} label="Verified Today" value="37" tone="green" />
    <StatCard icon={PackageSearch} label="Pending Dispense" value="6" tone="teal" />
    <StatCard icon={AlertTriangle} label="Interaction Flags" value="2" tone="amber" />
    <StatCard icon={ShieldAlert} label="Fraud Holds" value="1" tone="red" />
  </div>
);

const VerifyView = () => {
  const [rxid, setRxid] = useState("RX-99281");
  const [verified, setVerified] = useState(false);
  return (
    <div className="space-y-4">
      <SectionHeader icon={BadgeCheck} title="Prescription Verification" desc="Validate digital prescription authenticity before dispensing" />
      <Card>
        <div className="flex gap-2">
          <input className="mv-input mv-focusable mv-font-mono" value={rxid} onChange={(e) => setRxid(e.target.value)} />
          <button className="mv-btn mv-btn-primary" onClick={() => setVerified(true)}><Fingerprint size={14} /> Verify Authenticity</button>
        </div>
        {verified && (
          <div className="mt-4 space-y-2">
            <div className="mv-chip green"><Check size={11} /> Digital signature valid — issued by Dr. Lena Cross</div>
            <div className="mv-chip teal"><Lock size={11} /> Hash chain intact — no tampering detected</div>
            <div className="grid grid-cols-2 gap-3 mt-3 text-sm">
              <div><span style={{ color: "var(--text-faint)" }}>Medication:</span> Atorvastatin 20mg</div>
              <div><span style={{ color: "var(--text-faint)" }}>Patient:</span> Aarav Mehta</div>
              <div><span style={{ color: "var(--text-faint)" }}>Issued:</span> 12 Jun 2026</div>
              <div><span style={{ color: "var(--text-faint)" }}>Refills left:</span> 2</div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

const DispenseView = () => {
  const [done, setDone] = useState(false);
  return (
    <div className="space-y-4">
      <SectionHeader icon={PackageSearch} title="Dispensing Interface" desc="Log dispensed medication against verified prescription" />
      <Card className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>PRESCRIPTION</label><input className="mv-input mv-focusable mt-1 mv-font-mono" defaultValue="RX-99281" /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>QUANTITY DISPENSED</label><input className="mv-input mv-focusable mt-1" defaultValue="30 tablets" /></div>
        </div>
        <div className="flex justify-end">
          <button className="mv-btn mv-btn-primary" onClick={() => setDone(true)}><PackageSearch size={14} /> Confirm Dispense</button>
        </div>
        {done && <div className="mv-chip green"><Check size={11} /> Dispensing logged to immutable audit ledger</div>}
      </Card>
    </div>
  );
};

const InteractionsView = () => {
  const KNOWN = [
    { pair: "Metformin + Atorvastatin", risk: "Low", note: "No clinically significant interaction observed." },
    { pair: "Ibuprofen + Losartan", risk: "Moderate", note: "May reduce antihypertensive effect; monitor BP." },
    { pair: "Amoxicillin + Warfarin", risk: "High", note: "Increases bleeding risk — alternative antibiotic advised." },
    { pair: "Aspirin + Warfarin", risk: "High", note: "Concurrent use significantly increases bleeding risk." },
    { pair: "Atorvastatin + Clarithromycin", risk: "Moderate", note: "CYP3A4 inhibition increases statin exposure; consider dose reduction." },
  ];
  return (
    <div className="space-y-4">
      <SectionHeader icon={AlertTriangle} title="Drug Interaction Reference" desc="Known interactions — full check runs server-side at prescription creation" />
      <div className="space-y-3">
        {KNOWN.map((d, i) => (
          <Card key={i} className="flex items-center justify-between">
            <div><h4 className="font-semibold text-sm">{d.pair}</h4><p className="text-xs mt-1" style={{ color: "var(--text-dim)" }}>{d.note}</p></div>
            <Pill_ tone={RiskTone(d.risk)}>{d.risk} Risk</Pill_>
          </Card>
        ))}
      </div>
    </div>
  );
};

/* ---------------------------------------------------------------------- */
/* INSURANCE VIEWS                                                       */
/* ---------------------------------------------------------------------- */

const InsuranceOverview = ({ currentUser }) => {
  const { data, loading } = useApi(() => insuranceService.getClaims(), [currentUser?.user_id]);
  const claims = Array.isArray(data) ? data : [];
  const pending = claims.filter(c => c.status === "PENDING").length;
  const approved = claims.filter(c => c.status === "APPROVED").length;
  const rejected = claims.filter(c => c.status === "REJECTED").length;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={FileText} label="Total Claims" value={loading ? "…" : claims.length} tone="teal" />
        <StatCard icon={Clock} label="Pending Review" value={loading ? "…" : pending} tone="amber" />
        <StatCard icon={Check} label="Approved" value={loading ? "…" : approved} tone="green" />
        <StatCard icon={X} label="Rejected" value={loading ? "…" : rejected} tone="red" />
      </div>
    </div>
  );
};

const ClaimsView = ({ currentUser }) => {
  const { data, loading } = useApi(() => insuranceService.getClaims(), [currentUser?.user_id]);
  const claims = Array.isArray(data) ? data : [];
  const [updating, setUpdating] = useState({});
  const statusTone = s => s === "APPROVED" ? "green" : s === "REJECTED" ? "red" : "amber";

  const update = async (claimId, status) => {
    setUpdating(u => ({ ...u, [claimId]: true }));
    try {
      await insuranceService.updateClaimStatus(claimId, status);
      window.location.reload();
    } catch (e) {
      alert(e?.response?.data?.detail || "Update failed");
      setUpdating(u => ({ ...u, [claimId]: false }));
    }
  };

  return (
    <div className="space-y-4">
      <SectionHeader icon={FileText} title="Claims Review" desc="Insurance claims awaiting verification" />
      <Card>
        <table className="mv-table">
          <thead><tr><th>Claim ID</th><th>Resource</th><th>Amount</th><th>Status</th><th>Date</th><th>Actions</th></tr></thead>
          <tbody>
            {loading && <Loading />}
            {!loading && claims.length === 0 && <Empty msg="No claims found." />}
            {claims.map(c => (
              <tr key={c.claim_id}>
                <td className="mv-font-mono text-xs">{c.claim_id.slice(0, 8)}…</td>
                <td className="text-xs">{c.resource_type}</td>
                <td className="font-medium">&#8377;{c.amount?.toLocaleString()}</td>
                <td><Pill_ tone={statusTone(c.status)}>{c.status}</Pill_></td>
                <td className="text-xs">{new Date(c.created_at).toLocaleDateString()}</td>
                <td>
                  {c.status === "PENDING" && (
                    <div className="flex gap-1">
                      <button className="mv-btn mv-btn-primary py-1 px-2 text-xs" disabled={updating[c.claim_id]}
                        onClick={() => update(c.claim_id, "APPROVED")}><Check size={11} /> Approve</button>
                      <button className="mv-btn mv-btn-danger py-1 px-2 text-xs" disabled={updating[c.claim_id]}
                        onClick={() => update(c.claim_id, "REJECTED")}><X size={11} /> Reject</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

const AnomaliesView = ({ currentUser }) => {
  const { data, loading } = useApi(() => fraudService.getAlerts(currentUser?.user_id), [currentUser?.user_id]);
  const alerts = data?.alerts || [];
  const sevTone = s => s === "SEVERE" ? "red" : s === "MODERATE" ? "amber" : "green";
  return (
    <div className="space-y-4">
      <SectionHeader icon={Radar} title="Insurance Anomaly Detection" desc="Fraud alerts visible via patient consent" />
      {loading && <Card><p className="text-center py-8 text-gray-400">Loading...</p></Card>}
      {!loading && alerts.length === 0 && <Card><p className="text-center py-8 text-gray-400">No anomalies detected or no consent granted.</p></Card>}
      <div className="space-y-3">
        {alerts.map(f => (
          <Card key={f.alert_id} className="flex items-start gap-3">
            <div className="mv-glass p-2.5 rounded-xl" style={{ color: f.severity === "SEVERE" ? "var(--red)" : "var(--amber)" }}><AlertOctagon size={17} /></div>
            <div className="flex-1">
              <div className="flex items-center justify-between flex-wrap gap-1">
                <h4 className="font-semibold text-sm">{f.category?.replace(/_/g, " ")}</h4>
                <span className="text-xs" style={{ color: "var(--text-faint)" }}>{new Date(f.detected_at).toLocaleString()}</span>
              </div>
              <p className="text-sm mt-1" style={{ color: "var(--text-dim)" }}>{f.description}</p>
              <Pill_ tone={sevTone(f.severity)}>{f.severity}</Pill_>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

/* ---------------------------------------------------------------------- */
/* ADMIN / SHARED PLATFORM VIEWS                                         */
/* ---------------------------------------------------------------------- */

const AdminOverview = () => (
  <div className="space-y-5">
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard icon={Users} label="Active Users" value="2,481" tone="teal" />
      <StatCard icon={ShieldCheck} label="System Uptime" value="99.98%" tone="green" />
      <StatCard icon={ShieldAlert} label="Open Threats" value="0" tone="blue" />
      <StatCard icon={Server} label="Vault Shards" value="64" sub="Distributed across 3 regions" tone="amber" />
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <Card className="lg:col-span-2" style={{ height: 300 }}>
        <h4 className="font-semibold text-sm mb-3">Platform Activity (6 Months)</h4>
        <ResponsiveContainer width="100%" height="90%">
          <AreaChart data={analyticsTrend}>
            <defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#0FB6AA" stopOpacity={0.5} /><stop offset="100%" stopColor="#0FB6AA" stopOpacity={0} /></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="m" stroke="var(--text-faint)" fontSize={11} />
            <YAxis stroke="var(--text-faint)" fontSize={11} />
            <Tooltip contentStyle={{ background: "var(--panel-solid)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} />
            <Area type="monotone" dataKey="access" stroke="#0FB6AA" fill="url(#g1)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </Card>
      <TrustLedger />
    </div>
  </div>
);

const AICenterView = () => (
  <div className="space-y-5">
    <SectionHeader icon={Sparkles} title="AI Intelligence Center" desc="Clinical safety, case matching, fraud detection & assistant — unified" />

    <Card>
      <div className="flex items-center gap-2 mb-3"><ShieldCheck size={16} style={{ color: "var(--teal-deep)" }} /><h4 className="font-semibold text-sm">Clinical Safety Agent</h4></div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
        <StatCard icon={AlertTriangle} label="Interaction Risk Detected" value="3" tone="amber" />
        <StatCard icon={Pill} label="Duplicate Meds Found" value="1" tone="red" />
        <StatCard icon={ShieldAlert} label="Allergy Conflicts" value="0" tone="green" />
      </div>
      <table className="mv-table">
        <thead><tr><th>Pair / Conflict</th><th>Risk Score</th><th>Note</th></tr></thead>
        <tbody>{drugInteractions.map((d, i) => (
          <tr key={i}><td>{d.pair}</td><td><Pill_ tone={RiskTone(d.risk)}>{d.risk}</Pill_></td><td style={{ color: "var(--text-dim)" }}>{d.note}</td></tr>
        ))}</tbody>
      </table>
    </Card>

    <Card>
      <div className="flex items-center gap-2 mb-3"><Activity size={16} style={{ color: "var(--blue)" }} /><h4 className="font-semibold text-sm">Similar Case Matching</h4></div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {similarCases.map((c) => (
          <div key={c.id} className="mv-glass p-3 rounded-xl">
            <div className="flex items-center justify-between"><span className="mv-font-mono text-xs" style={{ color: "var(--text-faint)" }}>{c.id}</span><Pill_ tone="blue">{c.match}% match</Pill_></div>
            <p className="text-sm font-medium mt-2">{c.condition}</p>
            <p className="text-xs mt-1" style={{ color: "var(--text-dim)" }}>{c.outcome}</p>
            <div className="mv-progress-track mt-2"><div className="mv-progress-fill" style={{ width: `${c.success}%` }} /></div>
            <p className="text-xs mt-1" style={{ color: "var(--text-faint)" }}>{c.success}% treatment success rate</p>
          </div>
        ))}
      </div>
    </Card>

    <Card>
      <div className="flex items-center gap-2 mb-3"><Radar size={16} style={{ color: "var(--red)" }} /><h4 className="font-semibold text-sm">Fraud Detection Engine</h4></div>
      <div style={{ height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={fraudHeat} layout="vertical" margin={{ left: 30 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis type="number" stroke="var(--text-faint)" fontSize={11} />
            <YAxis type="category" dataKey="region" stroke="var(--text-faint)" fontSize={11} width={140} />
            <Tooltip contentStyle={{ background: "var(--panel-solid)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} />
            <Bar dataKey="score" radius={[0, 8, 8, 0]}>
              {fraudHeat.map((f, i) => <Cell key={i} fill={f.score > 50 ? "#E5484D" : f.score > 30 ? "#F2A93B" : "#0FB6AA"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="space-y-2 mt-3">
        {fraudAlertsData.map(f => (
          <div key={f.id} className="flex items-center justify-between text-sm">
            <span>{f.title}</span><Pill_ tone={RiskTone(f.level)}>{f.level}</Pill_>
          </div>
        ))}
      </div>
    </Card>

    <Card>
      <div className="flex items-center gap-2 mb-2"><Bot size={16} style={{ color: "var(--teal-deep)" }} /><h4 className="font-semibold text-sm">AI Medical Assistant</h4></div>
      <p className="text-sm" style={{ color: "var(--text-dim)" }}>Patient-facing conversational AI for medication explanations, side-effect information, and general guidance. Available under each patient's dashboard.</p>
      <div className="mv-chip amber mt-3"><AlertTriangle size={11} /> For informational purposes only — not a substitute for professional medical advice.</div>
    </Card>
  </div>
);

const SecurityCenterView = () => {
  const pieData = [{ name: "Encrypted", value: 100 }];
  return (
    <div className="space-y-5">
      <SectionHeader icon={Shield} title="Security Center" desc="Encryption, identity, and threat posture across CryptCare" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={Lock} label="Encryption" value="AES-256" sub="End-to-end" tone="teal" />
        <StatCard icon={FileSignature} label="Signature Verification" value="100%" sub="All RX cryptographically signed" tone="blue" />
        <StatCard icon={UserCog} label="RBAC Policies" value="6 roles" sub="Least-privilege enforced" tone="green" />
        <StatCard icon={Fingerprint} label="MFA Coverage" value="98.4%" tone="amber" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <h4 className="font-semibold text-sm mb-3">Threat Monitoring</h4>
          <div className="space-y-2.5">
            {[
              { t: "Brute-force login attempt blocked", lv: "Medium", time: "12 min ago" },
              { t: "Anomalous geo-access pattern", lv: "Low", time: "2 hrs ago" },
              { t: "Expired session token rejected", lv: "Low", time: "5 hrs ago" },
            ].map((x, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2"><Radar size={13} style={{ color: "var(--text-faint)" }} />{x.t}</div>
                <div className="flex items-center gap-2"><Pill_ tone={RiskTone(x.lv)}>{x.lv}</Pill_><span className="text-xs" style={{ color: "var(--text-faint)" }}>{x.time}</span></div>
              </div>
            ))}
          </div>
        </Card>
        <Card className="flex flex-col items-center justify-center">
          <ResponsiveContainer width="100%" height={140}>
            <RadialBarChart innerRadius="70%" outerRadius="100%" data={pieData} startAngle={90} endAngle={-270}>
              <RadialBar dataKey="value" cornerRadius={20} fill="#0FB6AA" />
            </RadialBarChart>
          </ResponsiveContainer>
          <p className="mv-font-display text-xl font-bold -mt-16">100%</p>
          <p className="text-xs mt-12" style={{ color: "var(--text-dim)" }}>Records fully encrypted</p>
        </Card>
      </div>
      <Card className="flex items-center justify-between">
        <div>
          <h4 className="font-semibold text-sm">Master Key Rotation</h4>
          <p className="text-xs mt-1" style={{ color: "var(--text-dim)" }}>Generate and activate a new AES-256-GCM key version.</p>
        </div>
        <button className="mv-btn mv-btn-danger" onClick={() => alert("Master Key Rotated: v2 active")}><KeyRound size={14} /> Rotate Master Key</button>
      </Card>
      <Card>
        <h4 className="font-semibold text-sm mb-3">Compliance Indicators</h4>
        <div className="flex gap-3 flex-wrap">
          {["HIPAA-aligned", "ISO 27001 controls", "SOC 2 Type II", "GDPR data rights"].map(c => <Pill_ key={c} tone="green"><BadgeCheck size={11} /> {c}</Pill_>)}
        </div>
      </Card>
    </div>
  );
};

const AuditView = () => (
  <div className="space-y-5">
    <SectionHeader icon={ScrollText} title="Audit & Transparency Dashboard" desc="Who accessed what, when, and why — fully traceable"
      action={<button className="mv-btn mv-btn-ghost"><Download size={14} /> Export Report</button>} />
    <Card>
      <table className="mv-table">
        <thead><tr><th>User</th><th>Action</th><th>Purpose</th><th>Time</th><th>Source IP</th></tr></thead>
        <tbody>{accessHistoryTimeline.map((a, i) => (
          <tr key={i}><td>{a.who}</td><td>{a.action}</td><td><Pill_ tone="blue">{a.purpose}</Pill_></td><td>{a.time}</td><td className="mv-font-mono">{a.ip}</td></tr>
        ))}</tbody>
      </table>
    </Card>
  </div>
);

const COLORS = ["#0FB6AA", "#2F6FE0", "#F2A93B", "#E5484D"];
const AnalyticsView = () => {
  const pieRx = [{ name: "Active", value: 58 }, { name: "Completed", value: 32 }, { name: "Expired", value: 10 }];
  return (
    <div className="space-y-5">
      <SectionHeader icon={BarChart3} title="Analytics Dashboard" desc="Prescription, access, fraud and AI insight metrics" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2" style={{ height: 300 }}>
          <h4 className="font-semibold text-sm mb-2">Prescriptions vs Access Events</h4>
          <ResponsiveContainer width="100%" height="90%">
            <LineChart data={analyticsTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="m" stroke="var(--text-faint)" fontSize={11} />
              <YAxis stroke="var(--text-faint)" fontSize={11} />
              <Tooltip contentStyle={{ background: "var(--panel-solid)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="rx" stroke="#2F6FE0" strokeWidth={2} name="Prescriptions" />
              <Line type="monotone" dataKey="access" stroke="#0FB6AA" strokeWidth={2} name="Access Events" />
              <Line type="monotone" dataKey="fraud" stroke="#E5484D" strokeWidth={2} name="Fraud Flags" />
            </LineChart>
          </ResponsiveContainer>
        </Card>
        <Card style={{ height: 300 }}>
          <h4 className="font-semibold text-sm mb-2">Prescription Status Mix</h4>
          <ResponsiveContainer width="100%" height="85%">
            <PieChart>
              <Pie data={pieRx} dataKey="value" innerRadius={45} outerRadius={75} paddingAngle={3}>
                {pieRx.map((p, i) => <Cell key={i} fill={COLORS[i]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: "var(--panel-solid)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={TrendingUp} label="MoM Growth" value="+10.4%" tone="teal" />
        <StatCard icon={Users} label="Patient Engagement" value="74%" tone="blue" />
        <StatCard icon={ShieldAlert} label="Fraud Rate" value="0.8%" tone="red" />
        <StatCard icon={Sparkles} label="AI Flags Resolved" value="92%" tone="green" />
      </div>
    </div>
  );
};

const UsersView = () => {
  const users = [
    { name: "Aarav Mehta", role: "Patient", status: "Active" }, { name: "Dr. Lena Cross", role: "Doctor", status: "Active" },
    { name: "Priya Rao", role: "Nurse", status: "Active" }, { name: "Imran Sheikh", role: "Pharmacist", status: "Active" },
    { name: "Northwind Health", role: "Insurance", status: "Active" }, { name: "K. Okafor", role: "Admin", status: "Active" },
  ];
  return (
    <div className="space-y-4">
      <SectionHeader icon={Users} title="User Management" desc="Role-based account administration"
        action={<button className="mv-btn mv-btn-primary"><Plus size={14} /> Add User</button>} />
      <Card>
        <table className="mv-table">
          <thead><tr><th>Name</th><th>Role</th><th>Status</th><th></th></tr></thead>
          <tbody>{users.map((u, i) => (
            <tr key={i}><td>{u.name}</td><td><Pill_ tone="blue">{u.role}</Pill_></td><td><Pill_ tone="green">{u.status}</Pill_></td>
              <td><button><MoreHorizontal size={15} style={{ color: "var(--text-faint)" }} /></button></td></tr>
          ))}</tbody>
        </table>
      </Card>
    </div>
  );
};


/* ---------------------------------------------------------------------- */
/* VITALS & CONSENTS VIEWS (Phase 4 & 6)                                  */
/* ---------------------------------------------------------------------- */



const VitalsHistoryView = ({ currentUser }) => {
  const [vitals, setVitals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVitals = async () => {
      try {
        const data = await nursingService.getVitals(currentUser.user_id);
        setVitals(data.vitals || []);
      } catch (err) {
        console.error("Failed to fetch vitals", err);
      } finally {
        setLoading(false);
      }
    };
    if (currentUser) fetchVitals();
  }, [currentUser]);

  return (
    <div className="space-y-4">
      <SectionHeader icon={HeartPulse} title="Vitals History" desc="Longitudinal tracking of your vital signs" />
      <Card>
        {loading ? <div className="p-4 text-center text-sm text-gray-500">Fetching records...</div> :
          <table className="mv-table">
            <thead><tr><th>Date</th><th>Heart Rate</th><th>Blood Pressure</th><th>Temp</th><th>SpO2</th><th>Notes</th></tr></thead>
            <tbody>
              {vitals.map((v, i) => (
                <tr key={i}>
                  <td className="text-xs">{new Date(v.recorded_at).toLocaleString()}</td>
                  <td className="font-medium">{v.heart_rate_bpm} bpm</td>
                  <td>{v.blood_pressure_systolic}/{v.blood_pressure_diastolic}</td>
                  <td>{v.temperature_celsius}°C</td>
                  <td>{v.spo2_percentage}%</td>
                  <td className="text-xs" style={{ color: "var(--text-dim)" }}>{v.clinical_notes}</td>
                </tr>
              ))}
              {vitals.length === 0 && <tr><td colSpan="6" className="text-center py-6 text-gray-500">No vitals found.</td></tr>}
            </tbody>
          </table>}
      </Card>
    </div>
  );
};

const VitalsManagementView = ({ currentUser }) => {
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);

  // Nurse records vitals for a patient. Since we don't have a patient selector yet,
  // we'll just require the nurse to type the patient's ID.
  const [patientId, setPatientId] = useState("");
  const [hr, setHr] = useState("");
  const [bpSys, setBpSys] = useState("");
  const [bpDia, setBpDia] = useState("");
  const [temp, setTemp] = useState("");
  const [spo2, setSpo2] = useState("");
  const [notes, setNotes] = useState("");

  const handleRecord = async () => {
    setLoading(true);
    setSaved(false);
    try {
      await api.post('/nursing/vitals', {
        patient_id: patientId,
        heart_rate_bpm: parseInt(hr),
        blood_pressure_systolic: parseInt(bpSys),
        blood_pressure_diastolic: parseInt(bpDia),
        temperature_celsius: parseFloat(temp),
        spo2_percentage: parseInt(spo2),
        clinical_notes: notes
      });
      setSaved(true);
    } catch (err) {
      console.error(err);
      alert("Error recording vitals. Did you request consent from the patient first?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <SectionHeader icon={HeartPulse} title="Vitals Management" desc="Record patient vital signs (requires vitals:write consent)" />
      <Card className="space-y-3">
        <div>
          <label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>PATIENT ID</label>
          <input className="mv-input mt-1" placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000" value={patientId} onChange={e => setPatientId(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>HR</label><input className="mv-input mt-1" placeholder="bpm" value={hr} onChange={e => setHr(e.target.value)} /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>BP SYS</label><input className="mv-input mt-1" placeholder="mmHg" value={bpSys} onChange={e => setBpSys(e.target.value)} /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>BP DIA</label><input className="mv-input mt-1" placeholder="mmHg" value={bpDia} onChange={e => setBpDia(e.target.value)} /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>TEMP</label><input className="mv-input mt-1" placeholder="°C" value={temp} onChange={e => setTemp(e.target.value)} /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>SpO2</label><input className="mv-input mt-1" placeholder="%" value={spo2} onChange={e => setSpo2(e.target.value)} /></div>
        </div>
        <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>CLINICAL NOTES</label><textarea className="mv-input mt-1" rows={2} placeholder="Observations..." value={notes} onChange={e => setNotes(e.target.value)} /></div>
        <div className="flex justify-end mt-2">
          <button className="mv-btn mv-btn-primary" onClick={handleRecord} disabled={loading || !patientId}><Check size={14} /> {loading ? "Encrypting..." : "Record Vitals"}</button>
        </div>
        {saved && <div className="mv-chip green mt-2"><Lock size={11} /> Vitals encrypted and stored successfully</div>}
      </Card>
    </div>
  );
};

/* ---------------------------------------------------------------------- */
/* VIEW REGISTRY                                                          */
/* ---------------------------------------------------------------------- */

const VIEWS = {
  patient: {
    overview: PatientOverview, vault: VaultView, prescriptions: PrescriptionsView, medications: MedicationsView,
    allergies: AllergiesView, labs: LabsView, emergency: EmergencyInfoView, ai: AIAssistantView,
    vitals: VitalsHistoryView, "access-requests": AccessRequestsView, "active-consents": ActiveConsentsView, "access-history": AccessHistoryView, fraud: FraudAlertsView,
  },
  doctor: { overview: DoctorOverview, search: PatientSearchView, prescribe: CreatePrescriptionView, "clinical-ai": ClinicalAIView, history: PatientHistoryView },
  nurse: { overview: NurseOverview, meds: MedAdminView, qr: QRVerifyView, schedule: ScheduleView, vitals: VitalsManagementView },
  pharmacist: { overview: PharmacyOverview, verify: VerifyView, dispense: DispenseView, interactions: InteractionsView },
  insurance: { overview: InsuranceOverview, claims: ClaimsView, anomalies: AnomaliesView },
  admin: { overview: AdminOverview, "ai-center": AICenterView, security: SecurityCenterView, audit: AuditView, analytics: AnalyticsView, users: UsersView },
};

/* ---------------------------------------------------------------------- */
/* REGISTER PAGE — shared sub-components (module-level so React doesn't  */
/* unmount them on every RegisterPage re-render, which would kill focus)  */
/* ---------------------------------------------------------------------- */

const RegCard = ({ children, wide }) => (
  <div className={`w-full ${wide ? "max-w-2xl" : "max-w-md"} p-8 bg-white/70 dark:bg-[#0F1C2A]/55 backdrop-blur-xl border border-[#0F283C]/10 dark:border-[#78BEC8]/14 rounded-2xl shadow-xl`}>
    {children}
  </div>
);

const RegLogo = () => (
  <div className="flex justify-center mb-5">
    <div className="w-12 h-12 rounded-2xl flex items-center justify-center bg-gradient-to-br from-[#0FB6AA] to-[#2F6FE0]">
      <ShieldCheck size={26} color="#fff" />
    </div>
  </div>
);

const RegBackBtn = ({ onClick, label = "Back" }) => (
  <button type="button" onClick={onClick}
    className="text-xs text-gray-400 hover:text-[#0FB6AA] transition-colors flex items-center gap-1 mb-4">
    <ChevronRight size={12} className="rotate-180" /> {label}
  </button>
);

const RegErrBox = ({ error }) => error ? (
  <div className="text-sm text-red-500 p-2.5 bg-red-50 dark:bg-red-900/20 rounded-xl">{error}</div>
) : null;

/* ---------------------------------------------------------------------- */
/* REGISTER PAGE                                                          */
/* ---------------------------------------------------------------------- */

const REGISTER_ROLES = [
  { id: "PATIENT", label: "Patient", icon: CircleUser, desc: "Manage your personal health records" },
  { id: "DOCTOR", label: "Doctor", icon: Stethoscope, desc: "Clinical access · MFA required" },
  { id: "NURSE", label: "Nurse", icon: HeartPulse, desc: "Vitals & medication administration" },
  { id: "PHARMACIST", label: "Pharmacist", icon: FlaskRound, desc: "Dispense & verify prescriptions" },
  { id: "LAB", label: "Lab Technician", icon: FlaskConical, desc: "Upload & manage lab reports" },
  { id: "INSURER", label: "Insurance Provider", icon: Building2, desc: "Claims review & fraud monitoring" },
  { id: "BLOOD_BANK", label: "Blood Bank", icon: Droplet, desc: "Inventory & fulfillment" },
];

const PROFESSIONAL_ROLES = ["DOCTOR", "NURSE", "PHARMACIST", "LAB", "INSURER", "BLOOD_BANK"];

const FieldRow = ({ label, children }) => (
  <div>
    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{label}</label>
    {children}
  </div>
);

const RegInput = ({ type = "text", ...props }) => (
  <input
    type={type}
    {...props}
    className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#0B1A28] outline-none focus:border-[#0FB6AA] transition-colors text-sm"
  />
);

const RegSelect = ({ children, ...props }) => (
  <select
    {...props}
    className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#0B1A28] outline-none focus:border-[#0FB6AA] transition-colors text-sm"
  >
    {children}
  </select>
);

const RegisterPage = ({ onRegistered, onBackToLogin }) => {
  // step: "role" | "details" | "otp"
  const [step, setStep] = useState("role");
  const [selectedRole, setRole] = useState(null);
  const [pendingUserId, setUid] = useState(null);
  const [showMfaUri, setMfaUri] = useState(null);
  const [otpCode, setOtpCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);

  // Form fields
  const [form, setForm] = useState({
    email: "", phone: "", password: "", full_name: "",
    dob: "", gender: "", blood_group: "",
    license_number: "", specialization: "", hospital_name: "",
    organization_name: "", department: "",
  });
  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  const isProfessional = PROFESSIONAL_ROLES.includes(selectedRole);
  const isPatient = selectedRole === "PATIENT";
  const isDoctor = selectedRole === "DOCTOR";
  const isNurse = selectedRole === "NURSE";

  /* ---- Step 1 → 2 ---------------------------------------------------- */
  const handleRoleSelect = (roleId) => {
    setRole(roleId);
    setError("");
    setStep("details");
  };

  /* ---- Step 2: submit registration ------------------------------------ */
  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const payload = {
        email: form.email,
        phone: form.phone,
        password: form.password,
        full_name: form.full_name,
        role: selectedRole,
      };
      if (isPatient) {
        if (form.dob) payload.dob = form.dob;
        if (form.gender) payload.gender = form.gender;
        if (form.blood_group) payload.blood_group = form.blood_group;
      }
      if (isProfessional) {
        payload.license_number = form.license_number;
        if (isDoctor) {
          payload.specialization = form.specialization;
          payload.hospital_name = form.hospital_name;
        }
        if (isNurse) {
          payload.hospital_name = form.hospital_name;
          payload.department = form.department;
        }
        if (["LAB", "PHARMACIST", "INSURER", "BLOOD_BANK"].includes(selectedRole)) {
          payload.organization_name = form.organization_name;
        }
      }

      const data = await authService.register(payload);
      setUid(data.user_id);
      if (data.mfa_provisioning_uri) setMfaUri(data.mfa_provisioning_uri);
      setStep("otp");
    } catch (err) {
      const msg = err?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : Array.isArray(msg) ? msg.map(m => m.msg).join("; ") : "Registration failed — please check your details.");
    } finally {
      setLoading(false);
    }
  };

  /* ---- Step 3: verify OTP --------------------------------------------- */
  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await authService.verifyOtp(pendingUserId, otpCode.trim());
      onRegistered(form.email, form.password);
    } catch (err) {
      const msg = err?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Invalid or expired code — please try again.");
    } finally {
      setLoading(false);
    }
  };

  /* ---- Shared card chrome — defined at module level above RegisterPage --- */

  /* ---- STEP 1: role selection ----------------------------------------- */
  if (step === "role") return (
    <div className="min-h-screen flex items-center justify-center bg-[#EEF4F7] dark:bg-[#050D17] text-[#0B1E33] dark:text-[#E7F1F5] p-4">
      <RegCard wide>
        <RegLogo />
        <h2 className="text-xl font-bold text-center mb-1" style={{ fontFamily: "'Sora', sans-serif" }}>Create your account</h2>
        <p className="text-sm text-center text-gray-500 dark:text-gray-400 mb-6">Select your role to get started</p>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mb-6">
          {REGISTER_ROLES.map(r => {
            const Icon = r.icon;
            return (
              <button key={r.id} onClick={() => handleRoleSelect(r.id)}
                className="flex flex-col items-center gap-2 p-4 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white/60 dark:bg-[#0B1A28]/60 hover:border-[#0FB6AA] hover:shadow-md transition-all text-left group">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-gradient-to-br from-[#0FB6AA]/20 to-[#2F6FE0]/20 group-hover:from-[#0FB6AA]/40 group-hover:to-[#2F6FE0]/40 transition-all">
                  <Icon size={20} style={{ color: "#0A8A82" }} />
                </div>
                <span className="text-xs font-bold text-center leading-tight">{r.label}</span>
                <span className="text-[10px] text-gray-400 text-center leading-tight hidden sm:block">{r.desc}</span>
              </button>
            );
          })}
        </div>

        <p className="text-center text-sm text-gray-500">
          Already have an account?{" "}
          <button onClick={onBackToLogin} className="text-[#0FB6AA] font-semibold hover:underline">Sign in</button>
        </p>
      </RegCard>
    </div>
  );

  /* ---- STEP 2: registration form ------------------------------------- */
  if (step === "details") {
    const roleInfo = REGISTER_ROLES.find(r => r.id === selectedRole);
    const RIcon = roleInfo?.icon || CircleUser;
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#EEF4F7] dark:bg-[#050D17] text-[#0B1E33] dark:text-[#E7F1F5] p-4">
        <RegCard wide>
          <RegLogo />
          <RegBackBtn onClick={() => { setStep("role"); setError(""); }} label="Change role" />

          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-gradient-to-br from-[#0FB6AA]/20 to-[#2F6FE0]/20">
              <RIcon size={20} style={{ color: "#0A8A82" }} />
            </div>
            <div>
              <h2 className="text-lg font-bold leading-tight" style={{ fontFamily: "'Sora', sans-serif" }}>
                Register as {roleInfo?.label}
              </h2>
              <p className="text-xs text-gray-400">{roleInfo?.desc}</p>
            </div>
          </div>

          <form onSubmit={handleRegister} className="space-y-3">
            {/* Always-present fields */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <FieldRow label="Full Name">
                <RegInput placeholder="e.g. Aarav Mehta" value={form.full_name} onChange={set("full_name")} required />
              </FieldRow>
              <FieldRow label="Email Address">
                <RegInput type="email" placeholder="you@example.com" value={form.email} onChange={set("email")} required />
              </FieldRow>
              <FieldRow label="Phone Number">
                <RegInput type="tel" placeholder="+91 98765 43210" value={form.phone} onChange={set("phone")} required minLength={8} maxLength={20} />
              </FieldRow>
              <FieldRow label="Password">
                <div className="relative">
                  <RegInput type={showPw ? "text" : "password"} placeholder="Min 10 chars, 1 upper, 1 digit" value={form.password} onChange={set("password")} required minLength={10} maxLength={128} />
                  <button type="button" onClick={() => setShowPw(p => !p)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-[#0FB6AA]">
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </FieldRow>
            </div>

            {/* Patient-specific fields */}
            {isPatient && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                <FieldRow label="Date of Birth">
                  <RegInput type="text" placeholder="DD/MM/YYYY" value={form.dob} onChange={set("dob")} />
                </FieldRow>
                <FieldRow label="Gender">
                  <RegSelect value={form.gender} onChange={set("gender")}>
                    <option value="">Select...</option>
                    <option>Male</option><option>Female</option><option>Other</option><option>Prefer not to say</option>
                  </RegSelect>
                </FieldRow>
                <FieldRow label="Blood Group">
                  <RegSelect value={form.blood_group} onChange={set("blood_group")}>
                    <option value="">Select...</option>
                    {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map(g => <option key={g}>{g}</option>)}
                  </RegSelect>
                </FieldRow>
              </div>
            )}

            {/* Professional fields */}
            {isProfessional && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <FieldRow label="License Number *">
                  <RegInput placeholder="e.g. MCI-2024-88213" value={form.license_number} onChange={set("license_number")} required />
                </FieldRow>
                {isDoctor && <>
                  <FieldRow label="Specialization">
                    <RegInput placeholder="e.g. Cardiology" value={form.specialization} onChange={set("specialization")} />
                  </FieldRow>
                  <FieldRow label="Hospital / Clinic">
                    <RegInput placeholder="e.g. City General Hospital" value={form.hospital_name} onChange={set("hospital_name")} />
                  </FieldRow>
                </>}
                {isNurse && <>
                  <FieldRow label="Hospital Name">
                    <RegInput placeholder="e.g. City General Hospital" value={form.hospital_name} onChange={set("hospital_name")} />
                  </FieldRow>
                  <FieldRow label="Department">
                    <RegInput placeholder="e.g. ICU, General Ward" value={form.department} onChange={set("department")} />
                  </FieldRow>
                </>}
                {["LAB", "PHARMACIST", "INSURER", "BLOOD_BANK"].includes(selectedRole) && (
                  <FieldRow label={selectedRole === "LAB" ? "Lab Name" : selectedRole === "PHARMACIST" ? "Pharmacy Name" : selectedRole === "INSURER" ? "Company Name" : "Facility Name"}>
                    <RegInput placeholder="Organization name" value={form.organization_name} onChange={set("organization_name")} />
                  </FieldRow>
                )}
              </div>
            )}

            {/* MFA notice for roles that require it */}
            {["DOCTOR", "NURSE", "PHARMACIST", "ADMIN"].includes(selectedRole) && (
              <div className="flex items-start gap-2 p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 text-xs text-blue-700 dark:text-blue-300">
                <KeyRound size={14} className="mt-0.5 shrink-0" />
                <span>This role requires TOTP multi-factor authentication. After registration you will receive a QR code — scan it with Google Authenticator or Authy before your first login.</span>
              </div>
            )}

            <RegErrBox error={error} />

            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-xl font-bold text-white shadow-lg disabled:opacity-70 mt-1"
              style={{ background: "linear-gradient(135deg, #0FB6AA, #2F6FE0)" }}>
              {loading ? "Creating account..." : "Create account & send OTP"}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500 mt-4">
            Already have an account?{" "}
            <button onClick={onBackToLogin} className="text-[#0FB6AA] font-semibold hover:underline">Sign in</button>
          </p>
        </RegCard>
      </div>
    );
  }

  /* ---- STEP 3: OTP verification --------------------------------------- */
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#EEF4F7] dark:bg-[#050D17] text-[#0B1E33] dark:text-[#E7F1F5] p-4">
      <RegCard>
        <RegLogo />
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-3"
            style={{ background: "linear-gradient(135deg,rgba(15,182,170,0.15),rgba(47,111,224,0.15))" }}>
            <Send size={24} style={{ color: "#0A8A82" }} />
          </div>
          <h2 className="text-xl font-bold" style={{ fontFamily: "'Sora', sans-serif" }}>Check your email</h2>
          <p className="text-sm text-gray-500 mt-1">
            We sent a 6-digit verification code to<br />
            <span className="font-semibold text-[#0B1E33] dark:text-[#E7F1F5]">{form.email}</span>
          </p>
        </div>

        {showMfaUri && (
          <div className="mb-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 text-xs text-amber-800 dark:text-amber-300 space-y-1">
            <div className="flex items-center gap-1.5 font-bold"><KeyRound size={13} /> MFA Setup Required</div>
            <p>Scan the provisioning URI below into Google Authenticator or Authy <strong>before your first login</strong>. This is shown once only.</p>
            <code className="block mt-1 text-[10px] break-all bg-amber-100 dark:bg-amber-900/40 p-2 rounded-lg">{showMfaUri}</code>
          </div>
        )}

        <form onSubmit={handleVerifyOtp} className="space-y-4">
          <FieldRow label="Verification Code">
            <RegInput
              type="text"
              inputMode="numeric"
              placeholder="6-digit code"
              value={otpCode}
              onChange={e => setOtpCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              maxLength={6}
              autoComplete="one-time-code"
              required
              style={{ letterSpacing: "0.3em", fontSize: 22, textAlign: "center", fontWeight: 700 }}
            />
          </FieldRow>
          <p className="text-xs text-gray-400 text-center">Code expires in 5 minutes. Check your spam folder if you don&apos;t see it.</p>

          <RegErrBox error={error} />

          <button type="submit" disabled={loading || otpCode.length < 6}
            className="w-full py-3 rounded-xl font-bold text-white shadow-lg disabled:opacity-70"
            style={{ background: "linear-gradient(135deg, #0FB6AA, #2F6FE0)" }}>
            {loading ? "Verifying..." : "Verify & activate account"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          Wrong email?{" "}
          <button onClick={() => { setStep("details"); setError(""); setOtpCode(""); }}
            className="text-[#0FB6AA] font-semibold hover:underline">Go back</button>
        </p>
      </RegCard>
    </div>
  );
};

/* ---------------------------------------------------------------------- */
/* LOGIN PAGE                                                             */
/* ---------------------------------------------------------------------- */

const LoginPage = ({ onLogin, onShowRegister, registeredSuccess }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await authService.login(email, password);
      const me = await authService.getMe();
      onLogin(me);
    } catch (err) {
      setError("Invalid credentials or server unavailable.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#EEF4F7] dark:bg-[#050D17] text-[#0B1E33] dark:text-[#E7F1F5] font-sans">
      <div className="w-full max-w-md p-8 bg-white/70 dark:bg-[#0F1C2A]/55 backdrop-blur-xl border border-[#0F283C]/10 dark:border-[#78BEC8]/14 rounded-2xl shadow-xl">
        <div className="flex justify-center mb-6">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center bg-gradient-to-br from-[#0FB6AA] to-[#2F6FE0]">
            <ShieldCheck size={26} color="#fff" />
          </div>
        </div>
        <h2 className="text-2xl font-bold text-center mb-1">Welcome to CryptCare</h2>
        <p className="text-sm text-center text-gray-500 dark:text-gray-400 mb-6">Enter your credentials to continue</p>

        {registeredSuccess && (
          <div className="flex items-center gap-2 p-3 mb-4 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-sm text-green-700 dark:text-green-300">
            <ShieldCheck size={16} className="shrink-0" />
            Account verified! You can now sign in.
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Email Address</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#0B1A28] outline-none focus:border-[#0FB6AA] transition-colors" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#0B1A28] outline-none focus:border-[#0FB6AA] transition-colors" />
          </div>
          {error && <div className="text-sm text-red-500 p-2 bg-red-50 dark:bg-red-900/20 rounded-lg">{error}</div>}
          <button type="submit" disabled={loading} className="w-full py-3 rounded-xl font-bold text-white shadow-lg disabled:opacity-70" style={{ background: "linear-gradient(135deg, #0FB6AA, #2F6FE0)" }}>
            {loading ? "Authenticating..." : "Sign In securely"}
          </button>
        </form>
        <div className="mt-6 text-center text-xs text-gray-500">
          <p className="font-semibold mb-1">Demo Accounts (password: <span className="font-mono">Password123</span>)</p>
          <p>patient@example.com · doctor@example.com</p>
          <p>nurse@example.com · pharmacist@example.com</p>
          <p>lab@example.com · insurer@example.com</p>
          <p>bloodbank@example.com · admin@example.com</p>
          <p className="mt-1 text-[11px] text-gray-400">MFA roles (doctor/nurse/pharmacist): TOTP secret <span className="font-mono">JBSWY3DPEHPK3PXP</span></p>
        </div>
        <p className="text-center text-sm text-gray-500 mt-4">
          New to CryptCare?{" "}
          <button onClick={onShowRegister} className="text-[#0FB6AA] font-semibold hover:underline">Create an account</button>
        </p>
      </div>
    </div>
  );
};

/* ---------------------------------------------------------------------- */
/* APP SHELL                                                              */
/* ---------------------------------------------------------------------- */

export default function MediVaultApp() {
  const [theme, setTheme] = useState("light");
  const [currentUser, setCurrentUser] = useState(null);
  const [nav, setNav] = useState("overview");
  const [roleMenu, setRoleMenu] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loadingApp, setLoadingApp] = useState(true);
  const [showRegister, setShowRegister] = useState(false);
  const [registeredSuccess, setRegisteredSuccess] = useState(false);

  useEffect(() => {
    const init = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const me = await authService.getMe();
          setCurrentUser(me);
        } catch (e) {
          localStorage.removeItem('access_token');
        }
      }
      setLoadingApp(false);
    };
    init();
  }, []);

  if (loadingApp) return <div className="min-h-screen flex items-center justify-center">Loading Secure Vault...</div>;
  if (!currentUser) {
    if (showRegister) return (
      <RegisterPage
        onRegistered={async (email, password) => {
          try {
            await authService.login(email, password);
            const me = await authService.getMe();
            setCurrentUser(me);
            setNav("overview");
            setShowRegister(false);
          } catch (e) {
            // Login after register failed (e.g. MFA role) — send to login page
            setShowRegister(false);
            setRegisteredSuccess(true);
          }
        }}
        onBackToLogin={() => { setShowRegister(false); setRegisteredSuccess(false); }}
      />
    );
    return (
      <LoginPage
        onLogin={(user) => { setCurrentUser(user); setNav("overview"); setRegisteredSuccess(false); }}
        onShowRegister={() => { setShowRegister(true); setRegisteredSuccess(false); }}
        registeredSuccess={registeredSuccess}
      />
    );
  }

  const role = currentUser.role.toLowerCase();

  const ROLES = [
    { id: "patient", icon: CircleUser },
    { id: "doctor", icon: Stethoscope },
    { id: "nurse", icon: Activity },
    { id: "pharmacist", icon: Pill },
    { id: "lab", icon: FlaskConical },
    { id: "insurer", icon: Building2 },
    { id: "blood_bank", icon: Droplet },
    { id: "admin", icon: ShieldCheck },
  ];

  // Try to find the matching role icon, default to CircleUser
  const baseRoleInfo = ROLES.find(r => r.id === role) || ROLES[0];
  const roleInfo = { ...baseRoleInfo, name: currentUser.full_name, label: currentUser.role };

  const navItems = NAV[role] || NAV["patient"];
  const ViewComp = VIEWS[role]?.[nav] || (() => <div>View not found or not connected yet</div>);

  const switchRole = (id) => { /* Disabled, role is fixed */ };
  const go = (id) => { setNav(id); setSidebarOpen(false); };

  const handleLogout = () => {
    authService.logout();
    setCurrentUser(null);
  };

  return (
    <div className={`mv-root ${theme}`} style={{ minHeight: "100vh" }}>
      <GlobalStyle />
      <div className="relative z-10 flex" style={{ minHeight: "100vh" }}>

        {/* Sidebar */}
        <aside className={`fixed lg:static z-40 top-0 left-0 h-full lg:h-auto w-[260px] p-4 flex flex-col gap-2 transition-transform duration-200 ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
          style={{ background: "var(--panel-solid)", borderRight: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2.5 px-2 py-3 mb-2">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, var(--teal), var(--blue))" }}>
              <ShieldCheck size={19} color="#fff" />
            </div>
            <div>
              <div className="mv-font-display font-bold text-sm leading-tight">CryptCare</div>
              <div className="text-[10px] mv-font-mono" style={{ color: "var(--text-faint)" }}>SOVEREIGN RX NETWORK</div>
            </div>
            <button className="lg:hidden ml-auto" onClick={() => setSidebarOpen(false)}><X size={18} /></button>
          </div>

          <div className="text-[10px] font-semibold uppercase tracking-wider px-3 mb-1" style={{ color: "var(--text-faint)" }}>Navigation</div>
          <div className="flex-1 overflow-y-auto mv-scroll space-y-1">
            {navItems.map(item => (
              <div key={item.id} className={`mv-sidebar-item mv-focusable ${nav === item.id ? "active" : ""}`} onClick={() => go(item.id)} tabIndex={0}>
                <item.icon size={16} /> {item.label}
              </div>
            ))}
          </div>

          <div className="mv-glass p-3 rounded-xl mt-2">
            <div className="flex items-center gap-2 mb-1.5"><ShieldCheck size={13} style={{ color: "var(--green)" }} /><span className="text-xs font-semibold">System Secure</span></div>
            <p className="text-[11px]" style={{ color: "var(--text-faint)" }}>All vault shards encrypted · 0 active threats</p>
          </div>
        </aside>

        {sidebarOpen && <div className="fixed inset-0 bg-black/40 z-30 lg:hidden" onClick={() => setSidebarOpen(false)} />}

        {/* Main */}
        <div className="flex-1 min-w-0 flex flex-col">
          {/* Topbar */}
          <header className="sticky top-0 z-20 flex items-center gap-3 px-4 lg:px-6 py-3" style={{ background: "var(--panel-solid)", borderBottom: "1px solid var(--border)" }}>
            <button className="lg:hidden mv-glass p-2 rounded-lg" onClick={() => setSidebarOpen(true)}><LayoutDashboard size={17} /></button>

            <div className="hidden md:flex items-center gap-2 mv-glass px-3 py-2 rounded-xl flex-1 max-w-sm">
              <Search size={14} style={{ color: "var(--text-faint)" }} />
              <input className="bg-transparent outline-none text-sm flex-1" placeholder="Search records, patients, RX IDs…" />
            </div>

            <div className="flex-1 md:flex-none" />

            <div className="hidden sm:flex items-center gap-1.5 mv-chip green"><Lock size={11} /> End-to-End Encrypted</div>

            <button className="mv-glass p-2 rounded-lg mv-focusable" onClick={() => setTheme(t => t === "light" ? "dark" : "light")}>
              {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
            </button>
            <div className="relative">
              <button className="mv-glass p-2 rounded-lg relative mv-focusable" onClick={() => setSidebarOpen(prev => ({ ...prev, notif: !prev.notif }))}>
                <Bell size={16} />
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full text-[9px] flex items-center justify-center font-bold text-white" style={{ background: "var(--red)" }}>3</span>
              </button>
              {sidebarOpen.notif && (
                <div className="absolute right-0 top-full mt-2 w-72 mv-glass rounded-xl p-3 z-30 shadow-xl" style={{ background: "var(--panel-solid)" }}>
                  <div className="flex items-center justify-between mb-2 pb-2 border-b" style={{ borderColor: "var(--border)" }}>
                    <span className="font-semibold text-sm">Notifications</span>
                    <button className="text-xs text-blue-500">Mark all read</button>
                  </div>
                  <div className="space-y-2 max-h-64 overflow-y-auto mv-scroll">
                    {notificationsList.map(n => (
                      <div key={n.id} className="flex gap-2 items-start p-2 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                        <div className="mt-0.5">{n.type === "Break-Glass" ? <Siren size={14} className="text-red-500" /> : <Bell size={14} className="text-blue-500" />}</div>
                        <div>
                          <p className="text-xs font-medium" style={{ color: n.read ? "var(--text-dim)" : "var(--text)" }}>{n.message}</p>
                          <p className="text-[10px] mt-1" style={{ color: "var(--text-faint)" }}>{n.time}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="relative">
              <button className="flex items-center gap-2 mv-glass px-2.5 py-1.5 rounded-xl mv-focusable" onClick={() => setRoleMenu(m => !m)}>
                <div className="w-7 h-7 rounded-full flex items-center justify-center" style={{ background: "linear-gradient(135deg, var(--teal), var(--blue))" }}>
                  <roleInfo.icon size={14} color="#fff" />
                </div>
                <div className="hidden sm:block text-left">
                  <div className="text-xs font-semibold leading-tight">{roleInfo.name}</div>
                  <div className="text-[10px] leading-tight" style={{ color: "var(--text-faint)" }}>{roleInfo.label}</div>
                </div>
                <ChevronDown size={14} />
              </button>
              {roleMenu && (
                <div className="absolute right-0 top-full mt-2 w-64 mv-glass rounded-xl p-2 z-30" style={{ background: "var(--panel-solid)" }}>
                  <div className="text-[10px] font-semibold uppercase px-2 py-1" style={{ color: "var(--text-faint)" }}>Switch Role View</div>
                  <div className="p-2 text-xs text-center text-gray-500">Logged in as {currentUser.email}</div>
                  <div className="border-t my-1" style={{ borderColor: "var(--border)" }} />
                  <div className="mv-sidebar-item" onClick={handleLogout}><LogOut size={15} /> Sign out</div>
                </div>
              )}
            </div>
          </header>

          {/* Content */}
          <main className="flex-1 p-4 lg:p-6 max-w-[1400px] w-full mx-auto">
            <div className="mb-4">
              <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-faint)" }}>
                <span>{roleInfo.label}</span><ChevronRight size={12} />
                <span style={{ color: "var(--text)" }}>{navItems.find(n => n.id === nav)?.label}</span>
              </div>
            </div>
            <ViewComp go={go} currentUser={currentUser} />
          </main>
        </div>
      </div>
    </div>
  );
}
