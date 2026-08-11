// -----------------------------------------------------------
//  [*] DataGrid custom components — ColumnsButton
//
//  Toolbar button that toggles the grid's built-in column
//  visibility panel, styled to match the rest of the toolbar
//  rather than the stock GridToolbarColumnsButton. The panel
//  state is tracked locally so a second click closes the panel
//  instead of reopening it.
//
//  Must be rendered inside a DataGrid toolbar slot — it
//  reaches the grid through useGridApiContext.
//
//  Used by:
//    - QuickSearchToolbar — next to the quick filter
// -----------------------------------------------------------

import { useState } from 'react';
import { GridPreferencePanelsValue, useGridApiContext } from '@mui/x-data-grid';
import { Button } from '@mui/material';
import ViewColumnIcon from '@mui/icons-material/ViewColumn';







// -----------------------------------------------------------
// ColumnsButton (default export)
// -----------------------------------------------------------
//
// The brand-styled panel toggle: opens the grid's columns
// panel through the api ref and tracks the open state
// locally, so a second click closes instead of reopening.
//
// Used by:
//   - QuickSearchToolbar — next to the quick filter
// -----------------------------------------------------------

export default function ColumnsButton({ label = "Columns" }) {

  const apiRef = useGridApiContext();
  const [panelOpen, setPanelOpen] = useState(false);

  return (
    <Button
      variant="contained"
      startIcon={<ViewColumnIcon />}
      onClick={() => {
        if (panelOpen) {
          apiRef.current.hidePreferences();
          setPanelOpen(false);
        } else {
          apiRef.current.showPreferences(GridPreferencePanelsValue.columns);
          setPanelOpen(true);
        }
      }}
      sx={{
        marginLeft: '10px',
        height: 40,
        backgroundColor: 'primary.main',
        color: 'white',
        '&:hover': {
          backgroundColor: 'primary.accent',
        },
      }}
    >
      {label}
    </Button>
  );
}
