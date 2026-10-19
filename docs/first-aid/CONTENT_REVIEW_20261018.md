# First aid content update — 2026-10-18

Scope: the shared FirstAid component used by the public page and the account.
This records a source comparison, not a clinician's approval or certification.
The four existing scenarios and the selected site design are retained.
The call links are Russia-specific 112 and 103.

## Sources and decisions

- [RCUK paediatric life support, 2025](https://www.resus.org.uk/professional-library/2025-resuscitation-guidelines/paediatric-basic-life-support-guidelines): early call for an unresponsive child, airway assessment, initial breaths, ratio choice, infant hand technique, AED and foreign-body obstruction. Use this European protocol consistently; do not combine it with the different AHA sequence for an unresponsive choking infant.
- [NHS child resuscitation](https://www.nhs.uk/baby/first-aid-and-safety/first-aid/how-to-resuscitate-a-child/): parent-facing explanations of breaths, compression rate and depth. Its older two-finger infant hand technique is not copied; use RCUK 2025 instead.
- [St John Ambulance recovery position](https://www.sja.org.uk/first-aid-advice/recovery-position/): suspected spinal injury is not an automatic instruction to roll; airway protection takes priority if it cannot otherwise be maintained.
- [St John Ambulance child choking](https://www.sja.org.uk/first-aid-advice/child-choking/): effective cough versus obstruction needing intervention, older-child positioning and follow-up. Use RCUK 2025 for the early-call timing and infant technique.
- [RCUK first aid, 2025](https://www.resus.org.uk/professional-library/2025-resuscitation-guidelines/first-aid-guidelines): escalating bleeding control, manufactured tourniquet placement, time record and no lay release.
- [British Red Cross baby and child burns](https://www.redcross.org.uk/first-aid/learn-first-aid-for-babies-and-children/burns): local cooling, avoiding whole-body cold exposure, concurrent emergency call, medical advice for a child's burn.
- [NHS burns and scalds](https://www.nhs.uk/conditions/burns-and-scalds/): removing only non-adherent items and laying a covering without wrapping the limb.

Do not present these first-aid actions as diagnosis or as a replacement for dispatcher instructions and hands-on training. No AI responses, medicines, new emergency scenarios or changes to personal data are introduced.

## Acceptance checks

Build and TypeScript check; both rendered routes; 320px and 390px mobile layout;
all four native disclosure cards; readable ordered steps; direct call-link targets;
choking-to-CPR link opens its target card; no account needed for the public route;
no external AI call; published resource identity and Pages build status.

Evidence and rollback are saved in the task outputs folder. Physical phone and
clinical simulation checks are not represented by browser viewport checks.
