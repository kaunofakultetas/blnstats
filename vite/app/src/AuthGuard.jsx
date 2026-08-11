// -----------------------------------------------------------
//  [*] AuthGuard — session state for the whole app
//
//  One TanStack query — GET /api/checkauth with the session
//  cookie — shared through context as authData ({ id, email,
//  admin }, undefined when anonymous) and ready. retry is off
//  so an expired session settles immediately, and staleTime
//  Infinity means a login or logout only shows up after a
//  full page load.
//
//  A failed check does NOT redirect: most pages are public,
//  so a dead cookie just leaves authData undefined and the
//  header offers Login. Only the admin section is gated, and
//  that gate lives in AdminPageLayout.
//
//  Used by:
//    - App.jsx — AuthProvider wraps every page except /login
//    - Header — Login/Logout button and the Admin nav item
//    - AdminPageLayout — the admin-only gate
// -----------------------------------------------------------

import { createContext, useContext, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';


const AuthContext = createContext({ authData: undefined, ready: false });







// -----------------------------------------------------------
// useAuth
// -----------------------------------------------------------

export function useAuth() {
  return useContext(AuthContext);
}







// -----------------------------------------------------------
// AuthProvider
// -----------------------------------------------------------

export function AuthProvider({ children }) {

  // A 401 (no/expired session) is the normal anonymous case,
  // not an error to surface
  const { data, isPending } = useQuery({
    queryKey: ['checkauth'],
    queryFn: async () => (await axios.get('/api/checkauth', { withCredentials: true })).data,
    staleTime: Infinity,
    retry: false,
  });

  const value = useMemo(() => ({
    authData: data,
    ready: !isPending,
  }), [data, isPending]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
