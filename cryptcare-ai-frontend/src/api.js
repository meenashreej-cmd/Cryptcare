import axios from 'axios';

/**
 * Axios instance for all CryptCare API calls.
 *
 * baseURL is intentionally relative ("/api/v1") so that:
 *  - In development, Vite's proxy (vite.config.js) forwards requests to
 *    http://localhost:8000 — no CORS issues.
 *  - In production, the reverse proxy (nginx / Caddy) routes /api to the
 *    FastAPI container on the same host.
 */
const api = axios.create({
  baseURL: '/api/v1',
});

// ── Request interceptor ────────────────────────────────────────────────────
// Attach the stored JWT access token to every outgoing request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Response interceptor ───────────────────────────────────────────────────
// On a 401, attempt a silent token refresh using the stored refresh token.
// If the refresh succeeds, retry the original request once with the new token.
// If the refresh fails (expired / missing), clear tokens and reload to login.
let _isRefreshing = false;
let _refreshQueue = [];  // queued requests waiting for the new token

const processQueue = (error, token = null) => {
  _refreshQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  _refreshQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    // Only attempt refresh for 401s that haven't already been retried,
    // and skip the refresh endpoint itself to avoid infinite loops.
    if (
      error.response?.status === 401 &&
      !original._retry &&
      !original.url?.includes('/auth/refresh') &&
      !original.url?.includes('/auth/login')
    ) {
      if (_isRefreshing) {
        // Another request is already refreshing — queue this one.
        return new Promise((resolve, reject) => {
          _refreshQueue.push({ resolve, reject });
        }).then((token) => {
          original.headers.Authorization = `Bearer ${token}`;
          return api(original);
        });
      }

      original._retry = true;
      _isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        _isRefreshing = false;
        localStorage.removeItem('access_token');
        window.location.reload();
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post('/api/v1/auth/refresh', {
          refresh_token: refreshToken,
        });
        const newAccessToken = data.access_token;
        localStorage.setItem('access_token', newAccessToken);
        api.defaults.headers.common.Authorization = `Bearer ${newAccessToken}`;
        processQueue(null, newAccessToken);
        original.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(original);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.reload();
        return Promise.reject(refreshError);
      } finally {
        _isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ── AUTH ───────────────────────────────────────────────────────────────────
export const authService = {
  register: async (payload) => {
    const res = await api.post('/auth/register', payload);
    return res.data;
  },
  verifyOtp: async (user_id, otp_code) => {
    const res = await api.post('/auth/verify-otp', { user_id, otp_code });
    return res.data;
  },
  login: async (email, password, otp_code) => {
    const payload = { email, password };
    if (otp_code) payload.otp_code = otp_code;
    const res = await api.post('/auth/login', payload);
    localStorage.setItem('access_token', res.data.access_token);
    localStorage.setItem('refresh_token', res.data.refresh_token);
    return res.data;
  },
  getMe: async () => {
    const res = await api.get('/auth/me');
    return res.data;
  },
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

// ── VAULT ──────────────────────────────────────────────────────────────────
export const vaultService = {
  getPrescriptions: async (patientId) => {
    const res = await api.get(`/vault/prescriptions?patient_id=${patientId}`);
    return res.data;
  },
  createPrescription: async (payload) => {
    const res = await api.post('/vault/prescriptions', payload);
    return res.data;
  },
  getPrescriptionQRUrl: (prescriptionId) =>
    `/api/v1/vault/prescriptions/${prescriptionId}/qr`,
  getAllergies: async (patientId) => {
    const res = await api.get(`/vault/allergies?patient_id=${patientId}`);
    return res.data;
  },
  addAllergy: async (payload) => {
    const res = await api.post('/vault/allergies', payload);
    return res.data;
  },
  getVaccinations: async (patientId) => {
    const res = await api.get(`/vault/vaccinations?patient_id=${patientId}`);
    return res.data;
  },
  addVaccination: async (payload) => {
    const res = await api.post('/vault/vaccinations', payload);
    return res.data;
  },
};

// ── LAB ────────────────────────────────────────────────────────────────────
export const labService = {
  createRequest: async (payload) => {
    const res = await api.post('/lab/requests', payload);
    return res.data;
  },
  startRequest: async (requestId) => {
    const res = await api.put(`/lab/requests/${requestId}/start`);
    return res.data;
  },
  uploadReport: async (requestId, payload) => {
    const res = await api.post(`/lab/requests/${requestId}/report`, payload);
    return res.data;
  },
  getReport: async (reportId) => {
    const res = await api.get(`/lab/reports/${reportId}`);
    return res.data;
  },
};

// ── CONSENT ────────────────────────────────────────────────────────────────
export const consentService = {
  getMyConsents: async () => {
    const res = await api.get('/consent/my-consents');
    return res.data;
  },
  getHistory: async () => {
    const res = await api.get('/consent/history');
    return res.data;
  },
  getTimeline: async () => {
    const res = await api.get('/consent/timeline');
    return res.data;
  },
  approveConsent: async (consentId) => {
    const res = await api.put(`/consent/${consentId}/approve`);
    return res.data;
  },
  rejectConsent: async (consentId) => {
    const res = await api.put(`/consent/${consentId}/reject`);
    return res.data;
  },
  revokeConsent: async (consentId) => {
    const res = await api.post(`/consent/revoke/${consentId}`);
    return res.data;
  },
  requestConsent: async (payload) => {
    const res = await api.post('/consent/request', payload);
    return res.data;
  },
  getMyRequests: async () => {
    const res = await api.get('/consent/my-requests');
    return res.data;
  },
  breakGlass: async (patientId, reason) => {
    const res = await api.post('/consent/break-glass', { patient_id: patientId, reason });
    return res.data;
  },
  getAllConsents: async () => {
    const res = await api.get('/consent/all');
    return res.data;
  },
  grantCaregiver: async (payload) => {
    const res = await api.post('/consent/caregiver/grant', payload);
    return res.data;
  },
};

// ── NURSING ────────────────────────────────────────────────────────────────
export const nursingService = {
  recordVitals: async (payload) => {
    const res = await api.post('/nursing/vitals', payload);
    return res.data;
  },
  getVitals: async (patientId) => {
    const res = await api.get(`/nursing/patients/${patientId}/vitals`);
    return res.data;
  },
  assignNurse: async (payload) => {
    const res = await api.post('/nursing/assign', payload);
    return res.data;
  },
  removeNurse: async (assignmentId) => {
    const res = await api.post(`/nursing/assignments/${assignmentId}/remove`);
    return res.data;
  },
  getAssignments: async () => {
    const res = await api.get('/nursing/assignments');
    return res.data;
  },
  getNursePatients: async () => {
    const res = await api.get('/nursing/my-patients');
    return res.data;
  },
};

// ── PHARMACY ───────────────────────────────────────────────────────────────
export const pharmacyService = {
  verifyQR: async (qrPayload) => {
    const res = await api.post('/pharmacy/verify-qr', { qr_payload: qrPayload });
    return res.data;
  },
  dispense: async (prescriptionId, qrPayload) => {
    const res = await api.post(`/pharmacy/${prescriptionId}/dispense`, { qr_payload: qrPayload });
    return res.data;
  },
};

// ── INSURANCE ──────────────────────────────────────────────────────────────
export const insuranceService = {
  submitClaim: async (payload) => {
    const res = await api.post('/insurance/claims', payload);
    return res.data;
  },
  getClaims: async () => {
    const res = await api.get('/insurance/claims');
    return res.data;
  },
  updateClaimStatus: async (claimId, status) => {
    const res = await api.put(`/insurance/claims/${claimId}/status`, { status });
    return res.data;
  },
};

// ── BLOOD BANK ─────────────────────────────────────────────────────────────
export const bloodBankService = {
  addUnit: async (payload) => {
    const res = await api.post('/blood-bank/units', payload);
    return res.data;
  },
  getInventory: async () => {
    const res = await api.get('/blood-bank/inventory');
    return res.data;
  },
  createRequest: async (payload) => {
    const res = await api.post('/blood-bank/requests', payload);
    return res.data;
  },
  getRequests: async () => {
    const res = await api.get('/blood-bank/requests');
    return res.data;
  },
  fulfillRequest: async (requestId) => {
    const res = await api.put(`/blood-bank/requests/${requestId}/fulfill`);
    return res.data;
  },
  rejectRequest: async (requestId, reason) => {
    const res = await api.put(`/blood-bank/requests/${requestId}/reject`, { reason });
    return res.data;
  },
};

// ── FRAUD ──────────────────────────────────────────────────────────────────
export const fraudService = {
  getAlerts: async (patientId) => {
    const res = await api.get(`/fraud/alerts/${patientId}`);
    return res.data;
  },
  reviewAlert: async (alertId, status) => {
    const res = await api.put(`/fraud/alerts/${alertId}/review`, { status });
    return res.data;
  },
};

// ── AUDIT ──────────────────────────────────────────────────────────────────
export const auditService = {
  getLogs: async (skip = 0, limit = 100) => {
    const res = await api.get(`/audit/logs?skip=${skip}&limit=${limit}`);
    return res.data;
  },
  getStats: async () => {
    const res = await api.get('/audit/stats');
    return res.data;
  },
};

// ── NOTIFICATIONS ──────────────────────────────────────────────────────────
export const notificationService = {
  getAll: async (unreadOnly = false) => {
    const res = await api.get(`/notifications${unreadOnly ? '?unread_only=true' : ''}`);
    return res.data;
  },
  markRead: async (notificationId) => {
    const res = await api.put(`/notifications/${notificationId}/read`);
    return res.data;
  },
};

// ── ADMIN ──────────────────────────────────────────────────────────────────
export const adminService = {
  getPendingVerifications: async () => {
    const res = await api.get('/admin/pending-verifications');
    return res.data;
  },
  verifyLicense: async (userId, approve) => {
    const res = await api.put(`/auth/verify-license/${userId}?approve=${approve}`);
    return res.data;
  },
};

// ── EMERGENCY ──────────────────────────────────────────────────────────────
export const emergencyService = {
  getQRStatus: async () => {
    const res = await api.get('/emergency/qr/status');
    return res.data;
  },
  generateQR: async () => {
    const res = await api.post('/emergency/qr');
    return res.data;
  },
  deleteQR: async () => {
    const res = await api.delete('/emergency/qr');
    return res.data;
  },
  updateContact: async (payload) => {
    const res = await api.put('/emergency/contact', payload);
    return res.data;
  },
};

export default api;
