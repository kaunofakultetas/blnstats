// -----------------------------------------------------------
//  [*] AdminSidebar — left navigation of the admin section
//
//  A narrow icon rail sits in the layout; hovering expands
//  the panel OVER the content (no reflow), while the pin
//  button docks it open at real layout width. The pinned
//  choice persists in localStorage "sidebarOpen".
//
//  Links come from SECTIONS. The `external: true` ones (File
//  Browser, Prefect, DBGate) are separate containers proxied
//  under this domain by the endpoint Caddy, so they open in a
//  new tab rather than routing. Every row shows for everyone:
//  AdminPageLayout gates the admin section and every account
//  of this app is an administrator. Logout links to /login,
//  which drops the session cookie.
//
//  Split into (root component last):
//
//    SECTIONS              — the declarative link table
//    clampWidth            — sanity bounds on the width
//    findActiveHref        — which row the current URL is
//    useSidebarPreferences — pinned persistence (guarded)
//    useHoverExpand        — fly-over hover state
//    useContentWidth       — ghost + ResizeObserver width
//    SectionTitle          — grey group heading
//    MenuItemContent       — icon + label (tooltip on rail)
//    MenuItem              — internal <Link> / external <a>
//    PinButton             — the dock/undock bar
//    SidebarLinks          — the table rendered as the list
//    AdminSidebar          — slot + panel (default export)
//
//  Used by:
//    - AdminPageLayout — mounted once next to the routed page
// -----------------------------------------------------------

import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import Divider from '@mui/material/Divider';
import Tooltip from '@mui/material/Tooltip';

import PushPinIcon from '@mui/icons-material/PushPin';
import PushPinOutlinedIcon from '@mui/icons-material/PushPinOutlined';

import AirIcon from '@mui/icons-material/Air';
import BadgeIcon from '@mui/icons-material/Badge';

import UploadFileIcon from '@mui/icons-material/UploadFile';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import StorageIcon from '@mui/icons-material/Storage';

import ExitToAppIcon from "@mui/icons-material/ExitToApp";


const STORAGE_KEY = "sidebarOpen";

// Sidebar widths (px). Expanded = widest label +
// LABEL_SURROUND, which must stay in sync with the row
// markup: wrapper padding 2×10, icon column offset 7.5,
// icon 17, label margin 10, row right padding 10, panel
// border 1. DEFAULT bridges the first frame before the
// ResizeObserver fires.
const RAIL_WIDTH = 52;
const DEFAULT_EXPANDED_WIDTH = 210;
const MIN_EXPANDED_WIDTH = 140;
const MAX_EXPANDED_WIDTH = 400;
const LABEL_SURROUND = 20 + 7.5 + 17 + 10 + 10 + 1;

// Grace period after the mouse leaves the panel
const CLOSE_DELAY_MS = 200;







// -----------------------------------------------------------
// SECTIONS
// -----------------------------------------------------------
//
// The whole navigation as data: adding a link is a one-line
// edit here, no JSX involved.
//
// Used by:
//   - findActiveHref, SidebarLinks, AdminSidebar (below)
// -----------------------------------------------------------

const SECTIONS = [
  {
    title: "MAIN",
    items: [
      { href: "/admin", icon: AirIcon, label: "Workflows" },
      { href: "/admin/administrators", icon: BadgeIcon, label: "Administrators" },
    ],
  },
  {
    title: "SUBSYSTEMS",
    items: [
      { href: "/filebrowser", icon: UploadFileIcon, label: "File Browser", external: true },
      { href: "/prefect", icon: AccountTreeIcon, label: "Prefect Server", external: true },
      { href: "/dbgate", icon: StorageIcon, label: "DBGate", external: true },
    ],
  },
  {
    title: "ACCOUNT",
    items: [
      { href: "/login", icon: ExitToAppIcon, label: "Logout" },
    ],
  },
];







// -----------------------------------------------------------
// clampWidth
// -----------------------------------------------------------
//
// Sanity bounds only — the width itself is content-driven.
//
// Used by:
//   - useContentWidth (below)
// -----------------------------------------------------------

const clampWidth = (width) =>
  Math.min(Math.max(width, MIN_EXPANDED_WIDTH), MAX_EXPANDED_WIDTH);







// -----------------------------------------------------------
// findActiveHref
// -----------------------------------------------------------
//
// The href of the row owning the current URL: exact path or
// anything nested under it, LONGEST match winning so that
// /admin/administrators lights "Administrators" alone and not
// "Workflows" as well.
//
// Used by:
//   - AdminSidebar (below)
// -----------------------------------------------------------

function findActiveHref(pathname) {
  let best = null;

  for (const section of SECTIONS) {
    for (const item of section.items) {
      if (item.external) continue;
      if (pathname === item.href || pathname.startsWith(item.href + '/')) {
        if (!best || item.href.length > best.length) {
          best = item.href;
        }
      }
    }
  }

  return best;
}







// -----------------------------------------------------------
// useSidebarPreferences
// -----------------------------------------------------------
//
// The persisted pinned (docked open) state. Storage access is
// try/catch-guarded: private browsing modes can throw on it,
// and the sidebar must still work — it just forgets the
// choice on reload.
//
// Used by:
//   - AdminSidebar (below)
// -----------------------------------------------------------

function useSidebarPreferences() {

  const [pinned, setPinned] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) !== "false";
    } catch {
      return true;
    }
  });

  const togglePinned = () => {
    const newValue = !pinned;
    setPinned(newValue);
    try {
      localStorage.setItem(STORAGE_KEY, newValue);
    } catch { /* storage unavailable — the toggle still works */ }
  };

  return { pinned, togglePinned };
}







// -----------------------------------------------------------
// useHoverExpand
// -----------------------------------------------------------
//
// The fly-over hover state. Leaving collapses only after
// CLOSE_DELAY_MS, so brushing across the panel edge doesn't
// flicker it shut.
//
// Used by:
//   - AdminSidebar (below)
// -----------------------------------------------------------

function useHoverExpand() {

  const [hovered, setHovered] = useState(false);
  const closeTimer = useRef(null);

  const onMouseEnter = () => {
    clearTimeout(closeTimer.current);
    setHovered(true);
  };

  const onMouseLeave = () => {
    clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => setHovered(false), CLOSE_DELAY_MS);
  };

  useEffect(() => () => clearTimeout(closeTimer.current), []);

  return { hovered, onMouseEnter, onMouseLeave };
}







// -----------------------------------------------------------
// useContentWidth
// -----------------------------------------------------------
//
// The content-fit expanded width: a ResizeObserver on the
// invisible ghost copy of the labels recalibrates on new menu
// items or late-loading fonts. A ghost not laid out yet
// reports ~0, hence the small-width guard. `measured` turns
// true on the first real reading — the root keeps the width
// transition OFF until then, so the correction from the
// DEFAULT guess to the true width applies instantly instead
// of playing as a visible settle-slide on every page load.
//
// Used by:
//   - AdminSidebar (below)
// -----------------------------------------------------------

function useContentWidth(ghostRef) {

  const [expandedWidth, setExpandedWidth] = useState(DEFAULT_EXPANDED_WIDTH);
  const [measured, setMeasured] = useState(false);

  useEffect(() => {
    const ghost = ghostRef.current;
    if (!ghost) return;

    const observer = new ResizeObserver((entries) => {
      const labelWidth = entries[0]?.contentRect?.width ?? 0;
      if (labelWidth < 30) return;
      setExpandedWidth(clampWidth(Math.ceil(labelWidth) + LABEL_SURROUND));
      setMeasured(true);
    });

    observer.observe(ghost);
    return () => observer.disconnect();
  }, [ghostRef]);

  return { expandedWidth, measured };
}







// -----------------------------------------------------------
// SectionTitle
// -----------------------------------------------------------
//
// Grey heading above a group of links; on the rail a divider
// line takes its place so the grouping stays visible. Both
// stay in the DOM and CROSSFADE on the same 300 ms clock as
// the panel width — the old conditional swap popped the text
// in and out mid-animation. The fixed-height row keeps links
// from jumping while the panel expands, and nowrap keeps the
// title from re-wrapping at intermediate widths.
//
// Used by:
//   - SidebarLinks (below) — one per section
// -----------------------------------------------------------

function SectionTitle({ title, open }) {
  return (
    <div className="relative mt-[15px] mb-[2px] h-[15px] flex items-center">
      <p className={`text-[10px] font-bold text-[#999] whitespace-nowrap m-0 transition-opacity duration-300 ${open ? 'opacity-100' : 'opacity-0'}`}>{title}</p>
      <Divider className={`absolute inset-x-0 top-1/2 transition-opacity duration-300 ${open ? 'opacity-0' : 'opacity-100'}`} />
    </div>
  );
}







// -----------------------------------------------------------
// MenuItemContent
// -----------------------------------------------------------
//
// Icon + label. On the rail only the icon is visible and the
// label appears as a tooltip; the tooltip is controlled
// manually so it never fires once the panel is expanded and
// the label is already legible.
//
// Used by:
//   - MenuItem (below) — wrapped in a <Link> or <a>
// -----------------------------------------------------------

function MenuItemContent({ icon: Icon, label, open, active }) {

  const [hovered, setHovered] = useState(false);

  return (
    <Tooltip
      open={!open && hovered}
      title={label}
      placement="right"
      disableInteractive
      slotProps={{
        tooltip: { sx: { backgroundColor: '#000', fontSize: '15px' } },
      }}
    >
      <li
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={() => setHovered(false)}
        // pl-[7.5px] centers the 17px icon on the 52px rail and
        // pins the expanded icon column to that same spot; the
        // fixed h-[23px] stops rows shifting as the panel opens
        className={`flex items-center h-[23px] py-[3px] pl-[7.5px] pr-[10px] cursor-pointer whitespace-nowrap rounded-[3px] hover:bg-[#999] transition-colors ${active ? 'bg-primary/8' : ''}`}
      >
        <Icon style={{ fontSize: '17px', color: 'rgb(123, 0, 63)' }} />
        {/* Always in the DOM so the width can be measured and
            the row height stays constant — invisible rather
            than clipped on the rail */}
        <span className={`flex-1 min-w-0 overflow-hidden text-ellipsis text-[13px] leading-[17px] font-semibold ml-[10px] transition-opacity duration-300 ${active ? 'text-primary' : 'text-[rgb(65,65,65)]'} ${open ? 'opacity-100' : 'opacity-0'}`}>{label}</span>
      </li>
    </Tooltip>
  );
}







// -----------------------------------------------------------
// MenuItem
// -----------------------------------------------------------
//
// One link row: a router <Link> for in-app pages, or — when
// `external` — a plain <a> opening a new tab, since those
// rows leave the SPA for the proxied subsystem containers.
//
// Used by:
//   - SidebarLinks (below) — every item of every section
// -----------------------------------------------------------

function MenuItem({ href, icon: Icon, label, open, active, external = false }) {

  if (external) {
    return (
      <a href={href} className="no-underline" target="_blank" rel="noopener noreferrer">
        <MenuItemContent icon={Icon} label={label} open={open} active={active} />
      </a>
    );
  }

  return (
    <Link to={href} className="no-underline">
      <MenuItemContent icon={Icon} label={label} open={open} active={active} />
    </Link>
  );
}







// -----------------------------------------------------------
// PinButton
// -----------------------------------------------------------
//
// The burgundy dock/undock bar: filled pin when the panel is
// pinned open, outlined while it only flies out on hover.
// The tooltip names the action a click would take.
//
// Used by:
//   - AdminSidebar (below) — first row of the list
// -----------------------------------------------------------

function PinButton({ pinned, onToggle }) {
  return (
    <Tooltip
      title={pinned ? "Unpin sidebar" : "Pin sidebar"}
      placement="right"
      disableInteractive
      slotProps={{ tooltip: { sx: { backgroundColor: '#000', fontSize: '13px' } } }}
    >
      <button
        onClick={onToggle}
        className="w-full h-[30px] mt-3 flex items-center justify-center bg-primary hover:bg-primary-dark border-0 rounded-md cursor-pointer transition-colors"
      >
        {pinned
          ? <PushPinIcon style={{ fontSize: '18px', color: 'white' }} />
          : <PushPinOutlinedIcon style={{ fontSize: '18px', color: 'rgba(255,255,255,0.85)' }} />
        }
      </button>
    </Tooltip>
  );
}







// -----------------------------------------------------------
// SidebarLinks
// -----------------------------------------------------------
//
// The SECTIONS table rendered out: a SectionTitle per group,
// then a MenuItem per link, with `activeHref` marking the
// row that owns the current URL.
//
// Used by:
//   - AdminSidebar (below) — inside the panel
// -----------------------------------------------------------

function SidebarLinks({ open, activeHref }) {
  return (
    <>
      {SECTIONS.map((section) => (
        <div key={section.title}>
          <SectionTitle title={section.title} open={open} />
          {section.items.map((item) => (
            <MenuItem
              key={item.href}
              href={item.href}
              icon={item.icon}
              label={item.label}
              open={open}
              active={item.href === activeHref}
              external={item.external}
            />
          ))}
        </div>
      ))}
    </>
  );
}







// -----------------------------------------------------------
// AdminSidebar (default export)
// -----------------------------------------------------------
//
// Two nested boxes: the SLOT holds layout space in the page
// flex row (rail width, or the expanded width when pinned)
// and the PANEL is absolutely positioned inside it, so a
// hover expansion grows over the content without reflowing it.
// -----------------------------------------------------------

export default function AdminSidebar() {

  const { pathname } = useLocation();
  const ghostRef = useRef(null);

  const { hovered, onMouseEnter, onMouseLeave } = useHoverExpand();
  const { pinned, togglePinned } = useSidebarPreferences();
  const { expandedWidth, measured } = useContentWidth(ghostRef);

  const activeHref = findActiveHref(pathname);

  const open = pinned || hovered;
  const overlaying = open && !pinned;

  // No width animation until the first real measurement:
  // otherwise the DEFAULT-to-true-width correction plays as a
  // visible settle-slide on every page load
  const widthTransition = measured ? 'transition-[width] duration-300 ease-in-out' : '';
  const panelTransition = measured ? 'transition-[width,box-shadow] duration-300 ease-in-out' : '';

  return (
    // The slot — holds the layout space the panel flies out of
    <div
      className={`relative shrink-0 ${widthTransition}`}
      style={{ width: pinned ? expandedWidth : RAIL_WIDTH }}
    >
      {/* The panel — a plain white div, NOT a MUI Paper: Paper
          injects its own `transition: box-shadow ...` shorthand
          from emotion, which raced the width transition and
          made hover-open snap instead of slide */}
      <div
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        className={`absolute inset-y-0 left-0 z-40 border-r border-gray-200 bg-white overflow-y-auto overflow-x-hidden ${panelTransition} ${overlaying ? 'shadow-[4px_0_20px_rgba(0,0,0,0.25)]' : ''}`}
        style={{ width: open ? expandedWidth : RAIL_WIDTH }}
      >
        {/* Ghost measurer — an invisible, zero-height copy of
            every label at natural width. Same typography
            classes as the real labels so it measures true. */}
        <div ref={ghostRef} aria-hidden="true" className="absolute invisible h-0 overflow-hidden w-max whitespace-nowrap text-[13px] font-semibold">
          {SECTIONS.flatMap((section) => section.items).map((item) => (
            <div key={item.href}>{item.label}</div>
          ))}
        </div>

        <nav className="px-[10px]">
          <ul className="list-none m-0 p-0">
            <PinButton pinned={pinned} onToggle={togglePinned} />
            <SidebarLinks open={open} activeHref={activeHref} />
          </ul>
        </nav>
      </div>
    </div>
  );
}
