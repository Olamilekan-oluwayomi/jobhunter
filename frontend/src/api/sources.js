import client from "./client";

export const getSources = async () => {
  const { data } = await client.get("/sources");
  return data;
};