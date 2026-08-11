// -----------------------------------------------------------
//  [*] GeneratedImage — a chart produced by the backend
//
//  The public pages are galleries of SVGs the Python backend
//  renders into /DATA and Caddy serves under /rawdata. A file
//  only exists once its workflow has run, so each image needs
//  the same "not generated yet" fallback, and the guard makes
//  sure it is applied once: a missing placeholder would
//  otherwise retrigger onError forever. Sizing stays with the
//  caller — the pages frame these images differently — so
//  className and style pass straight through.
//
//  Used by:
//    - Snapshots, Coefficients, LorenzCurves, DataSources
// -----------------------------------------------------------

const FALLBACK_SRC = "/no-data-found.jpeg";







// -----------------------------------------------------------
// GeneratedImage (default export)
// -----------------------------------------------------------
//
// An <img> that swaps itself to the fallback at most once —
// the src guard breaks the onError loop a missing
// placeholder would otherwise cause.
//
// Used by:
//   - Snapshots, Coefficients, LorenzCurves, DataSources
// -----------------------------------------------------------

export default function GeneratedImage({ src, alt, className, style }) {
  return (
    <img
      src={src}
      alt={alt}
      className={className}
      style={style}
      onError={(event) => {
        if (event.target.getAttribute('src') === FALLBACK_SRC) return;
        event.target.src = FALLBACK_SRC;
      }}
    />
  );
}
