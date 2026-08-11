// -----------------------------------------------------------
//  [*] ActiveWorkflows — the runs panel of the dashboard
//
//  Despite the name it lists every recent flow run, not only
//  the running ones — the panel header above it counts those.
//
//  Used by:
//    - FlowsDashboard — the runs panel under the cards
// -----------------------------------------------------------

import { Box } from '@mui/material';

import WorkflowRunCard from './WorkflowRunCard';







// -----------------------------------------------------------
// ActiveWorkflows (default export)
// -----------------------------------------------------------
//
// One WorkflowRunCard per run, or a grey "No active
// workflows" placeholder when the list is empty.
//
// Used by:
//   - FlowsDashboard — the runs panel under the cards
// -----------------------------------------------------------

export default function ActiveWorkflows({ workflowRuns }) {
  return (
    <Box className="space-y-4">
      {workflowRuns.length === 0 ? (
        <Box className="text-center py-8 text-gray-500">
          No active workflows
        </Box>
      ) : (
        workflowRuns.map((run) => (
          <WorkflowRunCard
            key={run.id}
            run={run}
          />
        ))
      )}
    </Box>
  );
}
