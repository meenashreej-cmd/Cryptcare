import re
import sys

file_path = r"c:\Users\meena\OneDrive\Desktop\cryptcare\cryptcare\cryptcare-frontend\src\CryptCareApp.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add imports for api
if "import { authService, vaultService, consentService, nursingService } from './api';" not in content:
    content = content.replace(
        'import React, { useState, useEffect, useMemo, useRef } from "react";',
        'import React, { useState, useEffect, useMemo, useRef } from "react";\nimport { authService, vaultService, consentService, nursingService } from "./api";'
    )

# 2. Replace the App Shell
old_app_shell = """/* ---------------------------------------------------------------------- */
/* APP SHELL                                                              */
/* ---------------------------------------------------------------------- */

export default function CryptCareApp() {
  const [theme, setTheme] = useState("light");
  const [role, setRole] = useState("patient");
  const [nav, setNav] = useState("overview");
  const [roleMenu, setRoleMenu] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const roleInfo = ROLES.find(r => r.id === role);
  const navItems = NAV[role];
  const ViewComp = VIEWS[role][nav] || (() => <div>Not found</div>);

  const switchRole = (id) => { setRole(id); setNav("overview"); setRoleMenu(false); setSidebarOpen(false); };
  const go = (id) => { setNav(id); setSidebarOpen(false); };"""

new_app_shell = """/* ---------------------------------------------------------------------- */
/* LOGIN PAGE                                                             */
/* ---------------------------------------------------------------------- */

const LoginPage = ({ onLogin }) => {
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
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Email Address</label>
            <input type="email" value={email} onChange={e=>setEmail(e.target.value)} required className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#0B1A28] outline-none focus:border-[#0FB6AA] transition-colors" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Password</label>
            <input type="password" value={password} onChange={e=>setPassword(e.target.value)} required className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#0B1A28] outline-none focus:border-[#0FB6AA] transition-colors" />
          </div>
          {error && <div className="text-sm text-red-500 p-2 bg-red-50 dark:bg-red-900/20 rounded-lg">{error}</div>}
          <button type="submit" disabled={loading} className="w-full py-3 rounded-xl font-bold text-white shadow-lg disabled:opacity-70" style={{ background: "linear-gradient(135deg, #0FB6AA, #2F6FE0)" }}>
            {loading ? "Authenticating..." : "Sign In securely"}
          </button>
        </form>
        <div className="mt-6 text-center text-xs text-gray-500">
          <p>Demo Accounts:</p>
          <p>patient@example.com | doctor@example.com | nurse@example.com | admin@example.com</p>
          <p>Password: password123</p>
        </div>
      </div>
    </div>
  );
};

/* ---------------------------------------------------------------------- */
/* APP SHELL                                                              */
/* ---------------------------------------------------------------------- */

export default function CryptCareApp() {
  const [theme, setTheme] = useState("light");
  const [currentUser, setCurrentUser] = useState(null);
  const [nav, setNav] = useState("overview");
  const [roleMenu, setRoleMenu] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loadingApp, setLoadingApp] = useState(true);

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
  if (!currentUser) return <LoginPage onLogin={(user) => { setCurrentUser(user); setNav("overview"); }} />;

  const role = currentUser.role.toLowerCase();
  
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
  };"""

content = content.replace(old_app_shell, new_app_shell)

# 3. Replace the logout button in role menu
content = content.replace(
    '<div className="mv-sidebar-item"><LogOut size={15} /> Sign out</div>',
    '<div className="mv-sidebar-item" onClick={handleLogout}><LogOut size={15} /> Sign out</div>'
)

# 4. Hide the role switcher items but keep the logout button in the dropdown
role_menu_old = """                  {ROLES.map(r => (
                    <div key={r.id} className={`mv-sidebar-item ${role === r.id ? "active" : ""}`} onClick={() => switchRole(r.id)}>
                      <r.icon size={15} /> {r.label}
                    </div>
                  ))}
                  <div className="border-t my-1" style={{ borderColor: "var(--border)" }} />"""

role_menu_new = """                  <div className="p-2 text-xs text-center text-gray-500">Logged in as {currentUser.email}</div>
                  <div className="border-t my-1" style={{ borderColor: "var(--border)" }} />"""
content = content.replace(role_menu_old, role_menu_new)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated Auth Flow in CryptCareApp.jsx")
