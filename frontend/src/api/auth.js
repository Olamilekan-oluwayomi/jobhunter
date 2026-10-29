import client from "./client";

export const getMe = async () => (await client.get("/auth/me")).data;
export const login = async (payload) =>
  (await client.post("/auth/login", payload)).data;
export const register = async (payload) =>
  (await client.post("/auth/register", payload)).data;
export const logout = async () => client.post("/auth/logout");
export const saveProfile = async (profile) =>
  (await client.put("/auth/profile", profile)).data;
export const getWorkspaceIndex = async () =>
  (await client.get("/workspace-index")).data;
export const discoverJobs = async (params, signal) =>
  (await client.get("/discovery", { params, signal })).data;
export const getDiscoveryJob = async (id, signal) =>
  (await client.get(`/discovery/${id}`, { signal })).data;
