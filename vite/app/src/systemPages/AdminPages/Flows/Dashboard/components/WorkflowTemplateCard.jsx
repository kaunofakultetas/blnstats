// -----------------------------------------------------------
//  [*] WorkflowTemplateCard — one Prefect deployment
//
//  Run Now is hold-to-confirm: it launches a real pipeline (a
//  blockchain sync, a full statistics rebuild), so a stray
//  click must not start one.
//
//  Schedule and the settings button are decoration — no
//  handlers yet. Duration and Last Run stay hidden until the
//  values exist: Prefect reports no duration estimate, and an
//  untouched deployment has no update timestamp.
//
//  Used by:
//    - WorkflowTemplates — one card per deployment
// -----------------------------------------------------------

import {
  Box,
  Button,
  Card,
  CardContent,
  Typography
} from '@mui/material';

import { LongPressButton } from '@/components/LongPressButton';


export default function WorkflowTemplateCard({ template, triggerWorkflow }) {
  return (
    <Card className="h-full">
      <CardContent className="flex flex-col h-full">
        <Typography variant="h6" className="mb-2">
          📊 {template.name}
        </Typography>
        <Typography variant="body2" color="textSecondary" className="mb-3 flex-1">
          {template.description}
        </Typography>

        <Box className="mb-3">
          {template.estimatedDuration && (
            <Typography variant="caption" color="textSecondary" component="div">
              ⏱️ Duration: {template.estimatedDuration}
            </Typography>
          )}
          {template.lastRun && (
            <Typography variant="caption" color="textSecondary" component="div">
              🕒 Last Run: {template.lastRun}
            </Typography>
          )}
        </Box>

        <Box className="flex gap-2">
          <LongPressButton
            color="primary"
            size="small"
            sx={{ flex: 1 }}
            progressSize={20}
            onComplete={() => triggerWorkflow(template.id)}
            uncompletedToastMessage="Hold the button to start the workflow"
          >
            ▶️ Run Now
          </LongPressButton>
          <Button
            variant="outlined"
            size="small"
          >
            📅 Schedule
          </Button>
          <Button
            variant="outlined"
            size="small"
          >
            ⚙️
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}
