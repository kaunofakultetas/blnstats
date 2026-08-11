// -----------------------------------------------------------
//  [*] QuickActions — the shortcut card of the dashboard
//
//  Buttons that start pipelines without the Templates tab.
//  They hold deployment names, not ids: the names are known
//  ahead of time while Prefect assigns the UUIDs at serve
//  time, and triggerWorkflow resolves either. The names in
//  ACTIONS must match backend/workflows.py,
//  `to_deployment(name=...)`.
//
//  A button whose deployment is not being served is disabled
//  with a tooltip, so a missing worker shows before the click
//  rather than as a failed toast after it.
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
import AssessmentIcon from '@mui/icons-material/Assessment';







// -----------------------------------------------------------
// ACTIONS
// -----------------------------------------------------------
//
// Ordered heaviest first: full initialization re-imports both
// sources and recalculates everything, the update flow
// re-imports one source, the analysis flow only recalculates.
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
  },
  {
    deployment: 'LND DBReader Full Update Flow',
    label: 'Update From DBReader',
    icon: SyncIcon,
    variant: 'outlined',
  },
  {
    deployment: 'BLN Analysis Flow',
    label: 'Recalculate Statistics',
    icon: AssessmentIcon,
    variant: 'outlined',
  },
];







// -----------------------------------------------------------
// QuickActions (default export)
// -----------------------------------------------------------
//
// The "Quick Actions" card: one trigger button per ACTIONS
// entry, disabled with an explanatory tooltip when its
// deployment is not among the served names.
//
// Used by:
//   - FlowsDashboard — above the tabs
// -----------------------------------------------------------

export default function QuickActions({ triggerWorkflow, deploymentNames = [] }) {
  return (
    <Card className="mb-6">
      <CardContent>
        <Typography variant="h6" className="mb-3">
          Quick Actions
        </Typography>

        <Grid container spacing={2}>
          {ACTIONS.map(({ deployment, label, icon: Icon, variant }) => {
            const available = deploymentNames.includes(deployment);

            return (
              <Grid key={deployment} size={{ xs: 12, sm: 6, md: 4 }}>
                {/* The tooltip needs a wrapper span: a disabled
                    button fires no hover events of its own */}
                <Tooltip title={available ? deployment : `${deployment} is not being served`}>
                  <span className="block">
                    <Button
                      variant={variant}
                      color="primary"
                      fullWidth
                      disabled={!available}
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
