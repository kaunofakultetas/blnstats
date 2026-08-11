// -----------------------------------------------------------
//  [*] App — the root layout route
//
//  Every page renders through its outlet, wrapped in the
//  theme provider (providers.jsx) and AuthProvider. The page
//  frames live a level deeper, in the two layout routes, so
//  each mounts once and survives navigation in its section.
//
//  StyledEngineProvider injectFirst puts the MUI (emotion)
//  styles BEFORE the Tailwind stylesheet in <head>, so
//  Tailwind utilities win where the pages mix both systems.
//
//  /login is the exception: bare outlet, no theme (it
//  hardcodes its own colors) and no auth context — the page
//  IS the logout, so checking the session there is pointless.
//
//  Used by:
//    - router.jsx — element of the "/" layout route
// -----------------------------------------------------------

import { useLocation, useOutlet } from 'react-router-dom';
import { StyledEngineProvider } from '@mui/material/styles';
import Providers from '@/providers';
import { AuthProvider } from '@/AuthGuard';







// -----------------------------------------------------------
// App (default export)
// -----------------------------------------------------------
//
// Chooses between the bare /login outlet and the fully
// wrapped tree — theme, auth context and emotion-first style
// injection; the page frames live in the layout routes below.
//
// Used by:
//   - router.jsx — element of the "/" layout route
// -----------------------------------------------------------

export default function App() {

  const { pathname } = useLocation();
  const outlet = useOutlet();

  // Login skips every provider (see the file header)
  if (pathname === '/login') {
    return outlet;
  }

  return (
    <StyledEngineProvider injectFirst>
      <Providers>
        <AuthProvider>
          {outlet}
        </AuthProvider>
      </Providers>
    </StyledEngineProvider>
  );
}
