// -----------------------------------------------------------
//  [*] Admin — Administrators page
//
//  Admin-only. The Header/Sidebar/Footer frame and the session
//  gate come from AdminPageLayout, which the route nests this
//  page inside; the grid and the add/edit dialog live in
//  AdministratorsListTable.
//
//  Used by:
//    - router.jsx — route /admin/administrators
// -----------------------------------------------------------

import AdministratorsListTable from "./AdministratorsListTable/AdministratorsListTable";







// -----------------------------------------------------------
// AdministratorsList (default export)
// -----------------------------------------------------------
//
// Nothing but the mount point — AdministratorsListTable
// carries the whole page.
//
// Used by:
//   - router.jsx — route /admin/administrators
// -----------------------------------------------------------

export default function AdministratorsList() {
  return <AdministratorsListTable />;
}
