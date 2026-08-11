// -----------------------------------------------------------
//  [*] UniversalModal — the shared modal dialog
//
//  One configurable dialog: a title/description header with an
//  optional variant icon, arbitrary children as the body, and
//  either the stock Confirm/Cancel pair or custom `actions`.
//  The variant ("default" | "danger" | "warning" | "info" |
//  "success") picks the header icon and the confirm color.
//
//  Pass `sourceRect` (the trigger's getBoundingClientRect())
//  and the dialog flies out of that element and back into it
//  on close; without it it grows from the screen center.
//
//  The presets sit above the root component and lean on
//  function hoisting to reference it.
//
//  Split into (root component last):
//
//    FLIGHT_MS       — the one flow-animation duration
//    VARIANTS        — per-variant icon + color table
//    ModalHeader     — icon, title, description, close (×)
//    StandardActions — the stock Confirm/Cancel footer
//    ConfirmModal    — "are you sure?" preset
//    DeleteModal     — danger delete preset
//    AlertModal      — info notice preset
//    WarningModal    — warning notice preset
//    UniversalModal  — the modal itself (default export)
//
//  Imported via the folder's index.js:
//    @/components/UniversalModal
// -----------------------------------------------------------

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import {
  Modal,
  Paper,
  Box,
  Typography,
  Button,
  IconButton,
  CircularProgress,
  Divider,
} from "@mui/material";

import CloseIcon from '@mui/icons-material/Close';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';


// One duration for everything the flow animation moves — the
// paper's flight, both fades AND the unmount delay. Keep them
// identical or the close flight gets cut off before landing.
const FLIGHT_MS = 400;







// -----------------------------------------------------------
// VARIANTS
// -----------------------------------------------------------
//
// Per-variant header icon and the color fed to both that icon
// and the stock Confirm button. "default" has no icon at all.
//
// Used by:
//   - UniversalModal (below) — picked by the `variant` prop;
//     unknown values fall back to "default"
// -----------------------------------------------------------

const VARIANTS = {
  default: {
    icon: null,
    confirmColor: "primary",
    iconColor: "primary",
  },
  danger: {
    icon: ErrorOutlineIcon,
    confirmColor: "error",
    iconColor: "error",
  },
  warning: {
    icon: WarningAmberIcon,
    confirmColor: "warning",
    iconColor: "warning",
  },
  info: {
    icon: InfoOutlinedIcon,
    confirmColor: "info",
    iconColor: "info",
  },
  success: {
    icon: CheckCircleOutlineIcon,
    confirmColor: "success",
    iconColor: "success",
  },
};







// -----------------------------------------------------------
// ModalHeader
// -----------------------------------------------------------
//
// Header row: variant icon, title, description, close (×).
//
// Used by:
//   - UniversalModal (below)
// -----------------------------------------------------------

function ModalHeader({ icon: Icon, iconColor, title, description, hasBody, showCloseButton, onClose }) {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        p: 3,
        pb: description || hasBody ? 2 : 3,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: 1, marginBottom: 1 }}>
        {Icon && (
          <Icon
            color={iconColor}
            sx={{ fontSize: 28 }}
          />
        )}
        <Box>
          {title && (
            <Typography
              id="universal-modal-title"
              variant="h6"
              component="h2"
              sx={{ fontWeight: 600 }}
            >
              {title}
            </Typography>
          )}
          {description && (
            <Typography
              id="universal-modal-description"
              variant="body2"
              color="text.secondary"
              sx={{ mt: 0.5 }}
            >
              {description}
            </Typography>
          )}
        </Box>
      </Box>

      {showCloseButton && (
        <IconButton
          onClick={onClose}
          size="small"
          sx={{
            ml: 1,
            color: 'text.secondary',
            '&:hover': { color: 'error.main' }
          }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      )}
    </Box>
  );
}







// -----------------------------------------------------------
// StandardActions
// -----------------------------------------------------------
//
// Footer bar used when the caller passes no custom `actions`.
//
// Used by:
//   - UniversalModal (below)
// -----------------------------------------------------------

function StandardActions({ showCancel, cancelText, onCancel, showConfirm, confirmText, confirmColor, onConfirm, confirmDisabled, loading }) {
  return (
    <>
      <Divider />
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 1.5,
          p: 2,
          px: 3,
        }}
      >
        {showCancel && (
          <Button
            variant="outlined"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelText}
          </Button>
        )}
        {showConfirm && (
          <Button
            variant="contained"
            color={confirmColor}
            onClick={onConfirm}
            disabled={confirmDisabled || loading}
            startIcon={loading ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {confirmText}
          </Button>
        )}
      </Box>
    </>
  );
}







// -----------------------------------------------------------
// ConfirmModal
// -----------------------------------------------------------
//
// Generic "are you sure?" — default variant, Confirm/Cancel.
//
// Used by:
//   - nothing renders it yet — only re-exported by index.js
// -----------------------------------------------------------

export function ConfirmModal({
  title = "Confirm Action",
  confirmText = "Confirm",
  ...props
}) {
  return (
    <UniversalModal
      title={title}
      confirmText={confirmText}
      showCancel={true}
      {...props}
    />
  );
}







// -----------------------------------------------------------
// DeleteModal
// -----------------------------------------------------------
//
// Delete confirmation — danger variant, irreversible wording.
// The caller supplies onConfirm with the actual delete call.
//
// Used by:
//   - nothing renders it yet — only re-exported by index.js
// -----------------------------------------------------------

export function DeleteModal({
  title = "Delete",
  description = "Are you sure you want to delete? This action is irreversible.",
  confirmText = "Delete",
  ...props
}) {
  return (
    <UniversalModal
      title={title}
      description={description}
      confirmText={confirmText}
      variant="danger"
      {...props}
    />
  );
}







// -----------------------------------------------------------
// AlertModal
// -----------------------------------------------------------
//
// Informational notice — info variant, a single "OK" button
// since there is nothing to cancel.
//
// Used by:
//   - nothing renders it yet — only re-exported by index.js
// -----------------------------------------------------------

export function AlertModal({
  title = "Information",
  confirmText = "OK",
  showCancel = false,
  ...props
}) {
  return (
    <UniversalModal
      title={title}
      confirmText={confirmText}
      showCancel={showCancel}
      variant="info"
      {...props}
    />
  );
}







// -----------------------------------------------------------
// WarningModal
// -----------------------------------------------------------
//
// Warning notice — warning variant, "Understood" confirm.
// Keeps Cancel so the caller can wire onCancel to back out.
//
// Used by:
//   - nothing renders it yet — only re-exported by index.js
// -----------------------------------------------------------

export function WarningModal({
  title = "Warning",
  confirmText = "Understood",
  ...props
}) {
  return (
    <UniversalModal
      title={title}
      confirmText={confirmText}
      variant="warning"
      {...props}
    />
  );
}







// -----------------------------------------------------------
// UniversalModal (default export)
// -----------------------------------------------------------
//
// The dialog itself: an MUI Modal with a centered Paper, the
// flow animation done by hand — flight state, start-pose
// measurement and the delayed unmount all live here.
//
// Used by:
//   - AddEditAdministrator — the administrator dialog: custom
//     `actions`, both stock buttons hidden, closeRef and
//     sourceRect wired
//   - ConfirmModal / DeleteModal / AlertModal / WarningModal
//     (above) — thin prop-filling wrappers
// -----------------------------------------------------------

export default function UniversalModal({
  open,
  onClose,

  title,
  description,
  children,

  // Custom JSX for the button row; replaces the stock pair
  actions,

  confirmText = "Confirm",
  cancelText = "Cancel",
  onConfirm,
  onCancel,
  showCancel = true,
  showConfirm = true,
  confirmDisabled = false,

  variant = "default",

  maxWidth = 500,
  fullWidth = false,

  loading = false,

  closeOnConfirm = true,
  closeOnBackdropClick = true,
  showCloseButton = true,

  // Flow animation origin — the trigger's screen rectangle
  sourceRect = null,

  // Animated close for the consumer's OWN handlers: call
  // closeRef.current() instead of clearing your open-state —
  // the return flight plays first, onClose fires on landing
  closeRef = null,

  sx = {},
  contentSx = {},
}) {

  const variantConfig = VARIANTS[variant] || VARIANTS.default;


  // Flow animation: `entered` drives the transition (start
  // pose → resting pose), `exiting` keeps the modal mounted
  // while the return flight plays after `open` goes false.
  const paperRef = useRef(null);
  const [entered, setEntered] = useState(false);
  const [exiting, setExiting] = useState(false);
  const [flightFrom, setFlightFrom] = useState('translate(-50%, -50%) scale(0.92)');

  // The close must start IN THE SAME RENDER that receives
  // open=false: an effect would leave one frame at
  // mounted=false and MUI would unmount the paper before the
  // return flight can play. Skipped while a requestClose
  // flight runs — that path flips open=false only AFTER
  // landing.
  const closingRef = useRef(false);
  const [prevOpen, setPrevOpen] = useState(open);
  if (open !== prevOpen) {
    setPrevOpen(open);
    if (!open && !closingRef.current) {
      setExiting(true);
      setEntered(false);
    }
  }

  const mounted = open || exiting;

  // Every internal trigger (backdrop, Esc, the header ×,
  // Cancel, closeOnConfirm) flies back FIRST and calls onClose
  // only after landing — most consumers unmount the whole
  // modal on close, which would cut the flight off instantly.
  const requestClose = () => {
    if (closingRef.current) return;
    closingRef.current = true;
    setExiting(true);
    setEntered(false);
    setTimeout(() => {
      onClose?.();
      closingRef.current = false;
    }, FLIGHT_MS);
  };

  if (closeRef) {
    closeRef.current = requestClose;
  }

  // Entering: derive the start pose, then release it a frame
  // later so the transition has something to play. The
  // measurement waits a frame because MUI portals the modal —
  // the paper does not exist when this effect first runs; the
  // paper sits at opacity 0 until `entered`, hiding that frame.
  useLayoutEffect(() => {
    if (!open) return;
    setExiting(false);

    let raf2;
    const raf1 = requestAnimationFrame(() => {
      let start = 'translate(-50%, -50%) scale(0.92)';
      const paper = paperRef.current;
      if (sourceRect && paper) {
        const dx = (sourceRect.left + sourceRect.width / 2) - window.innerWidth / 2;
        const dy = (sourceRect.top + sourceRect.height / 2) - window.innerHeight / 2;
        // UNIFORM scale (the smaller ratio) keeps the modal's
        // proportions in flight instead of stretching it into
        // the source's shape (a grid row would smear it across
        // the screen). offsetWidth/Height are unaffected by the
        // live transform, unlike getBoundingClientRect.
        const scale = Math.min(
          sourceRect.width / paper.offsetWidth,
          sourceRect.height / paper.offsetHeight
        );
        start = `translate(-50%, -50%) translate(${dx}px, ${dy}px) scale(${scale})`;
      }
      setFlightFrom(start);
      raf2 = requestAnimationFrame(() => setEntered(true));
    });

    return () => {
      cancelAnimationFrame(raf1);
      if (raf2) cancelAnimationFrame(raf2);
    };
  }, [open, sourceRect]);

  // Leaving: unmount only once the return flight has landed
  useEffect(() => {
    if (!exiting) return;
    const timer = setTimeout(() => setExiting(false), FLIGHT_MS);
    return () => clearTimeout(timer);
  }, [exiting]);


  // Awaited so closeOnConfirm cannot shut the modal before an
  // async confirm (e.g. an API call) has finished
  const handleConfirm = async () => {
    if (onConfirm) {
      await onConfirm();
    }
    if (closeOnConfirm) {
      requestClose();
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    }
    requestClose();
  };

  // MUI reports why the modal wants to close; Esc still gets
  // through when backdrop clicks are ignored
  const handleBackdropClick = (event, reason) => {
    if (reason === 'backdropClick' && !closeOnBackdropClick) {
      return;
    }
    requestClose();
  };


  const showActionBar = actions || showConfirm || showCancel;


  return (
    <Modal
      open={mounted}
      onClose={handleBackdropClick}
      // Each aria id is set only when ModalHeader will render
      // the Typography node it targets — a missing title or
      // description would otherwise leave a dangling reference
      aria-labelledby={title ? "universal-modal-title" : undefined}
      aria-describedby={description ? "universal-modal-description" : undefined}
      slotProps={{
        backdrop: {
          sx: {
            backgroundColor: 'rgba(0, 0, 0, 0.15)',
            // backdrop-filter ignores the element's own opacity,
            // so the blur is animated explicitly — fading alone
            // would leave the page blurred until unmount
            backdropFilter: entered ? 'blur(6px)' : 'blur(0px)',
            opacity: entered ? 1 : 0,
            transition: `opacity ${FLIGHT_MS}ms ease, backdrop-filter ${FLIGHT_MS}ms ease`,
          },
        },
      }}
    >
      <Paper
        ref={paperRef}
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: entered ? 'translate(-50%, -50%)' : flightFrom,
          opacity: entered ? 1 : 0,
          // No transition while the start pose is being set up —
          // the paper must TELEPORT there, then animate out of it
          transition: entered || exiting
            ? `transform ${FLIGHT_MS}ms cubic-bezier(0.2, 0.8, 0.2, 1), opacity ${FLIGHT_MS}ms ease`
            : 'none',
          width: fullWidth ? '90%' : 'auto',
          maxWidth: maxWidth,
          minWidth: 300,
          maxHeight: '90vh',
          overflow: 'auto',
          borderRadius: 2,
          boxShadow: 24,
          outline: 'none',   // Modal focuses the Paper; hide the focus ring
          ...sx,
        }}
      >
        <ModalHeader
          icon={variantConfig.icon}
          iconColor={variantConfig.iconColor}
          title={title}
          description={description}
          hasBody={Boolean(children)}
          showCloseButton={showCloseButton}
          onClose={requestClose}
        />

        {/* Content */}
        {children && (
          <Box sx={{ px: 3, pb: showActionBar ? 2 : 3, ...contentSx }}>
            {children}
          </Box>
        )}

        {/* Custom actions — block layout allows full-width buttons */}
        {actions && (
          <>
            <Divider />
            <Box sx={{ p: 2, px: 3 }}>
              {actions}
            </Box>
          </>
        )}

        {/* Standard Confirm/Cancel bar — only when no custom actions */}
        {!actions && (showConfirm || showCancel) && (
          <StandardActions
            showCancel={showCancel}
            cancelText={cancelText}
            onCancel={handleCancel}
            showConfirm={showConfirm}
            confirmText={confirmText}
            confirmColor={variantConfig.confirmColor}
            onConfirm={handleConfirm}
            confirmDisabled={confirmDisabled}
            loading={loading}
          />
        )}
      </Paper>
    </Modal>
  );
}
