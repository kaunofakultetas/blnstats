// -----------------------------------------------------------
//  [*] FlowsDashboard — the /admin workflow dashboard
//
//  Talks straight to the Prefect API: Caddy proxies
//  /prefect/api/* to the Prefect server behind a session
//  check, so these are same-origin cookie requests.
//
//  Deployments are fetched once and double as the Templates
//  tab. The run tree polls every 10 s and waits on them,
//  because a run is labelled with its deployment's name when
//  it has one; a deployments failure only costs that label.
//  A failed poll leaves the last good tree on screen.
//
//  Split into (root component last):
//
//    calculateDuration      — start/end → "2m", "1.5h", ...
//    mapPrefectStateToStatus — Prefect state → our vocabulary
//    processFlowRunData     — runs + flows + tasks → the tree
//    fetchFlowRuns          — the three POSTs behind the tree
//    FlowsDashboard         — the page body (default export)
//
//  Used by:
//    - Flows.jsx — the /admin page body
// -----------------------------------------------------------

import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axios from "axios";
import toast from 'react-hot-toast';
import {
  Alert,
  Box,
  Paper,
  Tab,
  Tabs
} from '@mui/material';

import PageTitle from '@/components/PageTitle/PageTitle';
import PageLoading from '@/components/PageLoading/PageLoading';
import QuickActions from './components/QuickActions';
import ActiveWorkflows from './components/ActiveWorkflows';
import WorkflowTemplates from './components/WorkflowTemplates';


// Every Prefect filter endpoint is a POST with a JSON body;
// the cookie is what the endpoint's forward_auth checks
const PREFECT_POST_CONFIG = {
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
};

const RUNS_POLL_INTERVAL_MS = 10000;

// Prefect needs a moment to register a new flow run before it
// shows up in a filter query
const TRIGGER_REFRESH_DELAY_MS = 1500;







// -----------------------------------------------------------
// calculateDuration
// -----------------------------------------------------------
//
// The largest unit that still reads well. A run still going
// is measured against now.
//
// Used by:
//   - processFlowRunData (below)
// -----------------------------------------------------------

const calculateDuration = (startTime, endTime, status) => {
  if (!startTime) return null;
  const start = new Date(startTime);
  const end = endTime ? new Date(endTime) : new Date();
  if (status !== 'completed' && status !== 'running') return null;
  const durationMs = end - start;
  if (durationMs < 1000) return `${durationMs}ms`;
  if (durationMs < 60000) return `${Math.round(durationMs / 1000)}s`;
  if (durationMs < 3600000) return `${Math.round(durationMs / 60000)}m`;
  return `${(durationMs / 3600000).toFixed(1)}h`;
};







// -----------------------------------------------------------
// mapPrefectStateToStatus
// -----------------------------------------------------------
//
// Prefect's state types collapsed into the five the cards
// know how to color: completed, running, pending, failed,
// stopped.
//
// Used by:
//   - processFlowRunData (below)
// -----------------------------------------------------------

const mapPrefectStateToStatus = (stateType) => {
  switch (stateType?.toLowerCase()) {
    case 'completed': return 'completed';
    case 'running': return 'running';
    case 'pending': case 'scheduled': return 'pending';
    case 'failed': return 'failed';
    case 'cancelled': case 'canceled': return 'stopped';
    default: return 'pending';
  }
};







// -----------------------------------------------------------
// processFlowRunData
// -----------------------------------------------------------
//
// Folds the three flat Prefect lists into one tree per
// top-level run. Prefect models a subflow as a task run in
// the parent whose id shows up as another flow run's
// parent_task_run_id — such a task is replaced by that
// subflow and its own tasks, giving the cards their groups.
//
// Used by:
//   - fetchFlowRuns (below)
// -----------------------------------------------------------

const processFlowRunData = (runs, flows, tasks, deployments) => {

  const flowsById = new Map(flows.map(f => [f.id, f]));

  const tasksByFlowRunId = new Map();
  for (const task of tasks) {
    if (!tasksByFlowRunId.has(task.flow_run_id)) {
      tasksByFlowRunId.set(task.flow_run_id, []);
    }
    tasksByFlowRunId.get(task.flow_run_id).push(task);
  }

  const subflowsByParentTaskId = new Map();
  for (const run of runs) {
    if (run.parent_task_run_id) {
      subflowsByParentTaskId.set(run.parent_task_run_id, run);
    }
  }

  const topLevelRuns = runs.filter(run => !run.parent_task_run_id);

  return topLevelRuns.map(run => {
    const deployment = deployments.find(d => d.id === run.deployment_id);
    const flow = flowsById.get(run.flow_id);
    const displayName = deployment ? deployment.name : (flow ? flow.name : run.name);

    const runTasks = tasksByFlowRunId.get(run.id) || [];
    const runItems = runTasks.map(task => {
      const subflowRun = subflowsByParentTaskId.get(task.id);

      if (subflowRun) {
        const subflowFlow = flowsById.get(subflowRun.flow_id);
        const subflowName = subflowFlow ? subflowFlow.name : subflowRun.name;
        const subflowStatus = mapPrefectStateToStatus(subflowRun.state?.type);
        const subflowTasks = (tasksByFlowRunId.get(subflowRun.id) || [])
          .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
          .map(sft => {
            const sftStatus = mapPrefectStateToStatus(sft.state?.type);
            return { type: 'task', id: sft.id, name: sft.name, status: sftStatus, duration: calculateDuration(sft.start_time, sft.end_time, sftStatus), startTime: sft.start_time };
          });
        return { type: 'subflow', id: subflowRun.id, name: subflowName, status: subflowStatus, duration: calculateDuration(subflowRun.start_time, subflowRun.end_time, subflowStatus), startTime: task.start_time, tasks: subflowTasks };
      }

      const taskStatus = mapPrefectStateToStatus(task.state?.type);
      return { type: 'task', id: task.id, name: task.name, status: taskStatus, duration: calculateDuration(task.start_time, task.end_time, taskStatus), startTime: task.start_time };
    });

    runItems.sort((a, b) => new Date(a.startTime) - new Date(b.startTime));

    return {
      id: run.id,
      name: displayName,
      status: mapPrefectStateToStatus(run.state?.type),
      startTime: run.start_time ? new Date(run.start_time).toLocaleString() : 'Not started',
      tasks: runItems,
    };
  });
};







// -----------------------------------------------------------
// fetchFlowRuns
// -----------------------------------------------------------
//
// Three POSTs: the last 50 runs, then the flows and task runs
// they reference.
//
// Used by:
//   - FlowsDashboard (below) — the polled query function
// -----------------------------------------------------------

const fetchFlowRuns = async (deployments) => {

  const runsResponse = await axios.post('/prefect/api/flow_runs/filter', {
    sort: "START_TIME_DESC",
    limit: 50,
    flow_runs: { state: { type: { any_: ["RUNNING", "PENDING", "SCHEDULED", "COMPLETED", "FAILED", "CANCELLED"] } } }
  }, PREFECT_POST_CONFIG);

  const flowRuns = runsResponse.data;
  if (flowRuns.length === 0) return [];

  const allFlowIds = [...new Set(flowRuns.map(run => run.flow_id))];

  const flowsResponse = await axios.post('/prefect/api/flows/filter', {
    flows: { id: { any_: allFlowIds } }
  }, PREFECT_POST_CONFIG);

  const taskRunsResponse = await axios.post('/prefect/api/task_runs/filter', {
    flow_runs: { id: { any_: flowRuns.map(r => r.id) } }
  }, PREFECT_POST_CONFIG);

  return processFlowRunData(flowRuns, flowsResponse.data, taskRunsResponse.data, deployments);
};







export default function FlowsDashboard() {

  const [activeTab, setActiveTab] = useState(0);
  const queryClient = useQueryClient();


  const {
    data: prefectDeployments = [],
    isPending: deploymentsLoading,
    error: deploymentsError,
    refetch: refetchDeployments,
  } = useQuery({
    queryKey: ['prefect-deployments'],
    queryFn: async () => (await axios.post('/prefect/api/deployments/filter', {}, PREFECT_POST_CONFIG)).data,
  });


  // The deployments stay out of the query key on purpose — a
  // key that changed with them would throw away the run tree
  // and flash the spinner; later changes ride the next poll.
  const {
    data: workflowRuns = [],
    isPending: runsLoading,
    error: runsError,
    refetch: refetchRuns,
  } = useQuery({
    queryKey: ['prefect-flow-runs'],
    queryFn: () => fetchFlowRuns(prefectDeployments),
    enabled: !deploymentsLoading,
    refetchInterval: RUNS_POLL_INTERVAL_MS,
  });


  const workflowTemplates = useMemo(() => prefectDeployments.map(d => ({
    id: d.id,
    name: d.name,
    description: d.description || 'Prefect deployment',
    flowName: d.flow_name,
    lastRun: d.updated,
  })), [prefectDeployments]);


  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };


  // `ref` is a deployment UUID (template cards) or a name
  // (shortcut buttons, written before the ids exist). The
  // loading toast is dismissed by id — a bare toast.dismiss()
  // would clear unrelated notifications too.
  const triggerWorkflow = async (ref) => {
    const loadingToastId = toast.loading(`Starting workflow...`);
    try {
      const deployment = prefectDeployments.find(d => d.id === ref || d.name === ref);

      if (deployment) {
        await axios.post(`/prefect/api/deployments/${deployment.id}/create_flow_run`, {}, PREFECT_POST_CONFIG);
        toast.dismiss(loadingToastId);
        toast.success(`Successfully triggered '${deployment.name}'`);
        setTimeout(
          () => queryClient.invalidateQueries({ queryKey: ['prefect-flow-runs'] }),
          TRIGGER_REFRESH_DELAY_MS
        );
      } else {
        toast.dismiss(loadingToastId);
        toast.error(`Deployment not found: ${ref}`);
      }
    } catch (error) {
      toast.dismiss(loadingToastId);
      toast.error(`Failed to start workflow: ${error.response?.data?.detail || error.message}`);
    }
  };


  return (
    <div className="w-full">
      <Box className="min-h-[calc(100vh-115px)] w-full flex flex-col p-4 bg-gray-50">

        <PageTitle>Workflows</PageTitle>

        {deploymentsError && (
          <Alert severity="error" className="mb-4" action={<button onClick={() => refetchDeployments()} className="text-red-600 underline hover:no-underline">Retry</button>}>
            <strong>Deployments Error:</strong> {deploymentsError.message}
          </Alert>
        )}
        {runsError && (
          <Alert severity="error" className="mb-4" action={<button onClick={() => refetchRuns()} className="text-red-600 underline hover:no-underline">Retry</button>}>
            <strong>Flow Runs Error:</strong> {runsError.message}
          </Alert>
        )}

        <QuickActions
          triggerWorkflow={triggerWorkflow}
          deploymentNames={prefectDeployments.map(d => d.name)}
        />

        <Paper className="flex-1">
          <Tabs value={activeTab} onChange={handleTabChange} className="border-b">
            <Tab label={`Active Workflows ${!runsLoading ? `(${workflowRuns.filter(r => r.status === 'running').length})` : ''}`} />
            <Tab label={`Templates ${deploymentsLoading ? '' : `(${workflowTemplates.length})`}`} />
          </Tabs>

          <Box className="p-4">
            {activeTab === 0 && (
              runsLoading
                ? <PageLoading label="Loading flow runs..." />
                : <ActiveWorkflows workflowRuns={workflowRuns} />
            )}
            {activeTab === 1 && (
              deploymentsLoading
                ? <PageLoading label="Loading deployments..." />
                : <WorkflowTemplates workflowTemplates={workflowTemplates} triggerWorkflow={triggerWorkflow} />
            )}
          </Box>
        </Paper>
      </Box>
    </div>
  );
}
