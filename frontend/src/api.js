import axios from 'axios';

// Twelve-factor config: the backend's address is environment, not code.
// Local dev falls back to localhost; a deployed build sets VITE_API_URL
// (e.g. https://your-backend.onrender.com) at build time.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  // Per-attempt, not per-page-load: the initial fetch retries (see App.jsx),
  // so this only needs to outlast one cold boot rather than every possible
  // one. Keeping it at 60s bounds the worst case to something a person will
  // actually sit through instead of a single 90s stare at a spinner.
  timeout: 60000,
});
