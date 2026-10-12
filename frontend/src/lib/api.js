import axios from "axios";

// Kosong/tidak di-set (build Docker tunggal Coolify) → API di origin yang sama (/api)
export const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
export const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

export default api;
