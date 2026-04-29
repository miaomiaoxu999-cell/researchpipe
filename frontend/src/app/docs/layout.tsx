import { DocsSidebar } from "@/components/docs/sidebar";

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex">
      <DocsSidebar />
      <article className="flex-1 px-12 py-12 max-w-[860px] prose-research">
        {children}
      </article>
    </div>
  );
}
