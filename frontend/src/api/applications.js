import client from "./client";

export const createApplication = async (payload) => {
  const { data } = await client.post("/applications", payload);
  return data;
};

export const updateApplication = async (applicationId, payload) => {
  const { data } = await client.patch(`/applications/${applicationId}`, payload);
  return data;
};