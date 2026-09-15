import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "@/shared/auth/AuthContext";
import { LoginPage } from "@/features/auth/LoginPage";
import { WorkspacesPage } from "@/features/workspaces/WorkspacesPage";
import { TrackersPage } from "@/features/trackers/TrackersPage";
import { TrackerGridPage } from "@/features/trackers/TrackerGridPage";
import { ApprovalsPage } from "@/features/approvals/ApprovalsPage";
import { TicketsPage } from "@/features/tickets/TicketsPage";
import { IngestionPage } from "@/features/ingestion/IngestionPage";
import { ChatPlannerPage } from "@/features/chat-planner/ChatPlannerPage";
import { DocumentsPage } from "@/features/documents/DocumentsPage";
import { TeamPage } from "@/features/team/TeamPage";
import { AppLayout } from "@/app/layout/AppLayout";
import { MarketingLayout } from "@/features/marketing/MarketingLayout";
import { HomePage } from "@/features/marketing/HomePage";
import { ProductPage } from "@/features/marketing/ProductPage";
import { PricingPage } from "@/features/marketing/PricingPage";
import { AboutPage } from "@/features/marketing/AboutPage";
import { RequestAccessPage } from "@/features/marketing/RequestAccessPage";

/**
 * Two shells: MarketingLayout (public, unauthenticated -- Home/Product/
 * Pricing/About/Request access) at the root, and AppLayout (the
 * authenticated product, tenant-scoped, per-resource access enforced by
 * the API not here) under /app. /login sits outside both.
 *
 * Route-level auth is still "is there a valid JWT at all" -- per-
 * resource access_level (D-2) and role checks (Admin-only sections
 * like TeamPage's tenant-requests panel) are enforced by the API and
 * simply hidden/errored in the UI when a call 403s, not gated here.
 */
function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route path="/" element={<MarketingLayout />}>
        <Route index element={<HomePage />} />
        <Route path="product" element={<ProductPage />} />
        <Route path="pricing" element={<PricingPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="request-access" element={<RequestAccessPage />} />
      </Route>

      <Route
        path="/app"
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/app/workspaces" replace />} />
        <Route path="workspaces" element={<WorkspacesPage />} />
        <Route path="trackers" element={<TrackersPage />} />
        <Route path="trackers/:trackerId" element={<TrackerGridPage />} />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="tickets" element={<TicketsPage />} />
        <Route path="ingestion" element={<IngestionPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="chat" element={<ChatPlannerPage />} />
        <Route path="team" element={<TeamPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
