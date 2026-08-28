(() => {
  'use strict';

  const providerEl = document.getElementById('provider');
  let modelEl = document.getElementById('model');
  if (!providerEl || !modelEl) return;

  const customClass = 'custom-model-input';
  const originalPlaceholder = modelEl.getAttribute('placeholder') || 'Select a model';

  function apiKey(provider) {
    return provider ? (localStorage.getItem('aps_' + provider + '_key') || '') : '';
  }

  function replaceWithSelect() {
    if (modelEl.tagName === 'SELECT') return;
    const select = document.createElement('select');
    select.id = 'model';
    select.setAttribute('aria-label', 'AI model');
    select.innerHTML = '<option value="">Loading models…</option>';
    modelEl.replaceWith(select);
    modelEl = select;
  }

  function setLoading(message) {
    replaceWithSelect();
    modelEl.disabled = true;
    modelEl.innerHTML = `<option value="">${message}</option>`;
  }

  function populate(models, selected) {
    replaceWithSelect();
    modelEl.disabled = false;
    modelEl.innerHTML = '';
    const unique = [];
    for (const item of models || []) {
      const id = typeof item === 'string' ? item : item?.id;
      const label = typeof item === 'string' ? item : (item?.label || item?.id);
      if (id && !unique.some(x => x.id === id)) unique.push({ id, label });
    }
    if (!unique.length) {
      modelEl.innerHTML = '<option value="">No models available</option>';
      modelEl.disabled = true;
      return;
    }
    for (const item of unique) {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = item.label;
      modelEl.appendChild(option);
    }
    const preferred = selected && unique.some(x => x.id === selected) ? selected : unique[0].id;
    modelEl.value = preferred;
  }

  async function loadModels() {
    const provider = providerEl.value || 'openai';
    setLoading('Loading models…');
    try {
      const headers = {};
      const key = apiKey(provider);
      if (key) headers['X-Provider-API-Key'] = key;
      const response = await fetch('/api/models?provider=' + encodeURIComponent(provider), { headers });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Could not load models.');
      populate(data.models, data.default_model);
    } catch (error) {
      // Keep the UI usable when a live catalog is temporarily unavailable.
      populate([], '');
      modelEl.innerHTML = '<option value="">Model catalog unavailable</option>';
      modelEl.disabled = true;
      const status = document.getElementById('status');
      if (status) status.textContent = 'Could not load the model list. Check the provider and try again.';
    }
  }

  providerEl.addEventListener('change', loadModels);
  replaceWithSelect();
  loadModels();
})();
