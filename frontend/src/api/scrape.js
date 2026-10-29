import client from "./client";

export const runScrape = async () => {
  const { data } = await client.post("/scrape", null, { timeout: 300000 });
  return data;
};

export const getScrapeRuns = async (limit = 5) => {
  const { data } = await client.get("/scrape-runs", { params: { limit } });
  return data;
};
