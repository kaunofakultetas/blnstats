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

export default function AdministratorsList() {
  return <AdministratorsListTable />;
}
