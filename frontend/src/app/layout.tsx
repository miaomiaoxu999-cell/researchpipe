import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "投研派 ResearchPipe — 给投资人的 AI 研究助手",
  description:
    "把投研问题变成一份带引用的报告。基于 14,000 多篇 2026 年券商研报与一级市场数据，AI 自动综合，引用清晰，可一键导出。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className={`${sans.variable} ${mono.variable}`}>
      <body className="bg-cream text-ink antialiased min-h-screen">
        <Nav />
        <main className="min-h-[calc(100vh-64px)] pt-[64px]">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
