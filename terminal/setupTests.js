import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// jsdom has no canvas/WebGL renderer. Chart tests inspect the data and layout
// passed to Plotly instead of loading its browser-only rendering engine.
vi.mock("react-plotly.js", () => ({ default: () => null }));

window.URL.createObjectURL = function () {};

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() {
      return false;
    },
  }),
});
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
window.HTMLElement.prototype.scrollIntoView = function () {};
