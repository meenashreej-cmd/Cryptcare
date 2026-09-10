import re
import sys

file_path = r"c:\Users\meena\OneDrive\Desktop\cryptcare\cryptcare\medivault-ai-frontend\src\MediVaultApp.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Pass currentUser to ViewComp
content = content.replace(
    "<ViewComp go={go} />",
    "<ViewComp go={go} currentUser={currentUser} />"
)

# 2. Update PrescriptionsView
old_prescriptions = """const PrescriptionsView = () => {
  const [qr, setQr] = useState(null);
  return (
    <div className="space-y-4">
      <SectionHeader icon={FileText} title="Prescription History" desc="All prescriptions issued under your MediVault record" />
      <Card>
        <table className="mv-table">
          <thead><tr><th>RX ID</th><th>Medication</th><th>Doctor</th><th>Date</th><th>Status</th><th>Signature</th><th>QR</th></tr></thead>
          <tbody>
            {prescriptionHistory.map(p => (
              <tr key={p.id}>
                <td className="mv-font-mono">{p.id}</td><td>{p.med}</td><td>{p.doctor}</td><td>{p.date}</td>
                <td><Pill_ tone={p.status === "Active" ? "teal" : "blue"}>{p.status}</Pill_></td>
                <td>{p.signed && <span className="mv-chip green"><FileSignature size={11} /> Verified</span>}</td>
                <td><button className="mv-btn mv-btn-ghost py-1 px-2" onClick={() => setQr(p.id)}><QrCode size={14} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {qr && <PrescriptionQRModal rxid={qr} onClose={() => setQr(null)} />}
    </div>
  );
};"""

new_prescriptions = """const PrescriptionsView = ({ currentUser }) => {
  const [qr, setQr] = useState(null);
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRx = async () => {
      try {
        const data = await vaultService.getPrescriptions(currentUser.user_id);
        setPrescriptions(data);
      } catch (err) {
        console.error("Failed to fetch prescriptions", err);
      } finally {
        setLoading(false);
      }
    };
    if (currentUser) fetchRx();
  }, [currentUser]);

  return (
    <div className="space-y-4">
      <SectionHeader icon={FileText} title="Prescription History" desc="All prescriptions issued under your MediVault record" />
      <Card>
        {loading ? <div className="p-4 text-center text-sm text-gray-500">Decrypting vault records...</div> : 
        <table className="mv-table">
          <thead><tr><th>RX ID</th><th>Medication</th><th>Date</th><th>Status</th><th>QR</th></tr></thead>
          <tbody>
            {prescriptions.map(p => (
              <tr key={p.prescription_id}>
                <td className="mv-font-mono">{p.prescription_id.slice(0, 8)}...</td>
                <td>
                  {p.items.map(i => <div key={i.item_id}>{i.medicine_name} - {i.dosage}</div>)}
                </td>
                <td>{new Date(p.created_at).toLocaleDateString()}</td>
                <td><Pill_ tone={p.status === "ACTIVE" ? "teal" : "blue"}>{p.status}</Pill_></td>
                <td><button className="mv-btn mv-btn-ghost py-1 px-2" onClick={() => setQr(p.prescription_id)}><QrCode size={14} /></button></td>
              </tr>
            ))}
            {prescriptions.length === 0 && <tr><td colSpan="5" className="text-center py-6 text-gray-500">No prescriptions found in your vault.</td></tr>}
          </tbody>
        </table>
        }
      </Card>
      {qr && <PrescriptionQRModal rxid={qr} onClose={() => setQr(null)} />}
    </div>
  );
};"""
content = content.replace(old_prescriptions, new_prescriptions)

# 3. Update VitalsHistoryView
old_vitals = """const VitalsHistoryView = () => (
  <div className="space-y-4">
    <SectionHeader icon={HeartPulse} title="Vitals History" desc="Longitudinal tracking of your vital signs" />
    <Card>
      <table className="mv-table">
        <thead><tr><th>Date</th><th>Heart Rate</th><th>Blood Pressure</th><th>Temp</th><th>SpO2</th><th>Notes</th></tr></thead>
        <tbody>
          {vitalsData.map((v, i) => (
            <tr key={i}>
              <td className="text-xs">{v.date}</td>
              <td className="font-medium">{v.hr} bpm</td>
              <td>{v.bp}</td>
              <td>{v.temp}</td>
              <td>{v.spo2}</td>
              <td className="text-xs" style={{ color: "var(--text-dim)" }}>{v.notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  </div>
);"""

new_vitals = """const VitalsHistoryView = ({ currentUser }) => {
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
};"""
content = content.replace(old_vitals, new_vitals)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated Prescriptions and Vitals Views in MediVaultApp.jsx")
