import { Footer } from "../components/Footer";
import { Hero } from "../components/landing/Hero";
import { HonestNote } from "../components/landing/HonestNote";
import { HowItWorks } from "../components/landing/HowItWorks";
import { Nav } from "../components/landing/Nav";
import { Proof } from "../components/landing/Proof";

export default function Page() {
  return (
    <>
      <Nav />
      <Hero />
      <Proof />
      <HowItWorks />
      <HonestNote />
      <div className="mx-auto max-w-[1100px] px-5 pb-10 sm:px-8">
        <Footer />
      </div>
    </>
  );
}
