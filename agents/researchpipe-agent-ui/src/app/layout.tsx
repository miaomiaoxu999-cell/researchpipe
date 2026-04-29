import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ResearchPipe Agent — Chinese Investment Research Chat",
  description: "Ask any Chinese investment-research question. Powered by 14k+ broker reports + qmp deal data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen font-sans">{children}</body>
    </html>
  );
}
