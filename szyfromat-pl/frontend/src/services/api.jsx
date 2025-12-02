import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  login: (username, password) => 
    api.post('/api/auth/login', { username, password }),
  
  getMe: () => 
    api.get('/api/auth/me'),
};

// Messages
export const messagesApi = {
  getAll: (folder = 'inbox', limit = 50, offset = 0) =>
    api.get('/api/messages', { params: { folder, limit, offset } }),
  
  getOne: (id) =>
    api.get(`/api/messages/${id}`),
  
  send: (data) =>
    api.post('/api/messages', data),
  
  delete: (id) =>
    api.delete(`/api/messages/${id}`),
  
  archive: (id) =>
    api.post(`/api/messages/${id}/archive`),
  
  move: (id, folder) =>
    api.post(`/api/messages/${id}/move`, { folder }),
  
  markAsRead: (id) =>
    api.post(`/api/messages/${id}/read`),
};

// Folders
export const foldersApi = {
  getAll: () =>
    api.get('/api/folders'),
};

// Integrations
export const integrationsApi = {
  getStatus: () =>
    api.get('/api/integrations'),
};

export default api;
