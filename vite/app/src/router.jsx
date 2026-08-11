// -----------------------------------------------------------
//  [*] Router — the app's route table
//
//  Every page is a child of the App layout route ("/"), which
//  adds the theme and auth providers; below it two pathless
//  layout routes hold the persistent page frames, so
//  navigating inside a section swaps only the page body.
//
//  handle.fullWidth marks the pages that want the full window
//  width; PublicPageLayout reads it back through useMatches().
//
//  Used by:
//    - main.jsx — passed to RouterProvider
// -----------------------------------------------------------

import { createBrowserRouter } from 'react-router-dom';
import App from '@/App';

import PublicPageLayout from '@/systemPages/PublicPages/PublicPageLayout';
import AdminPageLayout from '@/systemPages/AdminPages/AdminPageLayout';

import Login from '@/systemPages/PublicPages/Login/Login';

import Home from '@/systemPages/PublicPages/Home/Home';
import About from '@/systemPages/PublicPages/About/About';
import Coefficients from '@/systemPages/PublicPages/Coefficients/Coefficients';
import DataSources from '@/systemPages/PublicPages/DataSources/DataSources';
import LorenzCurves from '@/systemPages/PublicPages/LorenzCurves/LorenzCurves';
import Snapshots from '@/systemPages/PublicPages/Snapshots/Snapshots';

import Flows from '@/systemPages/AdminPages/Flows/Flows';
import AdministratorsList from '@/systemPages/AdminPages/AdministratorsList/AdministratorsList';


export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      // Login — rendered bare (App skips the providers)
      { path: 'login', element: <Login /> },

      {
        element: <PublicPageLayout />,
        children: [
          { index: true, element: <Home /> },
          { path: 'about', element: <About /> },
          { path: 'coefficients', element: <Coefficients /> },
          { path: 'datasources', element: <DataSources />, handle: { fullWidth: true } },
          { path: 'lorenz', element: <LorenzCurves />, handle: { fullWidth: true } },
          { path: 'snapshots', element: <Snapshots />, handle: { fullWidth: true } },
        ],
      },

      // AdminPageLayout redirects these to /login without a session
      {
        element: <AdminPageLayout />,
        children: [
          { path: 'admin', element: <Flows /> },
          { path: 'admin/administrators', element: <AdministratorsList /> },
        ],
      },
    ],
  },
]);
