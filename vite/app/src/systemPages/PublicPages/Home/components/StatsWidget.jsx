// -----------------------------------------------------------
//  [*] StatsWidget — one headline number of the home page
//
//  Square card with an icon, a caption, the value and an
//  optional change row (green up, red down) labelled with the
//  dates being compared. Leaving changePercent undefined drops
//  that row entirely rather than filling it with placeholders.
//
//  Used by:
//    - Home — capacity, node count and channel count
// -----------------------------------------------------------

import { Card, Typography } from '@mui/material';


export default function StatsWidget({
  icon: Icon,
  title,
  value,
  changePercent,
  isPositive = true,
  changeLabel
}) {
  return (
    <Card
      className="flex-1 min-w-60 h-52 flex flex-col items-center justify-center text-center p-4"
      elevation={4}
    >
      <Icon color="primary" className="mb-2" sx={{ fontSize: 72 }} />
      <Typography variant="h6" className="mb-1">
        {title}
      </Typography>
      <Typography variant="h4" className="mb-2">
        {value}
      </Typography>
      {changePercent !== undefined && (
        <div className="flex flex-col items-center mt-2">
          <span className={`text-sm font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {isPositive ? '+' : ''}{changePercent}%
          </span>
          <span className="text-gray-500 text-xs ml-1">
            {changeLabel}
          </span>
        </div>
      )}
    </Card>
  );
}
