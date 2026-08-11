// -----------------------------------------------------------
//  [*] Public — Lorenz Curves page
//
//  Four generated Lorenz curves in two groups: by degree (how
//  many channels a node/entity has) and by weighted degree
//  (the summed capacity of those channels). Each group shows
//  the curve over individual nodes and over the entities they
//  are grouped into.
//
//  Used by:
//    - router.jsx — route /lorenz (inside PublicPageLayout,
//      full width)
// -----------------------------------------------------------

import GeneratedImage from "@/components/GeneratedImage/GeneratedImage";


// One subject ("Nodes" / "Entities") and one metric;
// ?inline=true serves the file for display, not as a download.
const curveUrl = (subject, metric) =>
  `/rawdata/GENERATED/${subject}/${metric}/Lorenz_Curves/20XX-03-01/10x6_Full.svg?inline=true`;


const CURVE_SECTIONS = [
  {
    metric: "degree",
    title: "Degree",
    description: "The degree of a node/entity is the number of channels it has.",
  },
  {
    metric: "weighted_degree",
    title: "Weighted Degree",
    description: "The weighted degree of a node/entity is the sum of the capacities of all its channels.",
  },
];


export default function LorenzCurves() {
  return (
    <div className="flex flex-col">

      {CURVE_SECTIONS.map((section) => (
        <div key={section.metric} className="flex flex-col">
          <h2>{section.title}</h2>
          <p className="text-left mb-4">
            {section.description}
          </p>

          {["Nodes", "Entities"].map((subject) => (
            <GeneratedImage
              key={subject}
              src={curveUrl(subject, section.metric)}
              alt={`Lorenz curve — ${subject.toLowerCase()} by ${section.title.toLowerCase()}`}
              className="m-4 rounded-lg shadow-lg"
              style={{
                maxWidth: '100%',
                height: 'auto'
              }}
            />
          ))}

          {/* Divider */}
          <div className="w-full border-t border-gray-300 mt-18 mb-8"></div>
        </div>
      ))}

    </div>
  );
}
