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
//  The admin field is decoration for now: the backend
//  hardcodes it to 1 (api/auth/routes.py ignores
//  current_user.admin) and no frontend code reads it — every
//  consumer only checks that authData exists.
//
//  Used by:
//    - App.jsx — AuthProvider wraps every page except /login
//    - Header — Login/Logout button and the Admin nav item
//    - AdminPageLayout — the admin-only gate
// -----------------------------------------------------------

import { createContext, useContext, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';


// The default a consumer sees OUTSIDE AuthProvider —
// anonymous and never becoming ready
const AuthContext = createContext({ authData: undefined, ready: false });







// -----------------------------------------------------------
// useAuth
// -----------------------------------------------------------
//
// Read access to the session: { authData, ready }. Outside
// AuthProvider the context default applies — anonymous and
// never ready — rather than a crash.
//
// Used by:
//   - Header — Login/Logout button and the Admin nav item
//   - AdminPageLayout — the admin-only gate
// -----------------------------------------------------------

export function useAuth() {
  return useContext(AuthContext);
}







// -----------------------------------------------------------
// AuthProvider
// -----------------------------------------------------------
//
// Runs the one checkauth query and publishes { authData,
// ready } through context, memoized so consumers re-render
// only when the session answer itself changes.
//
// Used by:
//   - App.jsx — wraps every page except /login
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
