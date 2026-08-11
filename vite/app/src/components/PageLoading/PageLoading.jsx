// -----------------------------------------------------------
//  [*] PageLoading — the standard "content is loading" filler
//
//  Centered spinner (+ optional label) that takes the place of
//  a page or panel while its data loads — one look, in the
//  theme's primary color, for every blocking load in the app.
//
//  It fills whatever box it is dropped into, so a caller that
//  wants a specific shape — the chart's fixed-height card,
//  say — sizes its own wrapper and puts this inside.
//
//  Used by:
//    - FlowsDashboard — both tabs, while Prefect answers
//    - DataSources — while the comparison file loads
//    - GeneralChart — while the statistics file loads
// -----------------------------------------------------------

import CircularProgress from '@mui/material/CircularProgress';







// -----------------------------------------------------------
// PageLoading (default export)
// -----------------------------------------------------------
//
// The spinner column itself: fills its wrapper, centers the
// progress ring, and shows the grey label only when one is
// given.
//
// Used by:
//   - FlowsDashboard — both tabs, while Prefect answers
//   - DataSources — while the comparison file loads
//   - GeneralChart — while the statistics file loads
// -----------------------------------------------------------

export default function PageLoading({ label }) {
  return (
    <div className="flex-1 h-full min-h-[200px] flex flex-col items-center justify-center gap-3 p-5">
      <CircularProgress />
      {label && <div className="text-gray-500 text-sm">{label}</div>}
    </div>
  );
}
