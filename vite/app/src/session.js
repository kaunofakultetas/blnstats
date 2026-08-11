// -----------------------------------------------------------
//  [*] session — dropping the session cookie
//
//  Logout is client-side only: the backend has no logout
//  route, and it marks the session cookie non-httpOnly
//  (SESSION_COOKIE_HTTPONLY = False in blnstats/__init__.py),
//  so document.cookie can expire it.
//
//  Used by:
//    - Header — the Logout button
//    - Login — /login doubles as logout
// -----------------------------------------------------------

export function clearSession() {
  document.cookie = 'session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
}
