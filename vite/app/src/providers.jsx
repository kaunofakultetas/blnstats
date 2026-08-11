// -----------------------------------------------------------
//  [*] Providers — the MUI theme wrapper
//
//  Wraps the app in the MUI ThemeProvider with the single
//  light theme plus CssBaseline. There is no color-mode
//  state: dark mode was removed by decision (2026-08-11). A
//  "theme-mode" key may linger in old visitors' localStorage
//  from the removed switcher — nothing reads it anymore.
//
//  Used by:
//    - App.jsx — wraps every page except /login
// -----------------------------------------------------------

import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import theme from '@/theme';







// -----------------------------------------------------------
// Providers (default export)
// -----------------------------------------------------------
//
// A static composition — the theme never changes at runtime,
// so there is no state to own and nothing above the children
// ever re-renders.
//
// Used by:
//   - App.jsx — wraps every page except /login
// -----------------------------------------------------------

export default function Providers({ children }) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}
