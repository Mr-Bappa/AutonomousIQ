import { create } from "zustand";

/**
 * Zustand owns local/UI-only state (STANDARDS.md Section 2) -- things
 * with no server counterpart. Nothing here should ever be a cache of an
 * API response; that's React Query's job (see useWorkspaces.ts for the
 * contrast). This store currently holds exactly one thing: whether the
 * nav rail is collapsed. It'll grow with genuinely UI-only concerns
 * (open modals, active tab, draft form state) as more features land --
 * it deliberately doesn't hold anything yet for features that aren't
 * built (Trackers, approvals, etc.).
 */
interface UiState {
  navCollapsed: boolean;
  toggleNav: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  navCollapsed: false,
  toggleNav: () => set((state) => ({ navCollapsed: !state.navCollapsed })),
}));
