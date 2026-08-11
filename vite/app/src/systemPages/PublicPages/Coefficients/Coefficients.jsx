// -----------------------------------------------------------
//  [*] Public — Coefficients page
//
//  One section per inequality/concentration coefficient: its
//  explanation and two generated charts — over node degree
//  (channel count) and over weighted degree (capacity).
//
//  Chart URLs come from the coefficient name with spaces as
//  underscores: that is how the backend names the generated
//  folders. COEFFICIENT_DESCRIPTIONS holds one unrendered
//  key ("Top 10 Percent Control Sum"); it stays because the
//  backend does generate that folder.
//
//  Split into (root component last):
//
//    AVAILABLE_COEFFICIENTS      — which sections to render
//    COEFFICIENT_DESCRIPTIONS    — the explanation texts
//    chartUrl                    — name → generated SVG path
//    Coefficients                — the page (default export)
//
//  Used by:
//    - router.jsx — route /coefficients (inside
//      PublicPageLayout)
// -----------------------------------------------------------

import GeneratedImage from "@/components/GeneratedImage/GeneratedImage";


const AVAILABLE_COEFFICIENTS = [
  "Gini",
  "HHI",
  "Nakamoto",
  "Normalized Shannon Entropy",
  "Shannon Entropy",
  "Normalized Theil",
  "Theil",
  "Top 10 Percent Control Percentage",
];


const COEFFICIENT_DESCRIPTIONS = {
  "Gini": "The Gini coefficient is a number between 0 and 1 that measures how evenly something—like income, wealth, or resources—is distributed across a group of people. A Gini coefficient of 0 means perfect equality, where everyone has exactly the same amount, while a Gini coefficient of 1 means total inequality, where one person has everything and everyone else has nothing. It's often used to understand economic inequality but can be applied to any situation where distribution matters.",
  "HHI": "The Herfindahl-Hirschman Index (HHI) is a measure of market concentration that shows how evenly or unevenly control is distributed among participants in a market or system. It is calculated by squaring the market share of each participant and then summing those squares. The HHI ranges from close to 0 (very competitive, many small players) to 10,000 (a monopoly, where one player has 100% control). In simple terms, a lower HHI means more decentralization and competition, while a higher HHI means more centralization and dominance by a few players.",
  "Nakamoto": "The Nakamoto coefficient measures the decentralization of a blockchain or distributed system by identifying the minimum number of independent entities required to control over 50% of a critical resource, such as mining power, staked tokens, or voting rights. If this small group colludes, it could potentially disrupt the system by censoring transactions or altering the blockchain's state. A higher Nakamoto coefficient means the system is more decentralized and resistant to such control, while a lower value indicates greater centralization and vulnerability.",
  "Normalized Shannon Entropy": "Shannon entropy is a measure of uncertainty or randomness in a set of outcomes, showing how unpredictable the information is. When normalized between 0 and 1, a value of 0 means no uncertainty (one outcome is certain), and a value of 1 means maximum uncertainty (all outcomes are equally likely). In simple terms, it tells you how evenly distributed or diverse the possibilities are—higher entropy means more diversity and less predictability, while lower entropy means less diversity and more predictability.",
  "Shannon Entropy": "Shannon entropy is a measure from information theory that quantifies the average amount of uncertainty or information contained in a set of possible outcomes. It is calculated by summing the probabilities of each outcome multiplied by the logarithm of their inverse probabilities. The higher the entropy, the more unpredictable or diverse the outcomes are; if one outcome is certain, the entropy is zero because there is no uncertainty. Unlike the normalized version, Shannon entropy is measured in bits (or another log base unit) and depends on the number of possible outcomes and their probabilities, so its value is not limited to a fixed range.",
  "Normalized Theil": "The normalized Theil Index is a version of the Theil Index scaled to range between 0 and 1, where 0 represents perfect equality (everyone has the same share) and 1 indicates maximum inequality (one person has everything). This normalization makes it easier to compare inequality across different populations or datasets by putting all values on a common scale. Like the original Theil Index, it measures how unevenly a resource like income is distributed, but the normalized form provides a clear, standardized way to interpret inequality levels.",
  "Theil": "The Theil Index is a measure of inequality that quantifies how unevenly a resource, like income or wealth, is distributed within a population. It's based on information theory and captures the difference between the actual distribution and perfect equality. A Theil Index of 0 means everyone has the same amount (perfect equality), while higher values indicate greater inequality. One advantage of the Theil Index is that it can be broken down to show inequality within subgroups and between subgroups, helping to identify where disparities come from.",
  "Top 10 Percent Control Percentage": "Calculated to show how much of the network's recources are controlled by the top 10% of nodes.",
  "Top 10 Percent Control Sum": "Calculated to show how much of the network's recources are controlled by the top 10% of nodes.",
};







// -----------------------------------------------------------
// chartUrl
// -----------------------------------------------------------
//
// Path of the generated SVG for one coefficient and metric.
// ?inline=true makes the endpoint serve the file for display
// instead of as a download.
// -----------------------------------------------------------

function chartUrl(coefficient, metric) {
  const folder = coefficient.split(" ").join("_");
  return `/rawdata/GENERATED/EntitiesNodes/${metric}/${folder}/20XX-03-01/6x6_Full.svg?inline=true`;
}


export default function Coefficients() {
  return (
    <div className="flex flex-col">

      {AVAILABLE_COEFFICIENTS.map((coefficient) => (
        <div key={coefficient} className="mb-8 mx-4">
          <h2>{coefficient}</h2>
          <p className="text-justify mb-4" style={{ textJustify: "inter-word" }}>
            {COEFFICIENT_DESCRIPTIONS[coefficient]}
          </p>

          <div className="flex flex-col gap-6 min-w-0 md:flex-row">
            <div className="basis-full md:basis-1/2 flex justify-center items-center">
              <GeneratedImage
                src={chartUrl(coefficient, "degree")}
                alt="Node Count"
                className="rounded-lg shadow-lg max-w-full h-auto"
                style={{ width: "100%", height: "auto" }}
              />
            </div>
            <div className="basis-full md:basis-1/2 flex justify-center items-center">
              <GeneratedImage
                src={chartUrl(coefficient, "weighted_degree")}
                alt="Network Capacity"
                className="rounded-lg shadow-lg max-w-full h-auto"
                style={{ width: "100%", height: "auto" }}
              />
            </div>
          </div>

          {/* Divider */}
          <div className="w-full border-t border-gray-300 mt-18"></div>
        </div>
      ))}

    </div>
  );
}
