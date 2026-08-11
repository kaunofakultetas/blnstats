// -----------------------------------------------------------
//  [*] Public — Snapshots page
//
//  Two generated SVGs of how network capacity is spread over
//  the entities: the shares as lines over time, and the sizes
//  as bubbles at one moment. Both are static backend files
//  served from /rawdata.
//
//  The dates are baked into the file paths and into the
//  headings — a new snapshot means editing both.
//
//  Used by:
//    - router.jsx — route /snapshots (inside PublicPageLayout,
//      full width)
// -----------------------------------------------------------

import GeneratedImage from "@/components/GeneratedImage/GeneratedImage";


// The framed look shared by both snapshots.
const IMAGE_CLASS = "m-4 rounded-lg shadow-lg";
const IMAGE_STYLE = {
  maxWidth: '100%',
  height: 'auto',
  padding: '10px',
  backgroundColor: 'white',
};


export default function Snapshots() {
  return (
    <div className="flex flex-col">

      {/* Entities Across Time */}
      <h2>Entities Shares Across Time (Up to 2025-07-01)</h2>
      <p className="text-left mb-4">
        The share of network capacity held by each entity, visualized over time.
      </p>
      <GeneratedImage
        src={"/rawdata/GENERATED/Snapshots/2025-07-01-Lines.svg"}
        alt="Entities shares across time"
        className={IMAGE_CLASS}
        style={IMAGE_STYLE}
      />


      {/* Divider */}
      <div className="w-full border-t border-gray-300 mt-18 mb-8"></div>

      {/* Entities Sizes */}
      <h2>Entities Sizes (At 2025-03-01)</h2>
      <p className="text-left mb-4">
        The share of network capacity held by each entity, visualized at a specific moment in time.
      </p>

      <GeneratedImage
        src={"/rawdata/GENERATED/Snapshots/2025-03-01-Bubles.svg"}
        alt="Entities sizes"
        className={IMAGE_CLASS}
        style={IMAGE_STYLE}
      />

      {/* Divider */}
      <div className="w-full border-t border-gray-300 mt-18 mb-8"></div>

    </div>
  );
}
