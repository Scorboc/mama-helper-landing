import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { faq } from '@/data/content';
import { Owl } from '@/components/Critters';

const Faq = () => (
  <section id="faq" className="px-3 py-10 sm:px-5 sm:py-16">
    <div className="mx-auto max-w-[1240px] grid gap-3 lg:grid-cols-[300px_minmax(0,1fr)]">
      <div className="tile flex flex-col justify-between">
        <div>
          <span className="cap mb-1">Вопросы и ответы</span>
          <h2 className="font-heading text-[26px] font-normal leading-[1.15] tracking-[-0.02em] sm:text-[30px]">
            Коротко о важном
          </h2>
        </div>
        <div className="mt-5 grid place-items-center rounded-xl bg-sage-soft py-6">
          <Owl className="h-20 w-20" />
        </div>
      </div>

      <div className="tile">
        <Accordion type="single" collapsible defaultValue="item-0" className="w-full">
          {faq.map((f, i) => (
            <AccordionItem
              key={f.q}
              value={`item-${i}`}
              className="border-b border-inner last:border-0"
            >
              <AccordionTrigger className="text-left font-heading text-[16px] font-medium hover:no-underline">
                {f.q}
              </AccordionTrigger>
              <AccordionContent className="text-[14px] leading-[1.5] text-muted-foreground">
                {f.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </div>
  </section>
);

export default Faq;
