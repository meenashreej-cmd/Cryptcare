import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
});

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// AUTH
export const authService = {
  register: async (payload) => { const res = await api.post('/auth/register', payload); return res.data; },
  verifyOtp: async (user_id, otp_code) => { const res = await api.post('/auth/verify-otp', { user_id, otp_code }); return res.data; },
  login: async (email, password, otp_code) => {
    const payload = { email, password };
    if (otp_code) payload.otp_code = otp_code;
    const res = await api.post('/auth/login', payload);
    localStorage.setItem('access_token', res.data.access_token);
    return res.data;
  },
  getMe: async () => { const res = await api.get('/auth/me'); return res.data; },
  logout: () => { localStorage.removeItem('access_token'); },
};

// VAULT
export const vaultService = {
  getPrescriptions: async (patientId) => { const res = await api.get(`/vault/prescriptions?patient_id=${patientId}`); return res.data; },
  createPrescription: async (payload) => { const res = await api.post('/vault/prescriptions', payload); return res.data; },
  getPrescriptionQRUrl: (prescriptionId) => `${api.defaults.baseURL}/vault/prescriptions/${prescriptionId}/qr`,
  getAllergies: async (patientId) => { const res = await api.get(`/vault/allergies?patient_id=${patientId}`); return res.data; },
  addAllergy: async (payload) => { const res = await api.post('/vault/allergies', payload); return res.data; },
  getVaccinations: async (patientId) => { const res = await api.get(`/vault/vaccinations?patient_id=${patientId}`); return res.data; },
  addVaccination: async (payload) => { const res = await api.post('/vault/vaccinations', payload); return res.data; },
};

// LAB
export const labService = {
  createRequest: async (payload) => { const res = await api.post('/lab/requests', payload); return res.data; },
  startRequest: async (requestId) => { const res = await api.put(`/lab/requests/${requestId}/start`); return res.data; },
  uploadReport: async (requestId, payload) => { const res = await api.post(`/lab/requests/${requestId}/report`, payload); return res.data; },
  getReport: async (reportId) => { const res = await api.get(`/lab/reports/${reportId}`); return res.data; },
};

// CONSENT
export const consentService = {
  getMyConsents: async () => { const res = await api.get('/consent/my-consents'); return res.data; },
  getHistory: async () => { const res = await api.get('/consent/history'); return res.data; },
  getTimeline: async () => { const res = await api.get('/consent/timeline'); return res.data; },
  approveConsent: async (consentId) => { const res = await api.put(`/consent/${consentId}/approve`); return res.data; },
  rejectConsent: async (consentId) => { const res = await api.put(`/consent/${consentId}/reject`); return res.data; },
  revokeConsent: async (consentId) => { const res = await api.post(`/consent/revoke/${consentId}`); return res.data; },
  requestConsent: async (payload) => { const res = await api.post('/consent/request', payload); return res.data; },
  getMyRequests: async () => { const res = await api.get('/consent/my-requests'); return res.data; },
  breakGlass: async (patientId, reason) => { const res = await api.post('/consent/break-glass', { patient_id: patientId, reason }); return res.data; },
  getAllConsents: async () => { const res = await api.get('/consent/all'); return res.data; },
  grantCaregiver: async (payload) => { const res = await api.post('/consent/caregiver/grant', payload); return res.data; },
};

// NURSING
export const nursingService = {
  recordVitals: async (payload) => { const res = await api.post('/nursing/vitals', payload); return res.data; },
  getVitals: async (patientId) => { const res = await api.get(`/nursing/patients/${patientId}/vitals`); return res.data; },
};

// PHARMACY
export const pharmacyService = {
  verifyQR: async (qrPayload) => { const res = await api.post('/pharmacy/verify-qr', { qr_payload: qrPayload }); return res.data; },
  dispense: async (prescriptionId, qrPayload) => { const res = await api.post(`/pharmacy/${prescriptionId}/dispense`, { qr_payload: qrPayload }); return res.data; },
};

// INSURANCE
export const insuranceService = {
  submitClaim: async (payload) => { const res = await api.post('/insurance/claims', payload); return res.data; },
  getClaims: async () => { const res = await api.get('/insurance/claims'); return res.data; },
  updateClaimStatus: async (claimId, status) => { const res = await api.put(`/insurance/claims/${claimId}/status`, { status }); return res.data; },
};

// BLOOD BANK
export const bloodBankService = {
  addUnit: async (payload) => { const res = await api.post('/blood-bank/units', payload); return res.data; },
  getInventory: async () => { const res = await api.get('/blood-bank/inventory'); return res.data; },
  createRequest: async (payload) => { const res = await api.post('/blood-bank/requests', payload); return res.data; },
  getRequests: async () => { const res = await api.get('/blood-bank/requests'); return res.data; },
  fulfillRequest: async (requestId) => { const res = await api.put(`/blood-bank/requests/${requestId}/fulfill`); return res.data; },
  rejectRequest: async (requestId, reason) => { const res = await api.put(`/blood-bank/requests/${requestId}/reject`, { reason }); return res.data; },
};

// FRAUD
export const fraudService = {
  getAlerts: async (patientId) => { const res = await api.get(`/fraud/alerts/${patientId}`); return res.data; },
  reviewAlert: async (alertId, status) => { const res = await api.put(`/fraud/alerts/${alertId}/review`, { status }); return res.data; },
};

// AUDIT
export const auditService = {
  getLogs: async (skip = 0, limit = 100) => { const res = await api.get(`/audit/logs?skip=${skip}&limit=${limit}`); return res.data; },
  getStats: async () => { const res = await api.get('/audit/stats'); return res.data; },
};

// NOTIFICATIONS
export const notificationService = {
  getAll: async (unreadOnly = false) => { const res = await api.get(`/notifications${unreadOnly ? '?unread_only=true' : ''}`); return res.data; },
  markRead: async (notificationId) => { const res = await api.put(`/notifications/${notificationId}/read`); return res.data; },
};

// ADMIN
export const adminService = {
  getPendingVerifications: async () => { const res = await api.get('/admin/pending-verifications'); return res.data; },
  verifyLicense: async (userId, approve) => { const res = await api.put(`/auth/verify-license/${userId}?approve=${approve}`); return res.data; },
};

// EMERGENCY
export const emergencyService = {
  getQRStatus: async () => { const res = await api.get('/emergency/qr/status'); return res.data; },
  generateQR: async () => { const res = await api.post('/emergency/qr'); return res.data; },
  deleteQR: async () => { const res = await api.delete('/emergency/qr'); return res.data; },
  updateContact: async (payload) => { const res = await api.put('/emergency/contact', payload); return res.data; },
};

export default api;
