import { Hero } from "@/components/landing/hero";
import { BuiltFor } from "@/components/landing/built-for";
import { ProductLines } from "@/components/landing/product-lines";
import { UseCases } from "@/components/landing/use-cases";
import { Audience } from "@/components/landing/audience";
import { Pricing } from "@/components/landing/pricing";

export default function HomePage() {
  return (
    <>
      <Hero />
      <BuiltFor />
      <ProductLines />
      <UseCases />
      <Audience />
      <Pricing />
    </>
  );
}
