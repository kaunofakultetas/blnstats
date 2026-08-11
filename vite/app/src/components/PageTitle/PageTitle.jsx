// -----------------------------------------------------------
//  [*] PageTitle — the standard page heading row
//
//  The grey 24px heading an admin page shows above its
//  content. Also a flex row with justify-between: pass
//  buttons or extras as siblings of the text and they land on
//  the right edge.
//
//  Pages mount this instead of styling a heading themselves,
//  so the size and the bottom margin cannot drift apart.
//
//  Used by:
//    - AdministratorsListTable — the grid heading
//    - FlowsDashboard — the dashboard heading
// -----------------------------------------------------------

export default function PageTitle({ children }) {
  return (
    <div className="w-full text-2xl text-gray-500 mb-2.5 flex items-center justify-between">
      {children}
    </div>
  );
}
