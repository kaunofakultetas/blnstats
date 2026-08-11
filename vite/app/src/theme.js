// -----------------------------------------------------------
//  [*] MUI theme — the single light scheme
//
//  Palette notes:
//    - primary.main is the brand burgundy #7B003F, mirrored in
//      globals.css as the Tailwind `primary` token. Keep the
//      two in sync.
//    - primary.accent is NOT a standard MUI palette slot: an
//      extra key the charts read for their gradient and
//      tooltip highlight.
//    - cssVariables is deliberately left off so palette values
//      stay plain hex strings — recharts and d3 write them
//      into SVG attributes, where a var(--mui-*) reference
//      would not resolve.
//
//  There is no dark mode by decision (2026-08-11) — the app
//  always runs this one light theme. The /login page renders
//  OUTSIDE the ThemeProvider (App.jsx) and keeps its own
//  hardcoded colors.
//
//  Used by:
//    - providers.jsx — passed to the ThemeProvider once
// -----------------------------------------------------------

import { createTheme } from '@mui/material/styles';
import { grey } from '@mui/material/colors';


// Keep in sync with the body rule in globals.css. MUI otherwise
// defaults to a Roboto stack that nothing loads, leaving its
// components in Helvetica while the rest of the app is Inter.
const FONT_STACK = "'Inter', Arial, Helvetica, sans-serif";


const theme = createTheme({
  typography: {
    fontFamily: FONT_STACK,
  },

  palette: {
    primary: {
      main: '#7b003f',
      accent: '#E64164'
    },
    secondary: {
      main: grey[50]
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff'
    },
  }
});

export default theme;
