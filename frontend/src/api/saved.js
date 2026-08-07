import client from "./client";

export const getSavedJobs = async () => {
  const { data } = await client.get("/saved");
  return data;
};

export const saveJob = async (jobId) => {
  const { data } = await client.post("/save-job", { job_id: jobId });
  return data;
};

export const unsaveJob = async (savedId) => {
  await client.delete(`/save-job/${savedId}`);
};