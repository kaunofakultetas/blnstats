// -----------------------------------------------------------
//  [*] DataGrid custom components — QuickSearchToolbar
//
//  The shared DataGrid toolbar shell: an always-expanded quick
//  filter, the columns button, the burgundy "add new" button
//  when onAddNew is given, then page-specific children in the
//  same row.
//
//  Built on DataGrid v8's composable QuickFilter parts. Grids
//  mounting it must also pass showToolbar — in v8 the toolbar
//  slot renders only when that flag is set. onAddNew receives
//  the click event, so a dialog can fly out of the button.
//
//  Used by:
//    - AdministratorsListTable — the toolbar slot
// -----------------------------------------------------------

import { QuickFilter, QuickFilterClear, QuickFilterControl } from "@mui/x-data-grid";
import { Box, InputAdornment, TextField } from '@mui/material';

import AddCircleOutlinedIcon from '@mui/icons-material/AddCircleOutlined';
import CancelIcon from '@mui/icons-material/Cancel';
import SearchIcon from '@mui/icons-material/Search';

import ColumnsButton from '@/components/DatagridCustomComponents/ColumnsButton';
import ToolbarButton from '@/components/DatagridCustomComponents/ToolbarButton';


export default function QuickSearchToolbar({ placeholder = "Search...", columnsLabel, addNewLabel = "Add new", onAddNew, children }) {
  return (
    <Box sx={{ margin: 1, display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
      <QuickFilter>
        <QuickFilterControl
          render={({ ref, ...other }) => (
            <TextField
              {...other}
              sx={{ width: 260 }}
              inputRef={ref}
              size="small"
              aria-label="Search"
              placeholder={placeholder}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                  endAdornment: other.value ? (
                    <InputAdornment position="end">
                      <QuickFilterClear
                        edge="end"
                        size="small"
                        aria-label="Clear search"
                        material={{ sx: { marginRight: -0.75 } }}
                      >
                        <CancelIcon fontSize="small" />
                      </QuickFilterClear>
                    </InputAdornment>
                  ) : null,
                  ...other.slotProps?.input,
                },
                ...other.slotProps,
              }}
            />
          )}
        />
      </QuickFilter>

      {/* Passed even when undefined, so callers without a
          custom label fall back to the button's own default */}
      <ColumnsButton label={columnsLabel} />

      {onAddNew && (
        <ToolbarButton
          label={addNewLabel}
          icon={AddCircleOutlinedIcon}
          onClick={onAddNew}
        />
      )}

      {children}
    </Box>
  );
}
