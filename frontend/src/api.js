import axios from 'axios';

// Twelve-factor config: the backend's address is environment, not code.
// Local dev falls back to localhost; a deployed build sets VITE_API_URL
// (e.g. https://your-backend.onrender.com) at build time.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});
