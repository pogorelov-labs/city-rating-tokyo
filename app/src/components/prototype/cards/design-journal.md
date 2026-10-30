# Card prototype design journal

Visual thesis: use the existing Inter typography and blue/navy vocabulary on a
quiet white surface, with one real photograph and readable, aligned data.

Content plan: place and character → rent and chosen commute → differences from
peers → commute bars and actual geography → conditions and source details.

Interaction thesis: immediate area/profile selection, a restrained 240 ms commute
bar transition, and native evidence disclosures. No entrance animation delays
the heading or photograph. Reduced motion removes nonessential transitions.

Tokens: ink `#182b3c`, action blue `#2563eb`, muted text `#586b78`, rule
`#dce3e7`, paper `#f7f8fa`, below-reference accent `#9e453d`. Typography uses the
existing Inter; main headings 42/36/32 px and section headings 24/20 px.

| Date | Observation | Decision |
| --- | --- | --- |
| 2026-10-30 | The previous district opening prioritized unavailable air data and institutional caveats. | Put the place and decision essentials first; retain material qualifications beside the numbers. |
| 2026-10-30 | A radar repeats the ten category rows. | Use one aligned comparison with two explicit values and selectable evidence. |
| 2026-10-30 | At 390 × 844 the first mobile draft placed essentials below the photograph. | Render the same essentials component immediately after the introduction on phones. The visible block now fits above the photo and traits. |
| 2026-10-30 | An unlabeled nested comparison select had an unstable computed name. | Give it an explicit accessible name; category evidence uses native buttons and details. |

The selected composition is implemented in `components/area/`. This prototype
remains a bounded reference; the production components cover the full dataset.
