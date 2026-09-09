import { fileURLToPath } from 'node:url'
import { dirname } from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const here = dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // The CARTO basemap key is stored unprefixed as CARTO_API_KEY. Vite only
  // exposes VITE_-prefixed vars to client code, and Vercel refuses to store a
  // browser-exposed value under a public framework prefix at all — so the two
  // tools disagree and the key gets injected here instead.
  //
  // This is a naming accommodation, not a privacy measure. The value still
  // ships in the client bundle, because the browser is what requests tiles
  // from CARTO's CDN and must carry the key. CARTO scopes these keys to a
  // registered domain rather than treating them as secrets, which is why
  // exposing it is the intended design and not a leak.
  //
  // process.env covers CI and Vercel (which passes every env var to the
  // build, prefixed or not, and for both Config and Secret types); loadEnv
  // with an empty prefix covers an unprefixed key in a local .env file.
  const fileEnv = loadEnv(mode, here, '')
  const cartoKey = process.env.CARTO_API_KEY ?? fileEnv.CARTO_API_KEY ?? ''

  return {
    plugins: [react()],
    define: {
      __CARTO_API_KEY__: JSON.stringify(cartoKey),
    },
  }
})
