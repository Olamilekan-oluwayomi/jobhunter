import client from "./client";

export const getJobs = async (params = {}) => {
  const { data } = await client.get("/jobs", {
    params: { page_size: 50, ...params },
  });
  return data;
};

export const getJob = async (jobId) => {
  const { data } = await client.get(`/jobs/${jobId}`);
  return data;
};