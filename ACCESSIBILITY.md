# Accessibility in GallosOS

Accessibility, usability, and responsiveness are baseline design priorities for GallosOS. Contestants should be able to start coding with readable defaults, predictable interactions, and little setup. The goal is one configurable environment that Organizers can adapt to individual needs.

## Priorities and design expectations

GallosOS is designed for competitive programming, including Latin American schools, universities, and training venues with varied equipment, keyboard layouts, and connectivity. Offline operation and restrained resource use are part of making the environment practical in those settings.

Contributors and coding agents should:

- Make text, controls, focus, and status understandable without relying on color alone. Investigate palette choices and verify contrast across interface states.
- Reduce unnecessary choices and configuration steps while keeping necessary accommodations available. Keep quick adjustments close to the task, such as the planned clock display controls and familiar zoom within browsers and IDEs.
- Preserve predictable keyboard operation and readable layouts when text is enlarged. Evaluate the actual applications and desktop, including dialogs and notifications.
- Consider responsiveness alongside readability and input access. Record the image, hardware, workload, and observations before making performance claims.
- Keep implemented behavior, planned capabilities, and tested results distinct. Update this statement and the relevant specifications when support or known barriers change.

The [desktop specification](./docs/WAYLAND_DESKTOP.md) defines detailed controls. [Phase 4](./ROADMAP.md#phase-4-contestant-workstation-features-beta-3) tracks future accessibility and appearance work; accessibility also applies to build instructions, Organizer tools, and project documentation.

## Organizer preparation and individual accommodations

Organizers are responsible for arranging individual accommodations before an event and testing them on the actual GallosOS image, workstation, applications, and event policy. This includes entering Contest mode and confirming that the accommodation remains available after session cleanup. If a barrier is reported during an event, the Organizer is the point of contact for arranging an adjustment.

Organizers may adapt the image and prepare per-workstation settings or accessible controls for a contestant's needs. Examples to evaluate include larger text, visual adjustments, and an individually preferred font such as OpenDyslexic. Choose and test adjustments with the contestant according to their needs.

The design requirement is that approved accommodations survive, or are restored during, Contest transitions while applicable policy validation, integrity protections, and cleanup requirements remain effective. Preparation must preserve the distinction between approved settings and contestant data subject to cleanup, and retain the required transition checks.

Contestants should not need to navigate OS settings before coding. Organizer preparation and simple defaults should handle ordinary setup, while necessary individual adjustments remain possible.

## Current support and known limitations

The commitments above guide development and event preparation. Current support and verification are limited as follows:

- **Appearance:** The current dark palette is temporary, not a final accessibility decision. Research, contrast checks across relevant interface states, graphical evaluation, and an explicit palette decision remain required. No reduction in eye strain is claimed.
- **Time displays:** The generated clock shows hours and minutes; the mode/countdown text is static. Interactive clock views and a live countdown are planned. Giving contestants a choice of time presentation is intended to reduce time pressure; a reduction in anxiety has not been demonstrated.
- **Reading adjustments:** Application zoom does not establish desktop-wide scaling or font replacement in problem PDFs. PDF font customization and OpenDyslexic integration remain unverified; a particular font is not a universal solution. Mozilla documents [zoom controls in Firefox's PDF viewer](https://support.mozilla.org/en-US/kb/view-pdf-files-firefox-or-choose-another-viewer).
- **Accommodation preservation:** A general accommodation configuration interface and automatic preservation mechanism are not yet implemented. The [Contest home reset](./docs/CONFIG_SPEC.md#mode-semantics--behavior-matrix) means changes made only inside the contestant home are not guaranteed to survive. Organizers must verify their prepared adjustments through Contest entry.
- **Assistive technology:** Screen-reader compatibility and a complete set of OS accessibility controls have not been verified. Organizers must assess the actual environment against the contestant's requirements before deployment.
- **Hardware and performance:** Memory recommendations remain provisional, and responsiveness depends on the workstation and workload. See [hardware requirements and acceptance limits](./docs/HARDWARE_COMPATIBILITY.md#2-hardware-requirements-matrix); universal hardware suitability has not been established.
- **Acceptance:** Repository checks establish source and unit evidence only. Booted-image, graphical-session, and physical-hardware acceptance remain separate gates. No OS-wide accessibility conformance is claimed. See the [release-acceptance tracker](./ROADMAP.md#release-acceptance).
- **Project support:** The public issue tracker is for project barriers and improvements, not confidential accommodation arrangements or event support. There is no guaranteed response deadline; event-specific requests belong with the Organizer.

## Reporting barriers and maintaining this statement

For a project accessibility barrier or a suggested improvement, [open a blank issue](https://github.com/CPC-GALLOS/GallosOS/issues/new). A plain-language description of the task you wanted to complete and what prevented it is enough to start. If known, the image version, application, input method, and mode can help investigation; screenshots, recordings, technical diagnostics, and disability disclosure are not required. Do not post private accommodation or medical details in a public issue.

Arrange event-specific accommodations with the Organizer through the event's established channels.

Project maintainers are responsible for keeping this statement current, reviewing reported barriers, identifying workarounds where available, and tracking confirmed work through issues and the roadmap. Contributors should explain the affected tasks, checks performed, remaining barriers, and evidence level when proposing accessibility changes.

This statement follows [GitHub's accessibility statement guidance](https://github.blog/open-source/maintainers/accessibility-statements-now-have-a-home-on-github/). It will evolve as features are implemented and evaluated.
