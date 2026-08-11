// -----------------------------------------------------------
//  [*] VennDiagramChart — overlap of the two channel sources
//
//  Two d3-drawn circles: LNResearch on the left, the LND
//  DBReader export on the right, the shared count in the
//  middle, with the totals repeated as cards below.
//
//  The SVG is wiped and redrawn on every size or data change —
//  a ResizeObserver reports the wrapper width and every radius,
//  offset and font size derives from it. Missing data is not an
//  error: counts fall back to 0 and the diagram renders empty.
//
//  Used by:
//    - DataSources — above the time series
// -----------------------------------------------------------

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';


// Shown until the first ResizeObserver callback arrives
const INITIAL_DIMENSIONS = { width: 800, height: 500 };

const DEFAULT_DATA = {
  "_LNResearch_ChannelAnnouncements": 0,
  "_LND_DBReader_ChannelAnnouncements": 0,
  "overlap": 0
};


export default function VennDiagramChart({ data }) {

  const containerRef = useRef(null);
  const svgRef = useRef(null);
  const [dimensions, setDimensions] = useState(INITIAL_DIMENSIONS);

  const chartData = data || DEFAULT_DATA;

  const lnResearchTotal = chartData["_LNResearch_ChannelAnnouncements"] || 0;
  const lndDbReaderTotal = chartData["_LND_DBReader_ChannelAnnouncements"] || 0;
  const overlapCount = chartData["overlap"] || 0;

  const lnResearchUnique = lnResearchTotal - overlapCount;
  const lndDbReaderUnique = lndDbReaderTotal - overlapCount;

  const totalCount = lnResearchTotal + lndDbReaderTotal - overlapCount;


  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver(entries => {
      for (let entry of entries) {
        const { width } = entry.contentRect;
        // Roughly 8:5; the 48 is the wrapper's own padding
        const height = Math.max(300, width * 0.625);
        setDimensions({ width: Math.max(350, width - 48), height });
      }
    });

    resizeObserver.observe(containerRef.current);

    return () => resizeObserver.disconnect();
  }, []);


  useEffect(() => {
    if (!svgRef.current) return;

    const { width, height } = dimensions;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // The 100/60 margins are label room — the side labels sit
    // outside the circles; the 80px floor stops the drawing
    // collapsing on a narrow phone
    const availableWidth = width - 100;
    const availableHeight = height - 60;
    const maxRadius = Math.min(availableWidth / 3, availableHeight / 2.2);
    const radius = Math.max(80, maxRadius);

    const centerY = height / 2;
    const circleSpacing = radius * 1.2; // > radius keeps the lens narrow
    const leftCenterX = (width / 2) - (circleSpacing / 2);
    const rightCenterX = (width / 2) + (circleSpacing / 2);

    const labelOffset = radius * 0.5;
    const leftLabelX = leftCenterX - labelOffset;
    const rightLabelX = rightCenterX + labelOffset;

    const titleFontSize = Math.max(12, radius / 10);
    const numberFontSize = Math.max(16, radius / 6);
    const subFontSize = Math.max(10, radius / 15);

    const g = svg.append("g");

    g.append("circle")
      .attr("cx", leftCenterX)
      .attr("cy", centerY)
      .attr("r", radius)
      .attr("fill", "rgba(59, 130, 246, 0.5)")
      .attr("stroke", "#3b82f6")
      .attr("stroke-width", Math.max(2, radius / 50));

    g.append("circle")
      .attr("cx", rightCenterX)
      .attr("cy", centerY)
      .attr("r", radius)
      .attr("fill", "rgba(239, 68, 68, 0.5)")
      .attr("stroke", "#ef4444")
      .attr("stroke-width", Math.max(2, radius / 50));

    const leftLabel = g.append("g")
      .attr("transform", `translate(${leftLabelX}, ${centerY})`);

    leftLabel.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", -titleFontSize)
      .style("font-size", `${titleFontSize}px`)
      .style("font-weight", "bold")
      .style("fill", "#1d4ed8")
      .text("LNResearch");

    leftLabel.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", numberFontSize / 3)
      .style("font-size", `${numberFontSize}px`)
      .style("font-weight", "bold")
      .style("fill", "#1d4ed8")
      .text(lnResearchUnique.toLocaleString());

    leftLabel.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", numberFontSize + subFontSize)
      .style("font-size", `${subFontSize}px`)
      .style("fill", "#3b82f6")
      .text("unique");

    const rightLabel = g.append("g")
      .attr("transform", `translate(${rightLabelX}, ${centerY})`);

    rightLabel.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", -titleFontSize)
      .style("font-size", `${titleFontSize}px`)
      .style("font-weight", "bold")
      .style("fill", "#dc2626")
      .text("LND DBReader");

    rightLabel.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", numberFontSize / 3)
      .style("font-size", `${numberFontSize}px`)
      .style("font-weight", "bold")
      .style("fill", "#dc2626")
      .text(lndDbReaderUnique.toLocaleString());

    rightLabel.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", numberFontSize + subFontSize)
      .style("font-size", `${subFontSize}px`)
      .style("fill", "#ef4444")
      .text("unique");

    const overlapLabel = g.append("g")
      .attr("transform", `translate(${width / 2}, ${centerY})`);

    overlapLabel.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", -titleFontSize / 2)
      .style("font-size", `${titleFontSize}px`)
      .style("font-weight", "bold")
      .style("fill", "#374151")
      .text("Overlap");

    overlapLabel.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", numberFontSize)
      .style("font-size", `${numberFontSize}px`)
      .style("font-weight", "bold")
      .style("fill", "#374151")
      .text(overlapCount.toLocaleString());

  }, [dimensions, lnResearchUnique, lndDbReaderUnique, overlapCount]);


  return (
    <div ref={containerRef} className="flex flex-col items-center p-6 bg-white rounded-lg shadow-lg w-full">
      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        className="border rounded w-full h-auto"
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
        preserveAspectRatio="xMidYMid meet"
      />

      <div className="mt-6 flex flex-row justify-center gap-8 text-center w-full">
        <div className="p-4 bg-blue-100 rounded-lg w-[250px]">
          <div className="text-lg text-blue-600 font-medium">LNResearch Total</div>
          <div className="text-3xl font-bold text-blue-700">{lnResearchTotal.toLocaleString()}</div>
        </div>
        <div className="p-4 bg-red-100 rounded-lg w-[250px]">
          <div className="text-lg text-red-600 font-medium">LND DBReader Total</div>
          <div className="text-3xl font-bold text-red-700">{lndDbReaderTotal.toLocaleString()}</div>
        </div>
      </div>

      <div className="mt-6 text-center text-base text-gray-600">
        <div className="p-4 bg-purple-100 rounded-lg w-[250px]">
          <div className="text-lg text-purple-600 font-medium">Overall Total Unique</div>
          <div className="text-3xl font-bold text-purple-700">{totalCount.toLocaleString()}</div>
          <div className="text-sm font-bold text-purple-700">{totalCount > 0 ? ((overlapCount / totalCount) * 100).toFixed(1) : 0}% overlap</div>
        </div>
      </div>

      {/* Only shown when the generated file carries the field */}
      {chartData["updated_at"] && (
        <div className="mt-6 text-center text-base text-gray-600">
          <div className="text-sm text-gray-500">Updated: {chartData["updated_at"]}</div>
        </div>
      )}
    </div>
  );
}
