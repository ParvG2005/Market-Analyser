import type { Session, User } from "@supabase/supabase-js";
import { create } from "zustand";
import { persist } from "zustand/middleware";

import { supabase } from "../lib/supabase";

interface AuthState {
  user: User | null;
  session: Session | null;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  setSession: (session: Session | null) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      session: null,
      isAuthenticated: false,
      setSession: (session) =>
        set({ session, user: session?.user ?? null, isAuthenticated: session != null }),
      signIn: async (email, password) => {
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        set({ session: data.session, user: data.user, isAuthenticated: data.session != null });
      },
      signUp: async (email, password) => {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        set({ session: data.session, user: data.user, isAuthenticated: data.session != null });
      },
      signOut: async () => {
        const { error } = await supabase.auth.signOut();
        if (error) throw error;
        set({ session: null, user: null, isAuthenticated: false });
      },
    }),
    {
      // Persists minimally (user + session) so a reload doesn't drop the UI
      // back to signed-out before Supabase's own onAuthStateChange fires.
      name: "market-assistant-auth",
      partialize: (state) => ({ user: state.user, session: state.session }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.isAuthenticated = state.session != null;
        }
      },
    },
  ),
);

let authInitialized = false;

/**
 * Registers the Supabase auth-state listener once so sign-in/refresh/sign-out
 * events (including those from another tab) keep the store in sync. Safe to
 * call multiple times — only the first call subscribes.
 */
export function initAuth(): void {
  if (authInitialized) return;
  authInitialized = true;
  supabase.auth.onAuthStateChange((_event, session) => {
    useAuthStore.getState().setSession(session);
  });
}
