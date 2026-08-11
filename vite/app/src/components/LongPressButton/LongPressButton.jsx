// -----------------------------------------------------------
//  [*] LongPressButton — hold-to-confirm button
//
//  Button that must be held down (default 3 s) before it
//  fires — for destructive actions, in place of a confirm
//  dialog. Mouse and touch both work.
//
//  The toasts land in the outlet AdminPageLayout mounts, so
//  these buttons belong inside the admin section.
//
//  The presets sit above the root component and lean on
//  function hoisting to reference it.
//
//  Split into (root component last):
//
//    useLongPress          — press state + rAF progress loop
//    PressProgress         — circular progress ring
//    ButtonTooltip         — tooltip that works when disabled
//    LongPressDeleteButton — red "delete" preset
//    LongPressIconButton   — IconButton flavor
//    LongPressButton       — the button itself (default export)
//
//  Imported via the folder's index.js:
//    @/components/LongPressButton
// -----------------------------------------------------------

import { useState, useEffect } from "react";
import { Button, IconButton, CircularProgress, Tooltip } from "@mui/material";
import toast from 'react-hot-toast';


// 3 s default hold — long enough that a stray click or an
// accidental touch can never fire the action
const DEFAULT_DURATION = 3000;







// -----------------------------------------------------------
// useLongPress
// -----------------------------------------------------------
//
// The only real state is `pressedAt`, the timestamp the hold
// started (null = not pressed). While it is set an rAF loop
// advances progress; the effect cleanup stops that loop, so
// unmounting mid-press is covered too.
//
// The buttons wire `cancel` to touchcancel alongside
// touchend/mouseup/mouseleave, so an OS-interrupted touch
// (incoming call, browser gesture) aborts the hold instead
// of letting the action fire with no finger down.
//
// Used by:
//   - LongPressIconButton, LongPressButton (below)
// -----------------------------------------------------------

function useLongPress({ onComplete, disabled, duration, completedToastMessage, uncompletedToastMessage }) {

  const [pressedAt, setPressedAt] = useState(null);
  const [progress, setProgress] = useState(0);


  useEffect(() => {
    if (pressedAt === null) return;

    let frame;
    const tick = () => {
      const elapsed = Date.now() - pressedAt;
      setProgress(Math.min((elapsed / duration) * 100, 100));

      if (elapsed >= duration) {
        setPressedAt(null);
        setProgress(0);
        if (completedToastMessage) {
          toast.success(<b>{completedToastMessage}</b>, { duration: 3000 });
        }
        onComplete?.();
        return;
      }

      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [pressedAt, duration, onComplete, completedToastMessage]);


  const start = (e) => {
    if (disabled) return;
    e.stopPropagation();
    e.preventDefault();

    setProgress(0);
    setPressedAt(Date.now());
  };


  const cancel = (e) => {
    if (pressedAt === null) return;
    e?.stopPropagation();

    if (Date.now() - pressedAt < duration && uncompletedToastMessage) {
      toast.error(<b>{uncompletedToastMessage}</b>, { duration: 3000 });
    }

    setPressedAt(null);
    setProgress(0);
  };


  return { isPressed: pressedAt !== null, progress, start, cancel };
}







// -----------------------------------------------------------
// PressProgress
// -----------------------------------------------------------
//
// MUI's own stroke transition is switched off so the ring
// tracks the rAF-driven value instead of lagging behind it.
//
// Used by:
//   - LongPressIconButton, LongPressButton (below)
// -----------------------------------------------------------

function PressProgress({ progress, size, thickness, color, bgColor }) {
  return (
    <div
      style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: size,
        height: size,
      }}
    >
      {/* Background circle */}
      <CircularProgress
        variant="determinate"
        value={100}
        size={size}
        thickness={thickness}
        sx={{ color: bgColor, position: 'absolute' }}
      />

      {/* Progress circle */}
      <CircularProgress
        variant="determinate"
        value={progress}
        size={size}
        thickness={thickness}
        sx={{
          color: color,
          position: 'absolute',
          '& .MuiCircularProgress-circle': {
            strokeLinecap: 'round',
            transition: 'none',
          },
        }}
      />
    </div>
  );
}







// -----------------------------------------------------------
// ButtonTooltip
// -----------------------------------------------------------
//
// The button is wrapped in a <span> so the tooltip works on
// disabled buttons too — a disabled element fires no hover
// events of its own.
//
// Used by:
//   - LongPressButton (below)
// -----------------------------------------------------------

function ButtonTooltip({ tooltip, fullWidth, children }) {

  if (!tooltip) return children;

  return (
    <Tooltip
      title={<span style={{ fontSize: '0.9rem' }}>{tooltip}</span>}
      arrow
      disableInteractive
      slotProps={{
        tooltip: { sx: { backgroundColor: 'black', py: 0.5, px: 1 } },
        arrow: { sx: { color: 'black' } },
      }}
    >
      <span style={{ display: 'flex', flex: 1, width: fullWidth ? '100%' : 'auto' }}>
        {children}
      </span>
    </Tooltip>
  );
}







// -----------------------------------------------------------
// LongPressDeleteButton (exported)
// -----------------------------------------------------------
//
// Red "delete" preset. Dead weight, kept as is: color="error"
// merely repeats LongPressButton's own default, and the two
// toast props it re-passes would ride along in {...props}
// anyway — the preset currently adds nothing but its name.
//
// Used by:
//   - AddEditAdministrator — the "Delete Record" button of
//     the administrator dialog
// -----------------------------------------------------------

export function LongPressDeleteButton({
  children,
  completedToastMessage,
  uncompletedToastMessage,
  ...props
}) {
  return (
    <LongPressButton
      color="error"
      completedToastMessage={completedToastMessage}
      uncompletedToastMessage={uncompletedToastMessage}
      {...props}
    >
      {children}
    </LongPressButton>
  );
}







// -----------------------------------------------------------
// LongPressIconButton (exported)
// -----------------------------------------------------------
//
// Hold-to-confirm on a round MUI IconButton. Same core props;
// no tooltip or pressedContent — the caller wraps its own.
//
// Used by:
//   - nothing yet — no icon-only destructive action exists
//     here, kept as part of the component's preset set
// -----------------------------------------------------------

export function LongPressIconButton({
  onComplete,
  disabled = false,
  duration = DEFAULT_DURATION,
  children,
  completedToastMessage,
  uncompletedToastMessage,
  progressSize = 24,
  progressThickness = 4,
  progressColor = "white",
  progressBgColor = "rgba(255,255,255,0.3)",
  ...buttonProps
}) {

  const { isPressed, progress, start, cancel } = useLongPress({
    onComplete,
    disabled,
    duration,
    completedToastMessage,
    uncompletedToastMessage,
  });

  return (
    <IconButton
      disabled={disabled}
      onMouseDown={start}
      onMouseUp={cancel}
      onMouseLeave={cancel}
      onTouchStart={start}
      onTouchEnd={cancel}
      onTouchCancel={cancel}
      onContextMenu={(e) => e.preventDefault()}
      {...buttonProps}
    >
      {isPressed ? (
        <PressProgress
          progress={progress}
          size={progressSize}
          thickness={progressThickness}
          color={progressColor}
          bgColor={progressBgColor}
        />
      ) : children}
    </IconButton>
  );
}







// -----------------------------------------------------------
// LongPressButton (default export)
// -----------------------------------------------------------
//
// The full MUI Button flavor: optional tooltip via
// ButtonTooltip, and while held the label gives way to the
// progress ring or the caller's `pressedContent`.
//
// Used by:
//   - LongPressDeleteButton (above)
//   - WorkflowTemplateCard — the "Run Now" button, so a
//     stray click cannot launch a pipeline
// -----------------------------------------------------------

export default function LongPressButton({
  onComplete,
  disabled = false,
  duration = DEFAULT_DURATION,

  children,
  pressedContent,          // shown instead of the ring while held

  color = "error",
  variant = "contained",
  fullWidth = false,
  size = "medium",
  sx = {},

  completedToastMessage,
  uncompletedToastMessage,

  tooltip = "",

  progressSize = 24,
  progressThickness = 4,
  progressColor = "white",
  progressBgColor = "rgba(255,255,255,0.3)",

  ...buttonProps
}) {

  const { isPressed, progress, start, cancel } = useLongPress({
    onComplete,
    disabled,
    duration,
    completedToastMessage,
    uncompletedToastMessage,
  });

  return (
    <ButtonTooltip tooltip={tooltip} fullWidth={fullWidth}>
      <Button
        variant={variant}
        color={color}
        fullWidth={fullWidth}
        size={size}
        disabled={disabled}
        onMouseDown={start}
        onMouseUp={cancel}
        onMouseLeave={cancel}
        onTouchStart={start}
        onTouchEnd={cancel}
        onTouchCancel={cancel}
        onContextMenu={(e) => e.preventDefault()} // long press opens it on touch
        sx={{
          userSelect: 'none', // holding otherwise selects the label
          ...sx,
        }}
        {...buttonProps}
      >
        {isPressed
          ? (pressedContent || (
              <PressProgress
                progress={progress}
                size={progressSize}
                thickness={progressThickness}
                color={progressColor}
                bgColor={progressBgColor}
              />
            ))
          : children}
      </Button>
    </ButtonTooltip>
  );
}
