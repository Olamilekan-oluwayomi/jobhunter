import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function QueryProvider({ children }) {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        refetchOnWindowFocus: false,
        // Retry transient failures with backoff, but don't hammer on
        // genuinely broken requests (4xx/errors are resolved by the caller).
        retry: (failureCount, error) =>
          failureCount < 3 && error?.response?.status >= 500,
        retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30_000),
      },
      mutations: {
        retry: (failureCount, error) =>
          failureCount < 2 && error?.response?.status >= 500,
      },
    },
  });

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}