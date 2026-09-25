import re
import sys

file_path = r"c:\Users\meena\OneDrive\Desktop\cryptcare\cryptcare\cryptcare-frontend\src\CryptCareApp.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_vitals_management = """const VitalsManagementView = () => {
  const [saved, setSaved] = useState(false);
  return (
    <div className="space-y-4">
      <SectionHeader icon={HeartPulse} title="Vitals Management" desc="Record patient vital signs (requires vitals:write consent)" />
      <Card className="space-y-3">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>HEART RATE</label><input className="mv-input mt-1" placeholder="bpm" /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>BLOOD PRESSURE</label><input className="mv-input mt-1" placeholder="mmHg" /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>TEMPERATURE</label><input className="mv-input mt-1" placeholder="°F or °C" /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>SpO2</label><input className="mv-input mt-1" placeholder="%" /></div>
        </div>
        <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>CLINICAL NOTES</label><textarea className="mv-input mt-1" rows={2} placeholder="Observations..." /></div>
        <div className="flex justify-end mt-2">
          <button className="mv-btn mv-btn-primary" onClick={() => setSaved(true)}><Check size={14} /> Record Vitals</button>
        </div>
        {saved && <div className="mv-chip green mt-2"><Lock size={11} /> Vitals encrypted and stored successfully</div>}
      </Card>
      <VitalsHistoryView />
    </div>
  );
};"""

new_vitals_management = """const VitalsManagementView = ({ currentUser }) => {
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
          <input className="mv-input mt-1" placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000" value={patientId} onChange={e=>setPatientId(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>HR</label><input className="mv-input mt-1" placeholder="bpm" value={hr} onChange={e=>setHr(e.target.value)} /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>BP SYS</label><input className="mv-input mt-1" placeholder="mmHg" value={bpSys} onChange={e=>setBpSys(e.target.value)} /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>BP DIA</label><input className="mv-input mt-1" placeholder="mmHg" value={bpDia} onChange={e=>setBpDia(e.target.value)} /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>TEMP</label><input className="mv-input mt-1" placeholder="°C" value={temp} onChange={e=>setTemp(e.target.value)} /></div>
          <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>SpO2</label><input className="mv-input mt-1" placeholder="%" value={spo2} onChange={e=>setSpo2(e.target.value)} /></div>
        </div>
        <div><label className="text-xs font-semibold" style={{ color: "var(--text-faint)" }}>CLINICAL NOTES</label><textarea className="mv-input mt-1" rows={2} placeholder="Observations..." value={notes} onChange={e=>setNotes(e.target.value)} /></div>
        <div className="flex justify-end mt-2">
          <button className="mv-btn mv-btn-primary" onClick={handleRecord} disabled={loading || !patientId}><Check size={14} /> {loading ? "Encrypting..." : "Record Vitals"}</button>
        </div>
        {saved && <div className="mv-chip green mt-2"><Lock size={11} /> Vitals encrypted and stored successfully</div>}
      </Card>
    </div>
  );
};"""

content = content.replace(old_vitals_management, new_vitals_management)

# We also need to export `api` from api.js and import it in CryptCareApp.jsx
if "import api, { authService" not in content:
    content = content.replace(
        'import { authService, vaultService, consentService, nursingService } from "./api";',
        'import api, { authService, vaultService, consentService, nursingService } from "./api";'
    )

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated VitalsManagementView in CryptCareApp.jsx")
