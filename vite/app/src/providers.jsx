// -----------------------------------------------------------
//  [*] Providers — MUI theme + color mode
//
//  Wraps the app in the MUI ThemeProvider and exposes the
//  light/dark switch through ColorModeContext, persisted in
//  localStorage under "theme-mode". The stored mode is read in
//  the state initializer, before the first paint, so the app
//  never flashes the wrong scheme.
//
//  Nothing calls toggleColorMode today — no theme switcher is
//  mounted — so the app always runs light. The context stays
//  so adding one is a one-component change.
//
//  Used by:
//    - App.jsx — wraps every page except /login
// -----------------------------------------------------------

import { createContext, useMemo, useState } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import getTheme from '@/theme';


const STORAGE_KEY = 'theme-mode';


export const ColorModeContext = createContext({
  mode: 'light',
  toggleColorMode: () => {},
});







// -----------------------------------------------------------
// readStoredMode
// -----------------------------------------------------------
//
// Storage access is try/catch-guarded: private browsing modes
// can throw on it, and the app must still render — it just
// forgets the remembered choice.
// -----------------------------------------------------------

function readStoredMode() {
  try {
    const savedMode = localStorage.getItem(STORAGE_KEY);
    return savedMode === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}







export default function Providers({ children }) {

  const [mode, setMode] = useState(readStoredMode);

  const colorMode = useMemo(() => ({
    mode,
    toggleColorMode: () => {
      const newMode = mode === 'light' ? 'dark' : 'light';
      setMode(newMode);
      try {
        localStorage.setItem(STORAGE_KEY, newMode);
      } catch { /* storage unavailable — the toggle still works */ }
    },
  }), [mode]);

  const theme = useMemo(() => getTheme(mode), [mode]);

  return (
    <ColorModeContext.Provider value={colorMode}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}
