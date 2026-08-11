// -----------------------------------------------------------
//  [*] Admin — Workflows page
//
//  Admin-only. The Header/Sidebar/Footer frame and the session
//  gate come from AdminPageLayout, which the route nests this
//  page inside.
//
//  Used by:
//    - router.jsx — route /admin
// -----------------------------------------------------------

import FlowsDashboard from "./Dashboard/FlowsDashboard";







// -----------------------------------------------------------
// Flows (default export)
// -----------------------------------------------------------
//
// Nothing but the mount point — FlowsDashboard carries the
// whole page.
//
// Used by:
//   - router.jsx — route /admin
// -----------------------------------------------------------

export default function Flows() {
  return <FlowsDashboard />;
}
