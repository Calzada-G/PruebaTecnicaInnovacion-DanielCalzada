import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import { Proveedores } from "../lib/proveedores";
import { Navegacion } from "../componentes/Navegacion";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--fuente-plex-sans",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--fuente-plex-mono",
});

export const metadata: Metadata = {
  title: "Ferreteria - Mostrador",
  description: "Inventario compartido y recomendaciones por plaza",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body>
        <Proveedores>
          <Navegacion />
          <main className="mx-auto max-w-[1400px] px-4 py-4">{children}</main>
        </Proveedores>
      </body>
    </html>
  );
}
