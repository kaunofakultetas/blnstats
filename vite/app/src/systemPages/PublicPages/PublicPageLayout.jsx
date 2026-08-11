// -----------------------------------------------------------
//  [*] PublicPageLayout — the frame of the public pages
//
//  Mounted ONCE as a pathless layout route (router.jsx), so
//  navigating between public pages swaps only the page body
//  and the header does not remount.
//
//  A layout route takes no props from its pages, so the width
//  flag rides on the route entry as handle.fullWidth and is
//  read back here through useMatches().
//
//  Used by:
//    - router.jsx — layout route around every public page
// -----------------------------------------------------------

import { Outlet, useMatches } from "react-router-dom";

import Header from "@/components/Header/Header";







// -----------------------------------------------------------
// Footer
// -----------------------------------------------------------
//
// The 30px burgundy copyright strip; the login page repeats
// the same text with its own styling instead of mounting
// this.
//
// Used by:
//   - PublicPageLayout (below)
// -----------------------------------------------------------

function Footer() {
  return (
    <div className="bg-primary h-[30px] flex justify-center items-center text-white text-[0.7em]">
      Copyright © | All Rights Reserved | Vilnius university Kaunas faculty
    </div>
  );
}







// -----------------------------------------------------------
// PublicPageLayout (default export)
// -----------------------------------------------------------
//
// Header, then the page body in a centered padded column —
// full-bleed when the route sets handle.fullWidth — sized so
// Footer stays at the bottom even on short pages.
//
// Used by:
//   - router.jsx — layout route around every public page
// -----------------------------------------------------------

export default function PublicPageLayout() {

  const matches = useMatches();
  const fullWidth = matches.some((match) => match.handle?.fullWidth);

  return (
    <>
      <div className="flex flex-col items-center justify-center">
        <Header />
        <div
          className={`flex flex-col items-center p-2 md:p-10 ${fullWidth ? "md:max-w-full" : "md:max-w-300"}`}
          style={{ width: '100%', minHeight: 'calc(100vh - 120px)' }}
        >
          <Outlet />
        </div>
      </div>

      <Footer />
    </>
  );
}
