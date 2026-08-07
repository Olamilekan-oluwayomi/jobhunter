export const jobKeys = {
  all: ["jobs"],
  lists: () => [...jobKeys.all, "list"],
  list: (params) => [...jobKeys.lists(), params],
  detail: (id) => [...jobKeys.all, "detail", id],
};

export const statsKeys = {
  all: ["stats"],
};

export const sourcesKeys = {
  all: ["sources"],
};

export const savedKeys = {
  all: ["saved"],
  lists: () => [...savedKeys.all, "list"],
};

export const applicationKeys = {
  all: ["applications"],
};

export const scrapeKeys = {
  all: ["scrape"],
};