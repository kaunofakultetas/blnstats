// -----------------------------------------------------------
//  [*] QuickActions — the launch buttons of the dashboard
//
//  The only way to start pipelines from the UI. The buttons
//  hold deployment names, not ids: the names are known ahead
//  of time while Prefect assigns the UUIDs at serve time,
//  and triggerWorkflow resolves either. The names in ACTIONS
//  must match backend/workflows.py, `to_deployment(name=...)`.
//
//  A button whose deployment is not being served is disabled
//  with a tooltip, so a missing worker shows before the click
//  rather than as a failed toast after it. The one-time
//  full-initialization button additionally greys out once
//  InitialSyncCompleted is '1' — the LNResearch archive only
//  needs importing once per database.
//
//  Used by:
//    - FlowsDashboard — above the tabs
// -----------------------------------------------------------

import {
  Button,
  Card,
  CardContent,
  Grid,
  Tooltip,
  Typography
} from '@mui/material';

import PlayCircleFilledIcon from '@mui/icons-material/PlayCircleFilled';
import SyncIcon from '@mui/icons-material/Sync';







// -----------------------------------------------------------
// ACTIONS
// -----------------------------------------------------------
//
// Ordered heaviest first: full initialization re-imports both
// sources and recalculates everything (oneTimeOnly — greyed
// out after its first success), the update flow re-imports
// the DBReader dump and recalculates. The former separate
// "Recalculate Statistics" action was removed 2026-08: the
// analysis pipeline runs inside both flows anyway.
//
// Used by:
//   - QuickActions (below)
// -----------------------------------------------------------

const ACTIONS = [
  {
    deployment: 'Full Initialization Flow',
    label: 'Run Full Pipeline',
    icon: PlayCircleFilledIcon,
    variant: 'contained',
    oneTimeOnly: true,
  },
  {
    deployment: 'LND DBReader Full Update Flow',
    label: 'Update From DBReader',
    icon: SyncIcon,
    variant: 'outlined',
  },
];







// -----------------------------------------------------------
// QuickActions (default export)
// -----------------------------------------------------------
//
// The "Quick Actions" card: one trigger button per ACTIONS
// entry, disabled with an explanatory tooltip when its
// deployment is not among the served names — or, for the
// oneTimeOnly action, when the initialization already
// happened.
//
// Used by:
//   - FlowsDashboard — above the runs panel
// -----------------------------------------------------------

export default function QuickActions({ triggerWorkflow, deploymentNames = [], initialSyncCompleted = false }) {
  return (
    <Card className="mb-6">
      <CardContent>
        <Typography variant="h6" className="mb-3">
          Quick Actions
        </Typography>

        <Grid container spacing={2}>
          {ACTIONS.map(({ deployment, label, icon: Icon, variant, oneTimeOnly }) => {
            const available = deploymentNames.includes(deployment);
            const alreadyInitialized = oneTimeOnly && initialSyncCompleted;

            const tooltip = !available
              ? `${deployment} is not being served`
              : alreadyInitialized
                ? 'Already initialized — the LNResearch archive imports once; use "Update From DBReader" for refreshes'
                : deployment;

            return (
              <Grid key={deployment} size={{ xs: 12, sm: 6 }}>
                {/* The tooltip needs a wrapper span: a disabled
                    button fires no hover events of its own */}
                <Tooltip title={tooltip}>
                  <span className="block">
                    <Button
                      variant={variant}
                      color="primary"
                      fullWidth
                      disabled={!available || alreadyInitialized}
                      onClick={() => triggerWorkflow(deployment)}
                      className="h-12"
                    >
                      <Icon className="mr-2" /> {label}
                    </Button>
                  </span>
                </Tooltip>
              </Grid>
            );
          })}
        </Grid>
      </CardContent>
    </Card>
  );
}
