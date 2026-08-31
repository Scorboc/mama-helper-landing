import Header from '@/components/Header';
import Hero from '@/components/Hero';
import Voices from '@/components/Voices';
import Topics from '@/components/Topics';
import HowItWorks from '@/components/HowItWorks';
import Pricing from '@/components/Pricing';
import Reviews from '@/components/Reviews';
import Faq from '@/components/Faq';
import Contacts from '@/components/Contacts';
import Footer from '@/components/Footer';

const Index = () => {
  return (
    <div className="min-h-screen overflow-x-hidden bg-background text-foreground">
      <Header />
      <main>
        <Hero />
        <Voices />
        <Topics />
        <HowItWorks />
        <Pricing />
        <Reviews />
        <Faq />
        <Contacts />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
