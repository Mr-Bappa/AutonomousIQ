import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "@/shared/auth/AuthContext";
import { App } from "@/app/App";
import "@/shared/design/tokens.css";

// One QueryClient for the whole app -- React Query is the single source
// of truth for server state (STANDARDS.md Section 2), so this instance
// (not per-feature clients) is what every useQuery/useMutation in
// features/* shares.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
