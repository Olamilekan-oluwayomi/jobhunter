import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api",
  withCredentials: true,
  timeout: 20000,
  headers: { "X-Requested-With": "JobHunter" },
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      !error.config?.url?.startsWith("/auth/")
    )
      window.dispatchEvent(new Event("jobhunter-session-expired"));
    return Promise.reject(error);
  },
);

export default client;
