import { Footer } from "../components/Footer";
import { Hero } from "../components/landing/Hero";
import { Nav } from "../components/landing/Nav";
import { Closing, HowItWorks, ReportPreview, WhereToRun } from "../components/landing/Sections";

export default function Page() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <ReportPreview />
        <HowItWorks />
        <WhereToRun />
        <Closing />
      </main>
      <div className="mx-auto max-w-[1120px] px-5 pb-10 sm:px-8">
        <Footer />
      </div>
    </>
  );
}
