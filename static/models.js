(() => {
  'use strict';

  const providerEl = document.getElementById('provider');
  let modelEl = document.getElementById('model');
  if (!providerEl || !modelEl) return;

  const FALLBACK_MODELS = {
    openai: ['gpt-4o-mini'],
    openrouter: ['openrouter/free', 'openai/gpt-4o-mini'],
    nvidia: ['meta/llama-3.1-8b-instruct']
  };
  let requestId = 0;

  function apiKey(provider) {
    return provider ? (localStorage.getItem('aps_' + provider + '_key') || '') : '';
  }

  function ensureSelect() {
    if (modelEl && modelEl.tagName === 'SELECT') return modelEl;
    const old = modelEl;
    const select = document.createElement('select');
    select.id = 'model';
    select.name = old?.name || 'model';
    select.className = old?.className || '';
    select.setAttribute('aria-label', 'AI model');
    old?.replaceWith(select);
    modelEl = select;
    return select;
  }

  function setOptions(models, selected, disabled = false) {
    const select = ensureSelect();
    const unique = [];
    for (const item of models || []) {
      const id = typeof item === 'string' ? item : item?.id;
      const label = typeof item === 'string' ? item : (item?.label || item?.id);
      if (id && !unique.some(x => x.id === id)) unique.push({ id, label });
    }

    select.innerHTML = '';
    for (const item of unique) {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = item.label;
      select.appendChild(option);
    }

    if (!unique.length) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = 'No models available';
      select.appendChild(option);
    }

    const preferred = selected && unique.some(x => x.id === selected)
      ? selected
      : unique[0]?.id || '';
    select.value = preferred;
    select.disabled = disabled || !unique.length;
    return select;
  }

  async function loadModels() {
    const provider = providerEl.value || 'openai';
    const currentRequest = ++requestId;
    const fallback = FALLBACK_MODELS[provider] || [];
    const select = ensureSelect();
    const previous = select.value;
    select.disabled = true;
    select.innerHTML = '<option value="">Loading models…</option>';

    try {
      const headers = {};
      const key = apiKey(provider);
      if (key) headers['X-Provider-API-Key'] = key;

      const response = await fetch(
        '/api/models?provider=' + encodeURIComponent(provider),
        { headers, cache: 'no-store' }
      );
      const data = await response.json().catch(() => ({}));

      if (currentRequest !== requestId) return;
      if (!response.ok) throw new Error(data.error || 'Could not load models.');

      const models = Array.isArray(data.models) && data.models.length
        ? data.models
        : fallback;
      setOptions(models, data.default_model || previous);
    } catch (error) {
      if (currentRequest !== requestId) return;
      // Never leave the selector blank because live discovery failed.
      setOptions(fallback, previous);
      select.title = fallback.length
        ? 'Live model discovery unavailable; showing the provider fallback list.'
        : 'No model fallback is configured for this provider.';
      const status = document.getElementById('status');
      if (status && fallback.length) {
        status.textContent = 'Live model discovery unavailable; using the provider fallback list.';
        window.setTimeout(() => {
          if (status.textContent.startsWith('Live model discovery unavailable')) status.textContent = '';
        }, 2500);
      }
    }
  }

  providerEl.addEventListener('change', loadModels);
  ensureSelect();
  loadModels();
})();
