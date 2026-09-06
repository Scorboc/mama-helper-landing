import Header from '@/components/Header';
import Hero from '@/components/Hero';
import Voices from '@/components/Voices';
import HowItWorks from '@/components/HowItWorks';
import Pricing from '@/components/Pricing';
import Footer from '@/components/Footer';

const Index = () => {
  return (
    <div className="min-h-screen overflow-x-hidden bg-background text-foreground">
      <Header />
      <main>
        <Hero />
        <Voices />
        <HowItWorks />
        <Pricing />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
