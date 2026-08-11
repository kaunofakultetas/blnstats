// -----------------------------------------------------------
//  [*] AdminPageLayout — the frame of the admin section
//
//  Mounted ONCE as a pathless layout route (router.jsx), so
//  moving between admin pages swaps only the page body and the
//  sidebar keeps its open/closed state. The section's one
//  Toaster lives here because both the workflow dashboard and
//  the administrator dialog raise toasts.
//
//  This is also the admin gate, acting on the session check
//  AuthGuard runs once. Being signed in is the whole gate —
//  every account of this app is an administrator and the
//  backend hardcodes admin: 1 in its checkauth answer.
//
//  Split into (root component last):
//
//    Footer           — the burgundy copyright bar
//    AdminSkeleton    — the frame as grey bones while the
//                       session check runs
//    AdminPageLayout  — frame + gate + outlet (default export)
//
//  Used by:
//    - router.jsx — layout route around every admin page
// -----------------------------------------------------------

import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Toaster } from 'react-hot-toast';
import { Box, Skeleton } from "@mui/material";

import { useAuth } from "@/AuthGuard";
import Header from "@/components/Header/Header";
import AdminSidebar from "@/components/Admin/Sidebar/Sidebar";







// -----------------------------------------------------------
// Footer
// -----------------------------------------------------------

function Footer() {
  return (
    <Box className="h-[30px] flex justify-center items-center text-[0.7em]" sx={{ backgroundColor: 'primary.main', color: 'white' }}>
      Copyright © | All Rights Reserved | Vilnius university Kaunas faculty
    </Box>
  );
}







// -----------------------------------------------------------
// AdminSkeleton
// -----------------------------------------------------------
//
// The heights match the real frame, so the page does not jump
// when /api/checkauth answers.
// -----------------------------------------------------------

function AdminSkeleton() {
  return (
    <Box className="flex flex-col">
      <div className="h-[64px] bg-primary" />

      <Box className="flex flex-row">
        {/* Width matches the sidebar's DEFAULT_EXPANDED_WIDTH
            so the frame barely moves when the real one arrives */}
        <div className="w-[210px] shrink-0 px-[10px] pt-[10px]">
          <Skeleton variant="rounded" height={30} />
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} variant="text" height={24} sx={{ mt: 1 }} />
          ))}
        </div>

        <div className="flex-1 p-6 h-[calc(100vh-94px)]">
          <Skeleton variant="text" height={40} width="30%" />
          <Skeleton variant="rounded" height={100} sx={{ mt: 2 }} />
          <Skeleton variant="rounded" height={240} sx={{ mt: 2 }} />
        </div>
      </Box>

      <Footer />
    </Box>
  );
}







export default function AdminPageLayout() {

  const { authData, ready } = useAuth();
  const { pathname } = useLocation();

  if (!ready) {
    return <AdminSkeleton />;
  }

  // redirectTo is what sends the user back here after login
  if (authData === undefined) {
    return <Navigate to={`/login?redirectTo=${encodeURIComponent(pathname)}`} replace />;
  }

  return (
    <Box className="flex flex-col">
      <Toaster position="top-right" />
      <Header />

      <Box className="flex flex-row">
        <AdminSidebar />
        <Outlet />
      </Box>

      <Footer />
    </Box>
  );
}
