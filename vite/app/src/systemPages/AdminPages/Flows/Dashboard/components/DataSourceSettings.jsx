// -----------------------------------------------------------
//  [*] DataSourceSettings — the DBReader dump URL card
//
//  Reads and writes the one System_Settings key the Prefect
//  import flows resolve their LND DBReader dump from
//  ('LND-DBReader-Source-1'). GET /api/settings loads the
//  current value into the field; Save POSTs it back. Both
//  DBReader-importing flows pick up the new URL on their
//  next run — the next scheduled one being the 1st of every
//  month at 04:00 (stated in the helper text; keep in sync
//  with the Cron in backend/workflows.py).
//
//  The field seeds from the fetched value exactly once (an
//  uncontrolled default), so typing is never clobbered by a
//  background refetch. Editing shows an "Unsaved changes"
//  chip and a Reset button; Save stays disabled until the
//  text differs from the loaded value AND looks like an
//  http(s) URL, and a successful save refetches the settings
//  so the button disables again on the new baseline. A
//  failed load unlocks the empty field instead of bricking
//  it — the URL can still be set by hand.
//
//  Used by:
//    - FlowsDashboard — below Quick Actions
// -----------------------------------------------------------

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import toast from 'react-hot-toast';

import {
  Button,
  Card,
  CardContent,
  Chip,
  InputAdornment,
  TextField,
  Typography
} from '@mui/material';

import StorageIcon from '@mui/icons-material/Storage';
import LinkIcon from '@mui/icons-material/Link';


// The System_Settings key edited here — must match
// DBREADER_SOURCE_KEY in backend/workflows.py
const SOURCE_KEY = 'LND-DBReader-Source-1';







// -----------------------------------------------------------
// DataSourceSettings (default export)
// -----------------------------------------------------------
//
// The card itself: a loading query seeds the field once, a
// mutation saves it (toasting the outcome and refetching the
// baseline), and the dirty state drives the chip, the Reset
// button and the Save gate.
//
// Used by:
//   - FlowsDashboard — below Quick Actions
// -----------------------------------------------------------

export default function DataSourceSettings() {

  // null until the settings load — the field renders disabled
  // with a placeholder while it is null, then seeds once
  const [value, setValue] = useState(null);
  const queryClient = useQueryClient();


  const { data: loadedValue = '', isPending, error: loadError } = useQuery({
    queryKey: ['system-settings', SOURCE_KEY],
    queryFn: async () => {
      const settings = (await axios.get('/api/settings', { withCredentials: true })).data;
      const url = settings[SOURCE_KEY] || '';
      // seed the field the first time the value arrives
      setValue((current) => (current === null ? url : current));
      return url;
    },
  });


  const saveMutation = useMutation({
    mutationFn: (url) => axios.post('/api/settings', { [SOURCE_KEY]: url }, { withCredentials: true }),
    onSuccess: (response) => {
      if (response.data?.type === 'ok') {
        toast.success('Data source saved');
        // refresh the baseline so the dirty state clears on
        // the just-saved value
        queryClient.invalidateQueries({ queryKey: ['system-settings', SOURCE_KEY] });
      } else {
        toast.error(response.data?.reason || 'Could not save data source');
      }
    },
    onError: (error) => {
      toast.error(`Could not save data source: ${error.response?.data?.reason || error.message}`);
    },
  });


  // The three states the controls hang off: dirty (differs
  // from the loaded baseline), a plausible URL, and saving
  const current = value ?? '';
  const trimmed = current.trim();
  const dirty = value !== null && trimmed !== loadedValue;
  const validUrl = /^https?:\/\/.+/.test(trimmed);


  return (
    <Card className="mb-6">
      <CardContent>

        <div className="flex items-center gap-2 mb-4">
          <StorageIcon fontSize="small" style={{ color: 'rgb(123, 0, 63)' }} />
          <Typography variant="h6">Data Source</Typography>
          {dirty && (
            <Chip label="Unsaved changes" size="small" color="warning" variant="outlined" className="ml-auto" />
          )}
        </div>

        {/* One text layer only: the label names the field, the
            helper line carries purpose + schedule — no extra
            paragraph crowding the floating label */}
        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-start">

          {/* A failed load unlocks the empty field — the URL
              can still be typed in and saved by hand */}
          <TextField
            fullWidth
            size="small"
            label="DBReader dump URL"
            placeholder={
              isPending ? 'Loading...'
                : loadError ? 'Could not load the current value — enter the URL manually'
                : 'https://.../lnd-dbreader-...json.gz'
            }
            value={current}
            disabled={value === null && !loadError}
            onChange={(e) => setValue(e.target.value)}
            error={trimmed !== '' && !validUrl}
            helperText={
              trimmed !== '' && !validUrl
                ? 'The URL must start with http:// or https://'
                : 'The dump URL both import flows download from — the scheduled update runs on the 1st of every month at 04:00.'
            }
            slotProps={{
              input: {
                className: 'font-mono text-sm',
                startAdornment: (
                  <InputAdornment position="start">
                    <LinkIcon fontSize="small" />
                  </InputAdornment>
                ),
              },
            }}
          />

          {/* h-10 matches the small TextField, so the buttons
              line up with the input row, not the helper line */}
          <div className="flex gap-2 shrink-0">
            {dirty && (
              <Button
                variant="outlined"
                color="inherit"
                onClick={() => setValue(loadedValue)}
                className="h-10 whitespace-nowrap"
              >
                Reset
              </Button>
            )}
            <Button
              variant="contained"
              color="primary"
              disabled={!dirty || !validUrl || saveMutation.isPending}
              onClick={() => saveMutation.mutate(trimmed)}
              className="h-10 whitespace-nowrap"
            >
              {saveMutation.isPending ? 'Saving...' : 'Save'}
            </Button>
          </div>

        </div>

      </CardContent>
    </Card>
  );
}
