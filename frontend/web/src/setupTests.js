// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

jest.mock('html2canvas', () => jest.fn());
jest.mock('jspdf', () => jest.fn());

// ─── Browser APIs missing from jsdom 16 ──────────────────────────────────────

if (!Blob.prototype.text) {
  Blob.prototype.text = function text() {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsText(this);
    });
  };
}
Object.defineProperty(document, 'fonts', { value: { ready: Promise.resolve() }, configurable: true });

// ─── Per-test mocks (CRA resets mock implementations before every test) ─────

beforeEach(() => {
  global.fetch = jest.fn();
  window.alert = jest.fn();
  window.scrollTo = jest.fn();
  global.URL.createObjectURL = jest.fn(() => 'blob:mock');
  global.URL.revokeObjectURL = jest.fn();

  require('html2canvas').mockImplementation(() =>
    Promise.resolve({ toDataURL: () => 'data:image/jpeg;base64,', width: 794, height: 1123 }),
  );
  require('jspdf').mockImplementation(() => ({ addImage: jest.fn(), addPage: jest.fn(), save: jest.fn() }));
});
