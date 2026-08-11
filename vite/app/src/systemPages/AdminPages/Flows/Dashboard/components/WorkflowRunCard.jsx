// -----------------------------------------------------------
//  [*] WorkflowRunCard — one flow run on the dashboard
//
//  Header, then the run's items: plain tasks, and subflows as
//  expandable groups holding their own tasks. "View in
//  Prefect" is a plain anchor: the Prefect UI is a separate
//  service behind the same domain, not a route of this app.
//
//  Split into (root component last):
//
//    getStatusColor  — status → MUI chip color
//    getStatusEmoji  — status → the emoji in front of a row
//    TaskItem        — one task row
//    SubflowItem     — one collapsible subflow group
//    WorkflowRunCard — the card (default export)
//
//  Used by:
//    - ActiveWorkflows — one card per run
// -----------------------------------------------------------

import { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Typography
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';







// -----------------------------------------------------------
// getStatusColor / getStatusEmoji
// -----------------------------------------------------------
//
// The statuses are the ones mapPrefectStateToStatus produces.
// -----------------------------------------------------------

const getStatusColor = (status) => {
  switch (status) {
    case 'completed': return 'success';
    case 'running': return 'primary';
    case 'pending': return 'default';
    case 'failed': return 'error';
    case 'stopped': return 'warning';
    default: return 'default';
  }
};

const getStatusEmoji = (status) => {
  switch (status) {
    case 'completed': return '✅';
    case 'running': return '🔄';
    case 'pending': return '⏳';
    case 'failed': return '❌';
    case 'stopped': return '⏹️';
    default: return '⏳';
  }
};







// -----------------------------------------------------------
// TaskItem
// -----------------------------------------------------------

function TaskItem({ item }) {
  return (
    <Box className="flex items-center gap-2">
      <span>{getStatusEmoji(item.status)}</span>
      <span>{item.name}</span>
      {item.duration && (
        <Chip label={item.duration} size="small" variant="outlined" />
      )}
    </Box>
  );
}







// -----------------------------------------------------------
// SubflowItem
// -----------------------------------------------------------
//
// Expanded by default so a running pipeline shows its progress
// without a click.
// -----------------------------------------------------------

function SubflowItem({ item }) {

  const [open, setOpen] = useState(true);

  return (
    <Box className="w-full">
      <Box className="flex items-center">
        <Box className="flex items-center gap-2 flex-grow">
          <span>{getStatusEmoji(item.status)}</span>
          <span className="font-semibold">{item.name}</span>
          {item.duration && (
            <Chip label={item.duration} size="small" variant="outlined" color={getStatusColor(item.status)} />
          )}
        </Box>
        <IconButton aria-label="expand row" size="small" onClick={() => setOpen(!open)}>
          {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
        </IconButton>
      </Box>

      <Collapse in={open} timeout="auto" unmountOnExit>
        <Box className="pl-6 border-l-2 border-gray-300">
          <List dense>
            {item.tasks.map((task) => (
              <ListItem key={task.id} className="pl-2">
                <ListItemText primary={<TaskItem item={task} />} />
              </ListItem>
            ))}
          </List>
        </Box>
      </Collapse>
    </Box>
  );
}







// -----------------------------------------------------------
// WorkflowRunCard (default export)
// -----------------------------------------------------------

export default function WorkflowRunCard({ run }) {
  return (
    <Box className="w-full border-2 border-gray-200 rounded-md">
      <Card>
        <CardContent>
          <Box className="flex justify-between items-start mb-3">
            <Box>
              <Typography variant="h6" className="flex items-center gap-4">
                <div>{getStatusEmoji(run.status)}</div>
                <div>{run.name}</div>
                <Chip label={run.status} color={getStatusColor(run.status)} size="small" />
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Started: {run.startTime}
              </Typography>
            </Box>
            <Box className="flex gap-1">
              <Button
                component="a"
                href={`/prefect/flow-runs/flow-run/${run.id}`}
                target="_blank"
                rel="noopener noreferrer"
                size="small"
                variant="outlined"
              >
                View in Prefect
              </Button>
            </Box>
          </Box>

          <Divider className="my-3" />

          {run.tasks && run.tasks.length > 0 && (
            <Box>
              <Typography variant="subtitle2" className="mb-2">Tasks:</Typography>
              <List dense>
                {run.tasks.map((item) => (
                  <ListItem key={item.id} className="pl-0">
                    {item.type === 'subflow'
                      ? <SubflowItem item={item} />
                      : <TaskItem item={item} />
                    }
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
