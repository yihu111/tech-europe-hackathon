// Environment configuration
const isDevelopment = import.meta.env.DEV;

export const API_BASE_URL = isDevelopment 
  ? 'http://127.0.0.1:8000'
  : import.meta.env.VITE_API_BASE_URL || 'https://your-production-api.com/api';

export const ENDPOINTS = {
  DEFAULT: `${API_BASE_URL}/`,
  SEARCH: `${API_BASE_URL}/search`,
  GITHUB: `${API_BASE_URL}/repos/`,
} as const;