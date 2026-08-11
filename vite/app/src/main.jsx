// -----------------------------------------------------------
//  [*] Entry point — mounts the React app
//
//  Renders the router into #root inside StrictMode and one
//  QueryClientProvider — a single QueryClient owns every
//  backend fetch: the session check, the generated JSON under
//  /rawdata, the Prefect polling and the admin grids. Global
//  Tailwind styles are imported here.
// -----------------------------------------------------------

import { StrictMode } from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { router } from '@/router';
import '@/globals.css';


// retry 1: a poll that fails twice in a row should surface
// its error state, not spin.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>
);
