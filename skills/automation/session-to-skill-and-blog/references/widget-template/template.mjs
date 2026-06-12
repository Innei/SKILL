// Dynamic widget template — Yohaku article design language.
// Implements the @haklex/rich-dynamic-protocol mount contract in vanilla JS.
// Sample interaction: a parameter explorer (slider → live readout + bars).
// Replace `.stage`/`apply()` internals with your own lesson; keep the
// token map, anatomy, and protocol plumbing. See DESIGN.md for the rules.

const styles = `
.widget {
  /* Self-contained palette — a snapshot of the Yohaku article language.
     Deliberately NOT reading host CSS vars: widgets are immutable versioned
     assets and must not break when the host renames its tokens. Theme is
     switched only via data-theme (pushed through host.theme). */
  --w-text: #24231f;
  --w-text-2nd: #787670;
  --w-border: #e3e1db;
  --w-surface: #f9f8f5;
  --w-accent: #c56473;

  font-family: -apple-system, 'Inter', system-ui, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: var(--w-text);
  border: 1px solid var(--w-border);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-sizing: border-box;
}
.widget[data-theme='dark'] {
  --w-text: #e8e8e8;
  --w-text-2nd: #8f8f8f;
  --w-border: #404040;
  --w-surface: #141414;
  --w-accent: #e095a4;
}
.eyebrow {
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--w-text-2nd);
}
.title {
  font-size: 14px;
  font-weight: 500;
  line-height: 1.57;
}
.stage {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 72px;
}
.bar {
  flex: 1;
  background: color-mix(in srgb, var(--w-accent) 24%, transparent);
  border-radius: 3px 3px 0 0;
  transition: height 200ms ease;
  min-height: 2px;
}
.bar.peak {
  background: var(--w-accent);
}
.controls {
  display: flex;
  align-items: center;
  gap: 8px;
}
input[type='range'] {
  flex: 1;
  accent-color: var(--w-accent);
  min-height: 32px;
}
button.step {
  appearance: none;
  border: 1px solid var(--w-border);
  border-radius: 8px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 13px;
  min-width: 32px;
  min-height: 32px;
  cursor: pointer;
  transition: border-color 200ms ease, background-color 200ms ease;
}
button.step:hover {
  border-color: var(--w-text-2nd);
}
button.step:active {
  transform: translateY(1px);
}
button.step:focus-visible,
input[type='range']:focus-visible {
  outline: 2px solid var(--w-accent);
  outline-offset: 2px;
}
.meta {
  font-size: 12px;
  line-height: 1.5;
  color: var(--w-text-2nd);
  font-variant-numeric: tabular-nums;
}
.meta .readout {
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, monospace;
  color: var(--w-text);
}
.reset {
  appearance: none;
  border: none;
  background: none;
  padding: 0;
  font: inherit;
  font-size: 12px;
  color: var(--w-text-2nd);
  text-decoration: underline dashed;
  text-underline-offset: 4px;
  cursor: pointer;
}
.error {
  font-size: 13px;
  color: var(--w-text-2nd);
}
@media (prefers-reduced-motion: reduce) {
  .bar, button.step {
    transition: none;
  }
}
`;

const BAR_COUNT = 24;

function createWidget(container) {
  const style = document.createElement('style');
  style.textContent = styles;
  container.getRootNode().append(style);

  const el = document.createElement('div');
  el.className = 'widget';
  container.append(el);

  let config = null;
  let value = 0;
  let lastPropsJson = null;

  // Sample lesson: a bell-ish distribution whose spread follows the slider.
  function heights(spread) {
    return Array.from({ length: BAR_COUNT }, (_, i) => {
      const x = (i - BAR_COUNT / 2 + 0.5) / (BAR_COUNT / 2);
      return Math.exp(-(x * x) / Math.max(0.05, spread / 50));
    });
  }

  function render() {
    if (!config) {
      el.innerHTML = `
        <div class="eyebrow">Widget</div>
        <div class="error">Invalid props — expected { title, min, max }.</div>`;
      return;
    }
    el.innerHTML = `
      <div class="eyebrow">Parameter explorer</div>
      <div class="title"></div>
      <div class="stage"></div>
      <div class="controls">
        <button class="step" type="button" data-d="-1" aria-label="decrease">−</button>
        <input type="range" aria-label="parameter" />
        <button class="step" type="button" data-d="1" aria-label="increase">+</button>
      </div>
      <div class="meta"><span class="readout"></span> · drag to feel how the spread reshapes the curve</div>`;

    el.querySelector('.title').textContent = config.title;
    const range = el.querySelector('input[type=range]');
    range.min = config.min;
    range.max = config.max;
    range.value = value;
    update();

    range.addEventListener('input', () => {
      value = Number(range.value);
      update();
    });
    for (const btn of el.querySelectorAll('button.step')) {
      btn.addEventListener('click', () => {
        value = Math.min(config.max, Math.max(config.min, value + Number(btn.dataset.d)));
        range.value = value;
        update();
      });
    }
  }

  function update() {
    const stage = el.querySelector('.stage');
    const hs = heights(value);
    const max = Math.max(...hs);
    stage.innerHTML = hs
      .map((h) => `<div class="bar${h === max ? ' peak' : ''}" style="height:${Math.round(h * 100)}%"></div>`)
      .join('');
    el.querySelector('.readout').textContent = `spread = ${value}`;
  }

  function apply(input) {
    const props = input.props ?? {};
    el.dataset.theme = input.host?.theme === 'dark' ? 'dark' : 'light';

    // theme-only update must not reset interaction state
    const propsJson = JSON.stringify(props);
    if (propsJson === lastPropsJson) return;
    lastPropsJson = propsJson;

    const min = Number.isFinite(Number(props.min)) ? Number(props.min) : 0;
    const max = Number.isFinite(Number(props.max)) ? Number(props.max) : 100;
    config =
      typeof props.title === 'string' && max > min
        ? { title: props.title, min, max }
        : null;
    value = config ? Math.round((min + max) / 2) : 0;
    render();
  }

  return { apply, destroy: () => el.remove() };
}

export default {
  mount(container, input) {
    const widget = createWidget(container);
    widget.apply(input);
    return {
      update(next) {
        widget.apply(next);
      },
      unmount() {
        widget.destroy();
      },
    };
  },
};
