import client from "./client";

export const getStats = async () => {
  const { data } = await client.get("/stats");
  return data;
};