import { DashboardSidebar } from "@/components/dashboard/sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex">
      <DashboardSidebar />
      <article className="flex-1 px-12 py-12 max-w-[920px]">{children}</article>
    </div>
  );
}
