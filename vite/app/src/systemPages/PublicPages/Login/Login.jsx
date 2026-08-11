// -----------------------------------------------------------
//  [*] Public — Login page
//
//  Opening /login also acts as logout: the session cookie is
//  dropped on mount (see src/session.js).
//
//  A successful login hard-navigates to ?redirectTo (the
//  header appends the page the visitor came from) or to "/" —
//  a full page load rather than a router navigation, so the
//  app restarts with the fresh session and AuthGuard sees it.
//
//  App skips every provider on /login, so the page renders
//  bare and its colors stay hardcoded.
//
//  Used by:
//    - router.jsx — route /login (rendered without a frame)
// -----------------------------------------------------------

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import { Box, Button, FormControl, Stack, TextField, Typography } from "@mui/material";

import { clearSession } from "@/session";
import Particles from './components/Particles/Particles';
import BouncingDotsLoader from './components/BouncingDotsLoader/BouncingDotsLoader';







// -----------------------------------------------------------
// safeRedirectTarget
// -----------------------------------------------------------
//
// Only a path on this site is accepted: anything absolute
// ("https://...") or protocol-relative ("//evil.example")
// falls back to "/", so a crafted /login?redirectTo=... link
// cannot bounce a freshly authenticated visitor off-site.
// -----------------------------------------------------------

function safeRedirectTarget(redirectTo) {
  if (!redirectTo) return '/';
  if (!redirectTo.startsWith('/') || redirectTo.startsWith('//')) return '/';
  return redirectTo;
}







// -----------------------------------------------------------
// Login (default export)
// -----------------------------------------------------------
//
// The white card over the particles background: email and
// password fields (Enter submits too), the backend's error
// text shown verbatim, and a grey loader button while the
// login request runs.
//
// Used by:
//   - router.jsx — route /login (rendered without a frame)
// -----------------------------------------------------------

export default function Login() {

  const [loggingIn, setLoggingIn] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorBoxText, setErrorBoxText] = useState("");

  const [searchParams] = useSearchParams();
  const redirectTo = searchParams.get('redirectTo');


  useEffect(() => {
    clearSession();
  }, []);


  // The backend answers the literal string "OK", or a
  // display-ready error message to put straight in the box.
  async function handleLogin(email, password) {
    setLoggingIn(true);
    try {
      const response = await axios.post("/api/login", { email: email, password: password });
      if (response.data === "OK") {
        window.location.href = safeRedirectTarget(redirectTo);
        return;
      }
      setErrorBoxText(response.data);
    } catch {
      setErrorBoxText("Login failed. Please try again.");
    } finally {
      setLoggingIn(false);
    }
  }


  return (
    <Box className="bg-gradient-to-br from-[#7b4397] to-[#dc2430] top-0 right-0 bottom-0 left-0 -z-2 h-screen overflow-scroll">


      {/* Login Form */}
      <Box className="absolute left-1/2 transform -translate-x-1/2 top-[15%] flex flex-col bg-white p-7 gap-4 rounded-[15px] z-[1] min-w-[350px]">

        <img src='/knf-color.png' alt='' width={250} height={83} className="rounded-2xl" />

        <Box className="text-center mt-2">
          <Typography component="h1" fontSize="1.25em" mb="0.25em">
            <b>Bitcoin LN Statistics</b>
          </Typography>
        </Box>

        <Stack spacing={2} className="mt-2.5 mb-2 text-black">
          <FormControl color="primary">
            <TextField required className="text-black placeholder:text-black"
              variant="standard" label="Email" onChange={(e) => { setEmail(e.currentTarget.value) }} />
          </FormControl>

          <FormControl color="primary">
            <TextField required variant="standard" type="password" label="Password" onKeyDown={(e) => e.key === 'Enter' ? handleLogin(email, password) : ''} onChange={(e) => { setPassword(e.currentTarget.value) }} />
          </FormControl>
        </Stack>


        <Box className="text-xs text-red-500 text-center whitespace-pre-wrap">
          {errorBoxText}
        </Box>

        {loggingIn ?
          <Button disabled={true} style={{ backgroundColor: 'grey', color: 'white', pointerEvents: 'none' }}>
            PLEASE WAIT <BouncingDotsLoader />
          </Button>
          :
          <Button sx={{ backgroundColor: 'rgb(123, 0, 63)', color: 'white' }} onClick={() => { handleLogin(email, password) }}>
            LOGIN
          </Button>
        }
      </Box>


      {/* Particles */}
      <Box className="fixed h-screen"><Particles /></Box>


      {/* Footer */}
      <Box className="h-[100px] w-full absolute bottom-0 flex items-center justify-center">
        <Box className="text-white text-[0.7em] leading-[10px] mt-[50px] text-center">
          Copyright © | All Rights Reserved | Vilnius university Kaunas faculty
        </Box>
      </Box>


    </Box>
  );
}
