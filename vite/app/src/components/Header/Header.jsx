// -----------------------------------------------------------
//  [*] Header — the burgundy top bar
//
//  Shown on every page except /login: VU logo and title pill
//  on the left (both link to /), section links in the middle,
//  Raw Data plus Login/Logout on the right, all collapsing
//  into the hamburger menu below the lg breakpoint.
//
//  The session comes from the auth context rather than a
//  prop, so the bar reads the same state as every other
//  consumer and no layout has to thread it down.
//
//  Split into (root component last):
//
//    NavbarButton — one nav link (internal <Link>, or an
//                   external <a> in a new tab)
//    Header       — the bar itself (default export)
//
//  Used by:
//    - PublicPageLayout, AdminPageLayout — mounted once above
//      the routed page
// -----------------------------------------------------------

import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { AppBar, Box, Button, Container, Divider, IconButton, Menu, MenuItem, Toolbar, Typography } from "@mui/material";

import MenuIcon from "@mui/icons-material/Menu";
import LoginIcon from "@mui/icons-material/Login";
import LogoutIcon from "@mui/icons-material/Logout";
import ElectricBoltSharpIcon from "@mui/icons-material/ElectricBoltSharp";

import { useAuth } from "@/AuthGuard";
import { clearSession } from "@/session";







// -----------------------------------------------------------
// NavbarButton
// -----------------------------------------------------------
//
// `external` entries (/rawdata is served by the Caddy
// endpoint, not by this SPA) render as a plain <a> that opens
// in a new tab.
//
// The mobile menu passes onClick because a client-side
// navigation does not unmount the menu — without it the panel
// stays open on top of the page the visitor just asked for.
//
// Used by:
//   - Header (below)
// -----------------------------------------------------------

function NavbarButton({ href, text, pathname, external = false, show = true, onClick }) {

  if (!show) return null;

  const item = (
    <MenuItem onClick={onClick} sx={{ borderRadius: "5px", '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' } }}>
      <Typography fontFamily={"Tahoma, sans-serif"} style={{ textDecoration: pathname === href ? "underline" : "none" }}>
        {text}
      </Typography>
    </MenuItem>
  );

  if (external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="no-underline text-inherit">
        {item}
      </a>
    );
  }

  return (
    <Link to={href} className="no-underline text-inherit">
      {item}
    </Link>
  );
}







// -----------------------------------------------------------
// Header (default export)
// -----------------------------------------------------------
//
// Renders both nav layouts — the wide-screen rows and the
// hamburger Menu repeat the same NavbarButton list — and
// holds the Login/Logout button back until `ready`.
//
// Used by:
//   - PublicPageLayout, AdminPageLayout — mounted once above
//     the routed page
// -----------------------------------------------------------

export default function Header() {

  const { authData, ready } = useAuth();
  const { pathname } = useLocation();

  const signedIn = authData !== undefined;

  const [anchorEl, setAnchorEl] = useState(null);
  const handleClick = (event) => setAnchorEl(event.currentTarget);
  const handleClose = () => setAnchorEl(null);


  // Dropping the cookie and reloading re-runs the session
  // check as an anonymous visitor, on the same page
  const signOut = () => {
    clearSession();
    window.location.reload();
  };


  // Held back until the session check settles, so the button
  // never flips from Login to Logout in front of the user
  let userLoginLogoutButton = null;
  if (ready) {
    userLoginLogoutButton = signedIn ? (
      <Button
        className="ml-1 block"
        color="inherit"
        sx={{ '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' } }}
        onClick={signOut}
        startIcon={<LogoutIcon />}
      >
        Logout
      </Button>
    ) : (
      <Button
        className="ml-1"
        color="inherit"
        sx={{ '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' } }}
        href={"/login?redirectTo=" + encodeURIComponent(pathname)}
        startIcon={<LoginIcon />}
      >
        Login
      </Button>
    );
  }


  return (
    <AppBar position={"static"} color="primary">
      <Container maxWidth={false} disableGutters>
        <Toolbar>

          <Link to="/">
            <img src="/vulogo.png" alt="Logo" width={80} height={80} className="cursor-pointer rounded-2xl p-3" />
          </Link>

          <Link to="/" className="ml-4 no-underline">
            <div className="border border-white rounded-xl text-white p-2 flex flex-row">
              <ElectricBoltSharpIcon className="mr-2" />
              <div className="pr-1.5">Bitcoin LN Statistics</div>
            </div>
          </Link>

          <Box className="ml-4 hidden lg:flex">
            <Box className="flex justify-start p-2 m-2 mx-auto gap-1">
              <NavbarButton href={`/`} text={"Home"} pathname={pathname} />
              <NavbarButton href={`/datasources`} text={"Sources"} pathname={pathname} />
              <NavbarButton href={`/snapshots`} text={"Snapshots"} pathname={pathname} />
              <NavbarButton href={`/coefficients`} text={"Coefficients"} pathname={pathname} />
              <NavbarButton href={`/lorenz`} text={"Lorenz Curves"} pathname={pathname} />
              <NavbarButton href={`/about`} text={"About"} pathname={pathname} />
              <NavbarButton href={`/admin`} text={"Admin"} pathname={pathname} show={ready && signedIn} />
            </Box>
          </Box>


          <Box className="flex-grow justify-end hidden lg:flex gap-1">
            <NavbarButton href={`/rawdata`} text={"Raw Data"} pathname={pathname} external />
            {userLoginLogoutButton}
          </Box>


          <Box className="flex-grow flex justify-end lg:hidden" sx={{ width: 20 }}>
            <IconButton
              aria-controls="mobile-menu"
              aria-haspopup="true"
              onClick={handleClick}
              color="inherit"
            >
              <MenuIcon />
            </IconButton>
            <Menu
              id="mobile-menu"
              anchorEl={anchorEl}
              keepMounted
              open={Boolean(anchorEl)}
              onClose={handleClose}
              transformOrigin={{ horizontal: 'right', vertical: 'top' }}
              anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
            >
              <NavbarButton href={`/`} text={"Home"} pathname={pathname} onClick={handleClose} />
              <NavbarButton href={`/datasources`} text={"Sources"} pathname={pathname} onClick={handleClose} />
              <NavbarButton href={`/snapshots`} text={"Snapshots"} pathname={pathname} onClick={handleClose} />
              <NavbarButton href={`/coefficients`} text={"Coefficients"} pathname={pathname} onClick={handleClose} />
              <NavbarButton href={`/lorenz`} text={"Lorenz Curves"} pathname={pathname} onClick={handleClose} />
              <NavbarButton href={`/about`} text={"About"} pathname={pathname} onClick={handleClose} />
              <NavbarButton href={`/admin`} text={"Admin"} pathname={pathname} show={ready && signedIn} onClick={handleClose} />
              <Divider />
              <NavbarButton href={`/rawdata`} text={"Raw Data"} pathname={pathname} external onClick={handleClose} />
              <Divider />
              {userLoginLogoutButton && (
                <MenuItem onClick={handleClose}>
                  {userLoginLogoutButton}
                </MenuItem>
              )}
            </Menu>
          </Box>

        </Toolbar>
      </Container>
    </AppBar>
  );
}
