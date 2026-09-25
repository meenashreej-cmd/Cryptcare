const fs = require('fs');
const babel = require('@babel/core');

try {
  const result = babel.transformFileSync('src/CryptcareApp.jsx', {
    presets: ['@babel/preset-react']
  });

  let code = result.code;
  // Stub imports
  code = code.replace(/import .* from .*;/g, '');
  // Stub export default
  code = code.replace(/export default .*/g, '');

  // Wrap in function to avoid strict mode issues with imports
  const wrappedCode = `
    const React = { useState: ()=>{}, useEffect: ()=>{}, useMemo: ()=>{}, useRef: ()=>{} };
    const useState = React.useState;
    const useEffect = React.useEffect;
    const useMemo = React.useMemo;
    const useRef = React.useRef;
    const api = {};
    const authService = {}; const vaultService = {}; const consentService = {}; const nursingService = {};
    const fraudService = {}; const insuranceService = {}; const auditService = {}; const notificationService = {};
    const adminService = {}; const bloodBankService = {}; const labService = {}; const hospitalService = {};
    const ShieldCheck = 'ShieldCheck'; const ShieldAlert = 'ShieldAlert'; const Shield = 'Shield'; const Lock = 'Lock'; const Unlock = 'Unlock'; const Fingerprint = 'Fingerprint'; const KeyRound = 'KeyRound';
    const LayoutDashboard = 'LayoutDashboard'; const FolderLock = 'FolderLock'; const FileText = 'FileText'; const Pill = 'Pill'; const AlertTriangle = 'AlertTriangle'; const FlaskConical = 'FlaskConical';
    const HeartPulse = 'HeartPulse'; const Bot = 'Bot'; const Inbox = 'Inbox'; const History = 'History'; const Siren = 'Siren'; const Users = 'Users'; const Search = 'Search'; const Stethoscope = 'Stethoscope';
    const ClipboardCheck = 'ClipboardCheck'; const QrCode = 'QrCode'; const ScanLine = 'ScanLine'; const CalendarClock = 'CalendarClock'; const PackageSearch = 'PackageSearch'; const FlaskRound = 'FlaskRound';
    const BadgeCheck = 'BadgeCheck'; const Activity = 'Activity'; const BarChart3 = 'BarChart3'; const ScrollText = 'ScrollText'; const Settings = 'Settings'; const Bell = 'Bell'; const Sun = 'Sun'; const Moon = 'Moon';
    const ChevronDown = 'ChevronDown'; const X = 'X'; const Check = 'Check'; const Upload = 'Upload'; const Eye = 'Eye'; const EyeOff = 'EyeOff'; const LogOut = 'LogOut'; const Plus = 'Plus'; const Clock = 'Clock'; const MapPin = 'MapPin';
    const Phone = 'Phone'; const Droplet = 'Droplet'; const UserCog = 'UserCog'; const Building2 = 'Building2'; const Server = 'Server'; const Radar = 'Radar'; const Sparkles = 'Sparkles'; const ChevronRight = 'ChevronRight';
    const Send = 'Send'; const FileSignature = 'FileSignature'; const TimerReset = 'TimerReset'; const ShieldX = 'ShieldX'; const Zap = 'Zap'; const TrendingUp = 'TrendingUp'; const AlertOctagon = 'AlertOctagon';
    const CircleUser = 'CircleUser'; const Filter = 'Filter'; const Download = 'Download'; const MoreHorizontal = 'MoreHorizontal';
    
    ${code}
  `;

  eval(wrappedCode);
  console.log("No top-level ReferenceError found.");
} catch (e) {
  console.error("Caught error:", e);
}
