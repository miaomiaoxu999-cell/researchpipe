import type { Metadata } from "next";
import { Inter, Source_Serif_4, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const serif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "投研派 ResearchPipe — 投研垂类 API · SDK · MCP",
  description:
    "聚焦投资 / 行研的垂类 API · SDK · MCP，为手搓 Agent 大军而生。Search · Research · Data · Watch 四条产品线，50+ 端点，覆盖一级市场尽调全流程。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className={`${sans.variable} ${serif.variable} ${mono.variable}`}>
      <body className="bg-white text-ink antialiased">
        <Nav />
        <main className="min-h-[calc(100vh-72px)] pt-[72px]">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
