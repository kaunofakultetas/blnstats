// -----------------------------------------------------------
//  [*] Public — Data Sources page
//
//  Where the channel announcement data comes from: a Venn
//  diagram of what the two importers (LNResearch and the LND
//  DBReader export) contributed and how much they overlap,
//  then the generated chart of the same comparison over time.
//  Both are generated files served from /rawdata.
//
//  Used by:
//    - router.jsx — route /datasources (inside
//      PublicPageLayout, full width)
// -----------------------------------------------------------

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

import GeneratedImage from "@/components/GeneratedImage/GeneratedImage";
import PageLoading from "@/components/PageLoading/PageLoading";
import VennDiagramChart from './components/VennDiagramChart';


// Both written by the compare-sources import (backend
// blnstats/data_import/compare_sources.py). "20XX-03-01" is a
// literal directory name — "20XX" plus the March x-tick mask —
// not a date to substitute.
const COMPARE_SOURCES_URL = '/rawdata/GENERATED/Compare_Sources/Channel_Announcements/compare_sources.json';
const TIME_SERIES_URL = '/rawdata/GENERATED/Compare_Sources/Channel_Announcements/20XX-03-01/10x6_Full.svg';







// -----------------------------------------------------------
// DataSources (default export)
// -----------------------------------------------------------
//
// Fetches the overlap counts for the Venn diagram — a spinner
// while pending, a red notice on failure — and shows the
// pre-rendered time-series SVG below it.
//
// Used by:
//   - router.jsx — route /datasources (inside
//     PublicPageLayout, full width)
// -----------------------------------------------------------

export default function DataSources() {

  // A generated static file — nothing invalidates it during a
  // visit, so it is fetched once and kept
  const { data: comparisonData = null, isPending, isError } = useQuery({
    queryKey: ['compare-sources'],
    queryFn: async () => (await axios.get(COMPARE_SOURCES_URL)).data,
    staleTime: Infinity,
  });


  return (
    <div className="flex flex-col">

      {/* Header */}
      <h2>Data Sources</h2>
      <p className="text-left mb-6">
        The data sources that were used in the research.
      </p>

      {/* Venn Diagram showing overlap */}
      <div className="mb-8 flex justify-center p-4">
        <div className="w-full">
          {isPending ? (
            <PageLoading label="Loading comparison data..." />
          ) : isError ? (
            <div className="flex justify-center p-8">
              <div className="text-red-500">Failed to load comparison data</div>
            </div>
          ) : (
            <VennDiagramChart data={comparisonData} />
          )}
        </div>
      </div>

      {/* Time series chart */}
      <div className="mb-6">
        <h3 className="text-xl font-semibold mb-4">Data Sources Over Time</h3>
        <GeneratedImage
          src={TIME_SERIES_URL}
          alt="Data Sources Over Time"
          className="m-4 rounded-lg shadow-lg"
          style={{
            maxWidth: '100%',
            height: 'auto'
          }}
        />
      </div>

      {/* Divider */}
      <div className="w-full border-t border-gray-300 mt-8 mb-8"></div>

    </div>
  );
}
