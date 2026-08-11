// -----------------------------------------------------------
//  [*] Public — Home page
//
//  The network overview: three headline cards (capacity, node
//  count, channel count) with their month-over-month change,
//  and the same three metrics as time series below.
//
//  Everything comes from one generated file served by Caddy,
//  /rawdata/GENERATED/General_Stats/20XX-XX-01.json, keyed by
//  block height. The cards compare its last two keys; a
//  missing file is not an error state, the cards fall back to
//  em dashes and the charts show their own filler.
//
//  Used by:
//    - router.jsx — route / (inside PublicPageLayout)
// -----------------------------------------------------------

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

import CurrencyBitcoinIcon from '@mui/icons-material/CurrencyBitcoin';
import HubIcon from '@mui/icons-material/Hub';
import PolylineIcon from '@mui/icons-material/Polyline';

import StatsWidget from './components/StatsWidget';
import GeneralChart from './components/GeneralChart';


const GENERAL_STATS_URL = '/rawdata/GENERATED/General_Stats/20XX-XX-01.json';







// -----------------------------------------------------------
// percentChange
// -----------------------------------------------------------
//
// A missing or zero baseline yields "0.0" rather than Infinity
// or NaN; callers guard on hasComparison before it matters.
// -----------------------------------------------------------

function percentChange(current, previous) {
  if (previous === 0 || previous === undefined) return "0.0";
  return (((current - previous) / previous) * 100).toFixed(1);
}







export default function Home() {

  // A static generated file — nothing invalidates it mid-visit
  const { data: rawData = null } = useQuery({
    queryKey: ['general-stats'],
    queryFn: async () => (await axios.get(GENERAL_STATS_URL)).data,
    staleTime: Infinity,
  });


  let latest = null, prev = null, lastDate = null, prevDate = null;
  if (rawData && rawData.data) {
    const keys = Object.keys(rawData.data).sort((a, b) => Number(a) - Number(b));
    const lastKey = keys[keys.length - 1];
    const prevKey = keys[keys.length - 2];
    latest = rawData.data[lastKey];
    prev = rawData.data[prevKey];
    lastDate = rawData.data[lastKey]["date"];
    prevDate = rawData.data[prevKey]["date"];
  }

  // Without two snapshots the cards get no changePercent at
  // all, which drops their whole change row — passing the dates
  // blind would print "null vs null" under an invented +0.0%.
  const hasComparison = Boolean(latest && prev);
  const comparisonLabel = hasComparison ? `${lastDate} vs ${prevDate}` : undefined;


  return (
    <div className="flex flex-col items-center justify-center lg:w-[1000px] px-4 lg:px-0">
      <div className="w-full px-4">
        <div className="flex flex-col md:flex-row gap-6">
          <StatsWidget
            icon={CurrencyBitcoinIcon}
            title="Total Network Capacity"
            value={
              latest
                ? `${latest.network_capacity.toLocaleString(undefined, { maximumFractionDigits: 2 })} BTC`
                : "—"
            }
            changePercent={
              hasComparison
                ? percentChange(latest.network_capacity, prev.network_capacity)
                : undefined
            }
            isPositive={hasComparison && latest.network_capacity >= prev.network_capacity}
            changeLabel={comparisonLabel}
          />

          <StatsWidget
            icon={HubIcon}
            title="Total Node Count"
            value={latest ? latest.node_count.toLocaleString() : "—"}
            changePercent={
              hasComparison
                ? percentChange(latest.node_count, prev.node_count)
                : undefined
            }
            isPositive={hasComparison && latest.node_count >= prev.node_count}
            changeLabel={comparisonLabel}
          />

          <StatsWidget
            icon={PolylineIcon}
            title="Total Channel Count"
            value={latest ? latest.channel_count.toLocaleString() : "—"}
            changePercent={
              hasComparison
                ? percentChange(latest.channel_count, prev.channel_count)
                : undefined
            }
            isPositive={hasComparison && latest.channel_count >= prev.channel_count}
            changeLabel={comparisonLabel}
          />
        </div>
      </div>

      {/* Divider */}
      <div className="w-full border-t border-gray-300 m-8"></div>

      <div className="w-full px-4">
        <GeneralChart
          title="Total network capacity in the BLN network"
          yAxisLabel="Total Network Capacity (BTC)"
          data={rawData}
          dataKey="network_capacity"
          height={400}
        />

        <GeneralChart
          title="Total node count in the BLN network"
          yAxisLabel="Total Number of Nodes"
          data={rawData}
          dataKey="node_count"
          height={400}
        />

        <GeneralChart
          title="Total channel count in the BLN network"
          yAxisLabel="Total Number of Channels"
          data={rawData}
          dataKey="channel_count"
          height={400}
        />
      </div>
    </div>
  );
}
