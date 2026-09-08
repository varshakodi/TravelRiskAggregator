import axios from 'axios';

// Twelve-factor config: the backend's address is environment, not code.
// Local dev falls back to localhost; a deployed build sets VITE_API_URL
// (e.g. https://your-backend.onrender.com) at build time.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  // Long enough to sit through a cold boot on idle-sleeping free hosting,
  // short enough that a genuinely dead backend surfaces as an error the
  // user can act on instead of a spinner that never resolves.
  timeout: 90000,
});
