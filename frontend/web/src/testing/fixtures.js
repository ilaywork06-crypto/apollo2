// Shared data and helpers for the App test suites.
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';

// ─── Data ────────────────────────────────────────────────────────────────────

export const ALTERNATIVE = {
  name: 'הראל גמל',
  id: '200',
  grade: 85.0,
  has_grade: true,
  rank: 1,
  hevra: 'הראל פנסיה וגמל בע"מ',
  tsua_1: 22.0,
  tsua_3: 14.0,
  tsua_5: 12.0,
  potential_amount: 160000,
  diff: 10000,
  diff_percent: 6.7,
  potential_amount_3: 180000,
  diff_3: 30000,
  diff_percent_3: 20.0,
  potential_amount_5: 210000,
  diff_5: 60000,
  diff_percent_5: 40.0,
  israel_equity_share: 75.0,
  gross: {
    tsua_1: 22.5,
    tsua_3: 14.5,
    tsua_5: 12.5,
    potential_amount: 160800,
    diff: 10800,
    diff_percent: 7.2,
    potential_amount_3: 182000,
    diff_3: 32000,
    diff_percent_3: 21.3,
    potential_amount_5: 214000,
    diff_5: 64000,
    diff_percent_5: 42.7,
  },
};

export const CLIENT = {
  name: 'מיטב גמל',
  id: '103',
  client_id: '987654321',
  grade: 72.5,
  has_grade: true,
  default_grade: 70.0,
  rank: 3,
  total_in_risk: 20,
  risk_level: 'medium',
  amount: 150000,
  dmei_nihul: 0.5,
  tsua_1: 18.98,
  tsua_3: 10.0,
  tsua_5: 9.0,
  hevra: 'מיטב גמל ופנסיה בע"מ',
  seniority_date: '20180101',
  percentile: 85,
  equity_exposure: 46.44,
  israel_equity_share: 20.0,
  liquidity_index: 18.8,
  liquidity_score: 77,
};

export const GOLDEN = {
  ...ALTERNATIVE,
  name: 'אלפא מור תגמולים',
  id: '900',
  grade: 91.0,
  potential_amount: 175000,
  diff: 25000,
  diff_percent: 16.7,
  gross: { ...ALTERNATIVE.gross, potential_amount: 176000, diff: 26000, diff_percent: 17.3, tsua_1: 30.5 },
  tsua_1: 30.0,
};

export const PORTFOLIO = {
  total_amount: 150000,
  holdings_count: 1,
  graded_amount: 150000,
  coverage: 100,
  weighted_score: 72.5,
  potential_score: 85.0,
  weighted_percentile: 85,
  upside: { net: { 1: 10000, 3: 30000, 5: 60000 }, gross: { 1: 10800, 3: 32000, 5: 64000 } },
};

export const holding = ({ client = {}, alternatives = [ALTERNATIVE], golden = {} } = {}) => ({
  client: { ...CLIENT, ...client },
  alternatives,
  golden,
});

export const MOCK_RESULT = { funds: [holding()], portfolio: PORTFOLIO };

export const bulkClient = (id, name, funds, portfolio = {}) => ({
  client_id: id,
  client_name: name,
  files: [`${id}.xml`],
  funds,
  portfolio: { ...PORTFOLIO, ...portfolio },
});

// ─── Helpers ─────────────────────────────────────────────────────────────────

export function mockFetchJson(data) {
  fetch.mockResolvedValueOnce({ ok: true, json: async () => data });
}

export function xmlFile(name = 'test.xml', content = '<MislakaRoot/>') {
  return new File([content], name, { type: 'text/xml' });
}

// Picks files through the first "choose files" input on the page
export function uploadFiles(files) {
  const input = document.querySelector('input[type="file"]');
  fireEvent.change(input, { target: { files } });
}

export function analyzeButton() {
  return screen.getByRole('button', { name: /הפעל ניתוח|נתח את כל הלקוחות/ });
}

export async function goToResults(result = MOCK_RESULT, { before } = {}) {
  mockFetchJson(result);
  render(<App />);
  if (before) await before();
  uploadFiles([xmlFile()]);
  fireEvent.click(analyzeButton());
  await screen.findAllByText('טבלת דירוג — AmoScore', {}, { timeout: 5000 });
}

export async function goToBulk(data, files = [xmlFile('a.xml')]) {
  mockFetchJson(data);
  render(<App />);
  fireEvent.click(screen.getByRole('tab', { name: /ניתוח מרובה לקוחות/ }));
  uploadFiles(files);
  fireEvent.click(analyzeButton());
  await screen.findByText('הלקוחות לפי דחיפות ניוד', {}, { timeout: 5000 });
}

export function lastRequest() {
  const [url, options] = fetch.mock.calls[fetch.mock.calls.length - 1];
  return { url, body: options.body };
}

export async function waitForRequest() {
  await waitFor(() => expect(fetch).toHaveBeenCalled());
  return lastRequest();
}

// Gives an element a 1000px-wide layout box starting at x=0, so a drag to clientX=N means N/10 %
export function stubWidth(element) {
  element.getBoundingClientRect = () => ({ left: 0, top: 0, right: 1000, bottom: 40, width: 1000, height: 40 });
}

export function drag(handle, clientX) {
  fireEvent.mouseDown(handle);
  fireEvent.mouseMove(window, { clientX });
  fireEvent.mouseUp(window);
}

export const rowsText = selector => Array.from(document.querySelectorAll(selector)).map(r => r.textContent);
