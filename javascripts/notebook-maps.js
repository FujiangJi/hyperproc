/* Browser-only snapshots: pan/zoom saved maps without starting a kernel. */
(() => {
  const maps = document.querySelectorAll('.notebook-map[data-snapshot]');
  const load = async (element) => {
    if (element.dataset.loaded) return;
    element.dataset.loaded = 'true';
    try {
      const response = await fetch(element.dataset.snapshot);
      if (!response.ok) throw new Error('Map snapshot could not be loaded.');
      const snapshot = await response.json();
      const map = L.map(element, {scrollWheelZoom: false}).setView(snapshot.center, snapshot.zoom);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      }).addTo(map);
      const displayed = [];
      for (const layer of snapshot.layers) {
        let rendered;
        try {
          const style = {color: '#087866', weight: 2, fillOpacity: 0.12};
          if (layer.type === 'geojson') rendered = L.geoJSON(layer.data, {style});
          else if (layer.type === 'marker') rendered = L.circleMarker(layer.location, {...style, radius: 5});
          else if (layer.type === 'polyline') rendered = L.polyline(layer.locations, style);
          else if (layer.type === 'rectangle') rendered = L.rectangle(layer.locations, style);
          else rendered = L.polygon(layer.locations, style);
          if (layer.name) {
            const label = document.createElement('span');
            label.textContent = layer.name;
            rendered.bindTooltip(label);
          }
          if (layer.granule) {
            const granule = layer.granule;
            const popup = document.createElement('div');
            popup.className = 'notebook-granule-popup';
            const title = document.createElement('strong');
            title.textContent = granule.name;
            popup.appendChild(title);
            for (const value of [
              `${granule.sensor} ${granule.level}`,
              granule.time,
              granule.cloud == null ? null : `Cloud: ${granule.cloud}%`,
              granule.size_mb == null ? null : `Size: ${granule.size_mb.toLocaleString()} MB`,
              granule.extent_kind
            ]) if (value) {
              const line = document.createElement('div');
              line.textContent = value;
              popup.appendChild(line);
            }
            if (granule.browse) {
              try {
                const url = new URL(granule.browse);
                if (url.protocol === 'https:' || url.protocol === 'http:') {
                  const link = document.createElement('a');
                  link.href = url.href; link.target = '_blank'; link.rel = 'noopener';
                  link.textContent = 'Open provider quicklook'; popup.appendChild(link);
                }
              } catch (_) { /* Ignore malformed provider links. */ }
            }
            rendered.bindPopup(popup);
          }
          rendered.addTo(map);
          displayed.push({layer, rendered});
        } catch (_) { /* A malformed saved layer must not hide the base map. */ }
      }
      const granules = displayed.filter(item => item.layer.granule);
      let initialBounds;
      if (granules.length) {
        initialBounds = L.featureGroup(granules.map(item => item.rendered)).getBounds();
        map.fitBounds(initialBounds, {padding: [25, 25], maxZoom: 11});
        const controls = document.createElement('div');
        controls.className = 'notebook-granule-controls';
        const label = document.createElement('label');
        const picker = document.createElement('select');
        picker.className = 'notebook-granule-picker';
        picker.id = `granule-picker-${element.id || element.getAttribute('aria-label').replaceAll(' ', '-')}`;
        label.htmlFor = picker.id; label.textContent = `${granules.length} granules`;
        const placeholder = document.createElement('option');
        placeholder.value = ''; placeholder.textContent = 'Choose a granule to inspect its extent…';
        picker.appendChild(placeholder);
        granules.forEach((item, index) => {
          const option = document.createElement('option');
          option.value = String(index);
          option.textContent = item.layer.granule.name;
          picker.appendChild(option);
          item.rendered.on('click', () => { picker.value = String(index); });
        });
        picker.addEventListener('change', () => {
          if (picker.value === '') return;
          const selected = granules[Number(picker.value)];
          if (selected.rendered.getBounds) map.fitBounds(selected.rendered.getBounds(), {padding: [35, 35], maxZoom: 12});
          else map.setView(selected.rendered.getLatLng(), 11);
          selected.rendered.openPopup();
        });
        controls.append(label, picker);
        element.before(controls);
      }
      L.control.scale().addTo(map);
      const reset = L.control({position: 'topright'});
      reset.onAdd = () => {
        const container = L.DomUtil.create('div', 'leaflet-bar');
        const button = L.DomUtil.create('button', 'notebook-map-reset', container);
        button.type = 'button'; button.textContent = 'Reset view';
        button.addEventListener('click', () => {
          map.closePopup();
          if (initialBounds) map.fitBounds(initialBounds, {padding: [25, 25], maxZoom: 11});
          else map.setView(snapshot.center, snapshot.zoom);
        });
        L.DomEvent.disableClickPropagation(container);
        return container;
      };
      reset.addTo(map);
      new ResizeObserver(() => map.invalidateSize()).observe(element);
    } catch (error) {
      element.textContent = `${error.message} Refresh the page after rebuilding the site.`;
    }
  };
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) {
        observer.unobserve(entry.target); load(entry.target);
      }
    }, {rootMargin: '200px'});
    maps.forEach(map => observer.observe(map));
  } else maps.forEach(load);
})();
