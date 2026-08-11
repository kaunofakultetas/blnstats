// -----------------------------------------------------------
//  [*] MUI theme — light and dark color schemes
//
//  One theme per scheme; providers.jsx owns which one is live.
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
//  Dark mode is fully defined but unreachable: no theme
//  switcher is mounted. The /login page renders OUTSIDE the
//  ThemeProvider (App.jsx) and keeps its hardcoded colors.
//
//  Used by:
//    - providers.jsx — rebuilt whenever the mode changes
// -----------------------------------------------------------

import { createTheme } from '@mui/material/styles';
import { green, grey, purple } from '@mui/material/colors';


// Keep in sync with the body rule in globals.css. MUI otherwise
// defaults to a Roboto stack that nothing loads, leaving its
// components in Helvetica while the rest of the app is Inter.
const FONT_STACK = "'Inter', Arial, Helvetica, sans-serif";


const getTheme = (mode) => createTheme({
  typography: {
    fontFamily: FONT_STACK,
  },

  palette: {
    mode,
    ...(mode === 'light' ? {
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
      } : {
        primary: {
          main: '#ffffff',
          accent: green[500]
        },
        secondary: {
          main: purple[300]
        },
        background: {
          default: '#121212',
          paper: '#121212'
        }
      }
    ),
  }
});

export default getTheme;
