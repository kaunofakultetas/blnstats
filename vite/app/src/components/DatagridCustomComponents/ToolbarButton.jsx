// -----------------------------------------------------------
//  [*] DataGrid custom components — ToolbarButton
//
//  Generic action button for DataGrid toolbars, with no grid
//  logic of its own. The click event is handed through, so a
//  caller can read e.currentTarget.getBoundingClientRect()
//  and fly a dialog out of the button.
//
//  The 40px height matches the small TextField of the quick
//  filter so the toolbar row lines up. Hover goes to
//  primary.accent — the brand pink Tailwind's bg-primary-dark
//  also paints — not MUI's darken() of the burgundy, which
//  reads as almost black.
//
//  Used by:
//    - QuickSearchToolbar — the "add new" button
// -----------------------------------------------------------

import { Button } from '@mui/material';


export default function ToolbarButton({ onClick, label, icon: Icon }) {
  return (
    <Button
      variant="contained"
      sx={{
        marginLeft: '10px',
        paddingLeft: '15px',
        paddingRight: '15px',
        fontSize: '14px',
        height: 40,
        backgroundColor: 'primary.main',
        color: 'white',
        '&:hover': {
          backgroundColor: 'primary.accent',
        },
      }}
      onClick={onClick}
    >
      {Icon && <Icon style={{ paddingRight: 8, fontSize: '22px' }} />}
      {label}
    </Button>
  );
}
