// -----------------------------------------------------------
//  [*] GeneralChart — the home page area chart
//
//  A recharts area chart with a brush, fed by the generated
//  JSON under /rawdata. Two data shapes are told apart by
//  data.meta.type: GeneralStatsDataStructure (the default),
//  one entry per block height plotted against time, and
//  ChannelLifetimePlot, one entry per channel age in days.
//  The lifetime branches are dead today: the backend writes
//  that JSON (General_Stats/Channel_Lifetime/) but no page
//  fetches it, so nothing passes the shape here. They stay
//  because wiring one up is a one-line caller change.
//
//  Colors come from the MUI theme, not Tailwind: recharts
//  writes them into SVG attributes, where a CSS variable would
//  not resolve — hence the plain hex values in theme.js.
//
//  Split into (root component last):
//
//    formatBitcoin / formatNodeCount — value formatters
//    CustomTooltip                   — the dark hover card
//    formatYAxisTick                 — 1000 → "1k"
//    GeneralChart                    — the chart (default export)
// -----------------------------------------------------------

import { useId, useMemo } from 'react';
import {
  Area,
  AreaChart,
  Brush,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';
import { useTheme } from '@mui/material/styles';

import PageLoading from '@/components/PageLoading/PageLoading';


// Unit-suffixed values for the tooltip card only — the axes
// keep bare numbers via formatYAxisTick below
const formatBitcoin = (value) => `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} BTC`;
const formatNodeCount = (value) => `${value.toLocaleString()} nodes`;







// -----------------------------------------------------------
// CustomTooltip
// -----------------------------------------------------------
//
// The dark hover card. recharts clones whatever is handed to
// Tooltip's `content` and injects `active` and `payload` — only
// dataKey and data come from the call site.
// -----------------------------------------------------------

function CustomTooltip({ active, payload, dataKey, data }) {

  const theme = useTheme();

  if (active && payload && payload.length) {
    const dataPoint = payload[0].payload;
    const value = payload[0].value;

    const formatValue = (val) => {
      if (dataKey === 'network_capacity') {
        return formatBitcoin(val);
      } else if (dataKey === 'node_count') {
        return formatNodeCount(val);
      }
      return val.toLocaleString();
    };

    if (data?.meta?.type === 'ChannelLifetimePlot') {
      return (
        <div className="bg-gray-800 text-white p-3 rounded-lg shadow-lg border border-gray-600">
          <div className="font-semibold mb-1" style={{ color: theme.palette.primary.accent }}>
            {dataPoint.lifetime_days} days
          </div>
          <div className="text-lg font-bold">
            {formatValue(value)}
          </div>
        </div>
      );
    }

    return (
      <div className="bg-gray-800 text-white p-3 rounded-lg shadow-lg border border-gray-600">
        <div className="font-semibold mb-1" style={{ color: theme.palette.primary.accent }}>
          {dataPoint.date}
        </div>
        <div className="text-lg font-bold">
          {formatValue(value)}
        </div>
        <div className="text-xs text-gray-300 mt-1">
          Block: {dataPoint.blockHeight}
        </div>
      </div>
    );
  }

  return null;
}







// -----------------------------------------------------------
// formatYAxisTick
// -----------------------------------------------------------
//
// Thousands are abbreviated to keep the axis gutter narrow.
// -----------------------------------------------------------

const formatYAxisTick = (value) => {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(0)}k`;
  }
  return value.toLocaleString();
};







// -----------------------------------------------------------
// GeneralChart (default export)
// -----------------------------------------------------------
//
// Normalizes data.data into time-ordered recharts entries
// (memoized), shows the loading filler until they exist, then
// draws the gradient area with brush and custom tooltip.
//
// Used by:
//   - Home — three instances: capacity, node count and
//     channel count over time
// -----------------------------------------------------------

export default function GeneralChart({ data, height = 400, title, dataKey, yAxisLabel }) {

  const theme = useTheme();

  // The gradient is referenced by DOM id and a page mounts
  // several of these charts, so a fixed id would make every one
  // fill from whichever instance rendered first. useId()'s
  // colons are dropped to keep the value safe inside url(#...).
  const gradientId = `chartGradient-${useId().replace(/:/g, '')}`;


  const chartData = useMemo(() => {
    if (!data?.data) return [];

    if (data.meta?.type === 'ChannelLifetimePlot') {
      return Object.entries(data.data)
        .map(([, entry]) => ({
          lifetime_days: entry.lifetime_days,
          [dataKey]: entry[dataKey],
        }))
        .sort((a, b) => a.lifetime_days - b.lifetime_days);
    }

    return Object.entries(data.data)
      .map(([blockHeight, entry]) => ({
        blockHeight,
        timestamp: entry.timestamp,
        date: entry.date,
        [dataKey]: entry[dataKey],
      }))
      .sort((a, b) => a.timestamp - b.timestamp);
  }, [data, dataKey]);


  const formatXAxisTick = (tickItem) => {
    if (data?.meta?.type === 'ChannelLifetimePlot') {
      return `${tickItem}d`;
    }

    const dataPoint = chartData.find(item => item.timestamp === tickItem);
    if (dataPoint && dataPoint.date) {
      return dataPoint.date.substring(0, 7);
    }
    const date = new Date(tickItem * 1000);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    return `${year}-${month}`;
  };


  if (!chartData.length) {
    return (
      <div className="flex h-64 bg-gray-50 rounded-lg">
        <PageLoading label="Loading chart data..." />
      </div>
    );
  }


  // Clicking the chart must not take focus — the brush handles
  // would keep an outline afterwards
  const handleMouseDown = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };


  return (
    <div className="w-full">
      <div className="p-4 bg-gray-50 rounded-lg mb-8">
        <h3 className="text-2xl text-gray-800 mb-4">
          {title}
        </h3>

        <div
          className="bg-white p-4 rounded-lg shadow-sm border"
          onMouseDown={handleMouseDown}
          style={{ outline: 'none' }}
        >
          <ResponsiveContainer width="100%" height={height}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={theme.palette.primary.accent} stopOpacity={0.8} />
                  <stop offset="100%" stopColor={theme.palette.primary.accent} stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#e2e8f0"
                strokeOpacity={0.6}
              />
              <XAxis
                // Both shapes plot a number on x. recharts
                // knows only "number" and "category"; anything
                // else falls back to category, which ignores
                // the domain below and spaces points by index.
                dataKey={data?.meta?.type === 'ChannelLifetimePlot' ? "lifetime_days" : "timestamp"}
                type="number"
                scale="linear"
                domain={['dataMin', 'dataMax']}
                tickFormatter={formatXAxisTick}
                stroke="#64748b"
                fontSize={12}
                tickMargin={8}
                minTickGap={30}
              />
              <YAxis
                tickFormatter={formatYAxisTick}
                stroke="#64748b"
                fontSize={12}
                tickMargin={8}
                label={{
                  value: yAxisLabel,
                  angle: -90,
                  position: 'insideLeft',
                  style: { textAnchor: 'middle', fill: '#64748b', fontSize: '12px' }
                }}
              />
              <Tooltip
                content={<CustomTooltip dataKey={dataKey} data={data} />}
                cursor={{
                  stroke: theme.palette.primary.main,
                  strokeWidth: 1,
                  strokeDasharray: '5 5'
                }}
              />
              <Area
                type="monotone"
                dataKey={dataKey}
                stroke={theme.palette.primary.main}
                strokeWidth={2}
                fill={`url(#${gradientId})`}
                dot={false}
                activeDot={{
                  r: 6,
                  stroke: theme.palette.primary.main,
                  strokeWidth: 2,
                  fill: '#ffffff'
                }}
              />

              {/* Brush for range selection */}
              <Brush
                dataKey={data?.meta?.type === 'ChannelLifetimePlot' ? "lifetime_days" : "timestamp"}
                height={20}
                stroke={theme.palette.primary.main}
                fill="#f8fafc"
                tickFormatter={formatXAxisTick}
                className="recharts-brush"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
