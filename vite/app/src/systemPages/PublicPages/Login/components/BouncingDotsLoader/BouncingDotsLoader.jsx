// -----------------------------------------------------------
//  [*] BouncingDotsLoader — three bouncing white dots
//
//  Tiny inline wait indicator: an emotion keyframe plus a
//  styled() root, so there is no stylesheet to carry. styled()
//  needs no ThemeProvider either (it falls back to the default
//  theme), which is what lets it work on the bare /login page.
//
//  Used by:
//    - Login — the "PLEASE WAIT" state of the login button
// -----------------------------------------------------------

import { keyframes, styled } from '@mui/material/styles';


// Pairs with the +5px resting transform below: each dot
// swings through the baseline, not only above it.
const bounce = keyframes`
  to { transform: translateY(-5px); }
`;


const Loader = styled('div')({
  display: 'flex',
  justifyContent: 'center',
  marginLeft: 10,

  '& div': {
    width: 5,
    height: 5,
    margin: '1px 2px',
    borderRadius: '50%',
    backgroundColor: 'white',
    opacity: 1,
    animation: `${bounce} 0.6s infinite alternate`,
    transform: 'translateY(5px)',
  },
  '& div:nth-of-type(2)': {
    animationDelay: '0.2s',
  },
  '& div:nth-of-type(3)': {
    animationDelay: '0.3s',
  },
});


export default function BouncingDotsLoader() {
  return (
    <Loader>
      <div></div>
      <div></div>
      <div></div>
    </Loader>
  );
}
