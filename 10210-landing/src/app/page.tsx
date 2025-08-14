import { Banner } from "@/components/Banner";
import { Navbar } from "@/components/Navbar";
import { Hero } from "@/components/Hero";
import { LogoTicker } from "@/components/LogoTicker";
import { CuWhappFeatures } from "@/components/CuWhappFeatures";
import { ProductShowcase } from "@/components/ProductShowcase";
import { CuWhappPricing } from "@/components/CuWhappPricing";
import { BlogSection } from "@/components/BlogSection";
import { FAQs } from "@/components/FAQs";
import { CallToAction } from "@/components/CallToAction";
import { Footer } from "@/components/Footer";


export default function Home() {
  return (
    <>
    <div className="overflow-x-hidden">
      <Banner />
      <Navbar />
      <Hero />
      <LogoTicker />
      
      <CuWhappFeatures />
      
      <ProductShowcase />
      <CuWhappPricing />
      <BlogSection />
      <FAQs />
     
      <CallToAction />
      </div>
      <Footer />
    </>
  );
}
