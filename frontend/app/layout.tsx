import type { Metadata, Viewport } from "next";
import { Fraunces, Inter, IBM_Plex_Mono } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-fraunces",
  display: "swap",
});
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Práxis · CENAT",
  description: "Copiloto clínico para psicólogos.",
};

// theme-color = porcelana do app: evita faixa clara/azulada da barra do navegador
// (chrome mobile) no topo de telas sem Topbar, como o login (G7).
export const viewport: Viewport = {
  themeColor: "#F8F6F1",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className={`${fraunces.variable} ${inter.variable} ${plexMono.variable}`}>
      <body>
        {children}
        <Toaster
          theme="light"
          position="top-right"
          toastOptions={{
            style: {
              background: "var(--surface)",
              border: "1px solid var(--border)",
              color: "var(--text)",
              borderRadius: "var(--radius-md)",
              boxShadow: "var(--shadow-md)",
              fontFamily: "var(--font-ui)",
            },
          }}
        />
      </body>
    </html>
  );
}
