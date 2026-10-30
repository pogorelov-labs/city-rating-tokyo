/** MapLibre initially expands compact attribution after credits arrive. */
export function collapseInitialAttribution(container: HTMLElement): () => void {
  const collapse = () => {
    if (!container.classList.contains('maplibregl-compact-show')) return;
    container.classList.remove('maplibregl-compact-show');
    container.removeAttribute('open');
    observer.disconnect();
  };
  const observer = new MutationObserver(collapse);
  observer.observe(container, { attributes: true, attributeFilter: ['class'] });
  collapse();
  return () => observer.disconnect();
}
