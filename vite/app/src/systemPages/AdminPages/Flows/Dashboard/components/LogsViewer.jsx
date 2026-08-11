// -----------------------------------------------------------
//  [*] LogsViewer — the pipeline log panel
//
//  Dormant: no tab on FlowsDashboard mounts it, and the lines
//  below are hardcoded sample output, not live logs. Prefect
//  serves the real ones at /prefect/api/logs/filter, which is
//  what wiring this panel up would query.
//
//  Used by:
//    - nothing yet — see above
// -----------------------------------------------------------

import { Box, Paper, Typography } from '@mui/material';


export default function LogsViewer() {
  return (
    <Box>
      <Typography variant="h6" className="mb-4">Recent Logs</Typography>
      <Paper className="p-4 bg-gray-900 text-green-400 font-mono text-sm max-h-96 overflow-y-auto">
        <div>[2024-01-15 14:30:15] INFO: Starting Lightning Network Analytics Pipeline</div>
        <div>[2024-01-15 14:30:16] INFO: Task 'transform-node-metrics' started</div>
        <div>[2024-01-15 14:32:50] INFO: Task 'transform-node-metrics' completed in 2m 34s</div>
        <div>[2024-01-15 14:32:51] INFO: Task 'generate-general-stats' started</div>
        <div>[2024-01-15 14:33:45] INFO: Processing 15.2M blocks for statistics generation</div>
        <div>[2024-01-15 14:34:20] INFO: Generated capacity distribution charts</div>
        <div>[2024-01-15 14:34:55] INFO: Generated node count evolution charts</div>
        <div>[2024-01-15 14:35:30] WARN: High memory usage detected: 85%</div>
        <div>[2024-01-15 14:36:10] INFO: Completed coefficient calculations for Nodes</div>
        <div>[2024-01-15 14:36:45] INFO: Starting Entities coefficient calculations...</div>
      </Paper>
    </Box>
  );
}
