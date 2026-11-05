import axios from "axios";
const apiOrigin = (import.meta.env.VITE_API_URL || "http://localhost:5656").replace(/\/+$/, "");
export const api = axios.create({
  baseURL: `${apiOrigin}/api`
});
api.interceptors.request.use(cfg=>{
  const token = localStorage.getItem("vita_token");
  if(token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});
