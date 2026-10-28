import client from "./client";

export const getApplications = async (params) => {
  const { data } = await client.get("/applications", { params });
  return data;
};

export const createApplication = async (payload) => {
  const { data } = await client.post("/applications", payload);
  return data;
};

export const updateApplication = async (applicationId, payload) => {
  const { data } = await client.patch(`/applications/${applicationId}`, payload);
  return data;
};
