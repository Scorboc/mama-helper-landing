import Header from '@/components/Header';
import Hero from '@/components/Hero';
import Voices from '@/components/Voices';
import HowItWorks from '@/components/HowItWorks';
import Pricing from '@/components/Pricing';
import Footer from '@/components/Footer';
import WhatsNew from '@/components/WhatsNew';

const Index = () => {
  return (
    <div className="landing-page min-h-screen overflow-x-hidden bg-background text-foreground">
      <a className="skip-link" href="#main-content">К основному содержимому</a>
      <Header />
      <main id="main-content" tabIndex={-1}>
        <Hero />
        <Voices />
        <WhatsNew />
        <HowItWorks />
        <Pricing />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
