// -----------------------------------------------------------
//  [*] WorkflowTemplates — the "Templates" tab body
//
//  The Prefect deployments as a card grid.
//
//  Used by:
//    - FlowsDashboard — the second tab
// -----------------------------------------------------------

import { Box, Grid, Typography } from '@mui/material';

import WorkflowTemplateCard from './WorkflowTemplateCard';


export default function WorkflowTemplates({ workflowTemplates, triggerWorkflow }) {
  return (
    <Box>
      <Typography variant="h6" className="mb-4">Workflow Templates</Typography>

      <Grid container spacing={3}>
        {workflowTemplates.map((template) => (
          <Grid key={template.id} size={{ xs: 12, md: 6, lg: 4 }}>
            <WorkflowTemplateCard
              template={template}
              triggerWorkflow={triggerWorkflow}
            />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
