import type { NextConfig } from "next";

// Sin nada que configurar: no hay imagenes remotas, ni redirecciones, ni
// rewrites. El frontend habla con FastAPI por CORS desde el navegador.
const config: NextConfig = {};

export default config;
