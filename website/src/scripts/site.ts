/** Small progressive enhancements. All product data stays local and illustrative. */
const menuButton = document.querySelector<HTMLButtonElement>('.menu-toggle');
const mobileNavigation = document.querySelector<HTMLElement>('#mobile-navigation');
function closeMenu(restoreFocus = false) {
  menuButton?.setAttribute('aria-expanded', 'false');
  menuButton?.setAttribute('aria-label', 'Open navigation');
  if (mobileNavigation) mobileNavigation.hidden = true;
  if (restoreFocus) menuButton?.focus();
}
menuButton?.addEventListener('click', () => {
  const open = menuButton.getAttribute('aria-expanded') !== 'true';
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
  if (mobileNavigation) mobileNavigation.hidden = !open;
});
mobileNavigation
  ?.querySelectorAll('a')
  .forEach((link) => link.addEventListener('click', () => closeMenu()));
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && menuButton?.getAttribute('aria-expanded') === 'true')
    closeMenu(true);
});
window.matchMedia('(min-width: 641px)').addEventListener('change', (event) => {
  if (event.matches) closeMenu();
});

const events = [...document.querySelectorAll<HTMLButtonElement>('[data-event]')];
function selectEvent(button: HTMLButtonElement) {
  events.forEach((event) => {
    event.classList.toggle('selected', event === button);
    event.setAttribute('aria-pressed', String(event === button));
  });
  const fields = {
    'evidence-title': button.dataset.evidenceTitle,
    'evidence-note': button.dataset.evidenceNote,
    'evidence-source': button.dataset.evidenceSource,
    'evidence-ref': button.dataset.evidenceRef,
  };
  for (const [id, value] of Object.entries(fields)) {
    const element = document.getElementById(id);
    if (element) element.textContent = value ?? '';
  }
}
events.forEach((button) => button.addEventListener('click', () => selectEvent(button)));
const filters = [...document.querySelectorAll<HTMLButtonElement>('[data-filter]')];
filters.forEach((button) =>
  button.addEventListener('click', () => {
    filters.forEach((filter) => filter.setAttribute('aria-pressed', String(filter === button)));
    let visible = 0;
    const visibleEvents: HTMLButtonElement[] = [];
    document.querySelectorAll<HTMLElement>('[data-event-group]').forEach((row) => {
      row.hidden =
        button.dataset.filter !== 'all' && row.dataset.eventGroup !== button.dataset.filter;
      if (!row.hidden) {
        visible++;
        const event = row.querySelector<HTMLButtonElement>('[data-event]');
        if (event) visibleEvents.push(event);
      }
    });
    if (
      !visibleEvents.some((event) => event.getAttribute('aria-pressed') === 'true') &&
      visibleEvents[0]
    )
      selectEvent(visibleEvents[0]);
    const count = document.getElementById('event-count');
    if (count) count.textContent = `${visible} events in chronological order`;
  }),
);

const citations = [...document.querySelectorAll<HTMLButtonElement>('[data-citation]')];
const referenceLabels: Record<string, string> = {
  deploy: 'Reference 1 selected · deployment at 09:47',
  error: 'Reference 2 selected · error increase at 09:52',
  incident: 'Reference 3 selected · incident opened at 09:56',
};
citations.forEach((button) =>
  button.addEventListener('click', () => {
    const source = button.dataset.citation ?? '';
    citations.forEach((citation) =>
      citation.setAttribute('aria-pressed', String(citation === button)),
    );
    document
      .querySelectorAll<HTMLElement>('[data-source]')
      .forEach((card) => card.classList.toggle('is-active', card.dataset.source === source));
    const status = document.getElementById('citation-status');
    if (status) status.textContent = referenceLabels[source] ?? '';
    if (window.matchMedia('(max-width: 640px)').matches)
      document.getElementById(`source-${source}`)?.scrollIntoView({
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
          ? 'instant'
          : 'smooth',
        block: 'center',
      });
  }),
);
