import { NavigationControl, type IControl } from 'maplibre-gl';
import { cameraMotion } from '@/lib/map-motion';

/** Keep the native draggable compass. Button bursts share a destination so
 * three presses mean three zoom levels even before the first ease finishes. */
export function navigationControl(zoomIn: string, zoomOut: string): IControl {
  const compass = new NavigationControl({ showZoom: false, visualizePitch: true });
  let detach: (() => void) | undefined;
  return {
    onAdd(map) {
      const group = compass.onAdd(map);
      let destination: number | null = null;
      const buttons = ([1, -1] as const).map(step => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = step === 1 ? 'maplibregl-ctrl-zoom-in' : 'maplibregl-ctrl-zoom-out';
        button.title = step === 1 ? zoomIn : zoomOut;
        button.setAttribute('aria-label', button.title);
        const icon = document.createElement('span');
        icon.className = 'maplibregl-ctrl-icon'; icon.setAttribute('aria-hidden', 'true');
        button.append(icon);
        button.onclick = event => {
          const next = Math.max(map.getMinZoom(true), Math.min(map.getMaxZoom(), (destination ?? map.getZoom()) + step));
          map.easeTo({ zoom: next, ...cameraMotion('step'), easeId: 'bangkok-zoom-steps' }, { originalEvent: event });
          destination = map.isZooming() ? next : null;
          sync();
        };
        return button;
      });
      const sync = () => {
        const z = destination ?? map.getZoom();
        buttons[0].disabled = z >= map.getMaxZoom();
        buttons[1].disabled = z <= map.getMinZoom(true);
      };
      // A drag, wheel, keyboard action or another camera command can interrupt
      // the ease. The following press must start at the actual camera then.
      const settled = () => { destination = null; sync(); };
      map.on('moveend', settled); map.on('resize', sync);
      group.prepend(...buttons); sync();
      detach = () => { map.off('moveend', settled); map.off('resize', sync); buttons.forEach(b => b.remove()); };
      return group;
    },
    onRemove() { detach?.(); detach = undefined; compass.onRemove(); },
  };
}
