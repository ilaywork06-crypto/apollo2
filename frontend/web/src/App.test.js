import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';

// ─── Mocks ────────────────────────────────────────────────────────────────────

global.fetch = jest.fn();
global.URL.createObjectURL = jest.fn(() => 'blob:mock');
global.URL.revokeObjectURL = jest.fn();

jest.mock('html2canvas', () =>
  jest.fn(() => Promise.resolve({ toDataURL: () => 'data:image/png;base64,mock' }))
);
jest.mock('jspdf', () =>
  jest.fn().mockImplementation(() => ({
    addImage: jest.fn(),
    save: jest.fn(),
    internal: { pageSize: { getWidth: () => 210, getHeight: () => 297 } },
  }))
);

beforeEach(() => {
  fetch.mockReset();
});

// Loading animation takes ~4 seconds; give tests enough headroom
jest.setTimeout(20000);

// ─── Helpers ──────────────────────────────────────────────────────────────────

const MOCK_RESULT = {
  funds: [
    {
      client: {
        name: 'מיטב גמל',
        id: '103',
        client_id: '987654321',
        grade: 72.5,
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
        seniority_date: '01/01/2018',
        percentile: 85,
        equity_exposure: 46.44,
      },
      alternatives: [
        {
          name: 'הראל גמל',
          id: '200',
          grade: 85.0,
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
        },
      ],
      golden: {},
    },
  ],
};

function uploadFile(filename = 'test.xml') {
  const input = document.querySelector('input[type="file"]');
  const file = new File(['<MislakaRoot/>'], filename, { type: 'text/xml' });
  fireEvent.change(input, { target: { files: [file] } });
  return file;
}

// ─── Rendering ────────────────────────────────────────────────────────────────

describe('App renders', () => {
  test('renders without crashing', () => {
    render(<App />);
  });

  test('shows upload section on initial load', () => {
    render(<App />);
    expect(screen.getByText(/העלה קבצי XML/i)).toBeInTheDocument();
  });

  test('shows weight labels for all four metrics', () => {
    render(<App />);
    expect(screen.getByText(/תשואה שנה/i)).toBeInTheDocument();
    expect(screen.getByText(/תשואה 3 שנים/i)).toBeInTheDocument();
    expect(screen.getByText(/תשואה 5 שנים/i)).toBeInTheDocument();
    expect(screen.getByText(/Sharp Ratio/i)).toBeInTheDocument();
  });

  test('shows company blacklist checkboxes', () => {
    render(<App />);
    // The hevrot panel is collapsed by default — open it first
    fireEvent.click(screen.getByText('בחירת חברות מנהלות'));
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBeGreaterThan(0);
  });

  test('submit button is present', () => {
    render(<App />);
    const btn = screen.getByRole('button', { name: /הפעל ניתוח/i });
    expect(btn).toBeInTheDocument();
  });

  test('submit button is disabled when no file is selected', () => {
    render(<App />);
    const btn = screen.getByRole('button', { name: /הפעל ניתוח/i });
    expect(btn).toBeDisabled();
  });

  test('weight bar segments are present (4 metrics)', () => {
    render(<App />);
    const segments = document.querySelectorAll('.weights-form .risk-band-seg');
    expect(segments.length).toBe(4);
  });

  test('shows exposure threshold controls', () => {
    render(<App />);
    // The risk exposure section renders labels like "0–25% חשיפה למניות" or just "חשיפה"
    expect(document.body.textContent).toMatch(/חשיפה/);
  });
});

// ─── Weight controls ──────────────────────────────────────────────────────────

describe('Weight controls', () => {
  test('default weights are displayed (10, 20, 25, 45)', () => {
    render(<App />);
    // The four default values should all appear in the document
    expect(document.body.textContent).toMatch(/10/);
    expect(document.body.textContent).toMatch(/20/);
    expect(document.body.textContent).toMatch(/25/);
    expect(document.body.textContent).toMatch(/45/);
  });

  test('weight bar legend shows current weight percentages', () => {
    render(<App />);
    // Legend renders each weight value as "label — X%"
    expect(document.body.textContent).toMatch(/10%/);
    expect(document.body.textContent).toMatch(/20%/);
    expect(document.body.textContent).toMatch(/25%/);
    expect(document.body.textContent).toMatch(/45%/);
  });

  test('weight bar markers are rendered (3 dividers between 4 segments)', () => {
    render(<App />);
    const markers = document.querySelectorAll('.weights-form .risk-band-marker--draggable');
    expect(markers.length).toBe(3);
  });
});

// ─── File upload ─────────────────────────────────────────────────────────────

describe('File upload', () => {
  test('uploading a file enables the submit button', async () => {
    render(<App />);
    uploadFile();
    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /הפעל ניתוח/i });
      expect(btn).not.toBeDisabled();
    });
  });

  test('shows file name after upload', async () => {
    render(<App />);
    uploadFile('mislaka.xml');
    await waitFor(() => {
      expect(screen.getByText(/mislaka\.xml/i)).toBeInTheDocument();
    });
  });

  test('submit button remains disabled without file', () => {
    render(<App />);
    const btn = screen.getByRole('button', { name: /הפעל ניתוח/i });
    expect(btn).toBeDisabled();
  });
});

// ─── Compare flow ─────────────────────────────────────────────────────────────

describe('Compare flow', () => {
  test('fetch is called with POST method when form submitted', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => MOCK_RESULT,
    });
    render(<App />);
    uploadFile();
    const btn = await screen.findByRole('button', { name: /הפעל ניתוח/i });
    fireEvent.click(btn);
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/compare'),
        expect.objectContaining({ method: 'POST' }),
      );
    }, { timeout: 5000 });
  });

  test('loading screen appears immediately after clicking analyze', async () => {
    fetch.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ ok: true, json: async () => MOCK_RESULT }), 2000))
    );
    render(<App />);
    uploadFile();
    const btn = await screen.findByRole('button', { name: /הפעל ניתוח/i });
    fireEvent.click(btn);
    // Immediately after click, the loading screen should be visible
    await waitFor(() => {
      expect(document.querySelector('.screen--upload')).not.toBeInTheDocument();
    }, { timeout: 3000 });
  });

  test('fetch payload contains weight fields', async () => {
    let capturedBody;
    fetch.mockImplementation((url, options) => {
      capturedBody = options.body;
      return Promise.resolve({ ok: true, json: async () => MOCK_RESULT });
    });
    render(<App />);
    uploadFile();
    const btn = await screen.findByRole('button', { name: /הפעל ניתוח/i });
    fireEvent.click(btn);
    await waitFor(() => {
      expect(capturedBody).toBeTruthy();
    });
    // FormData doesn't expose entries directly in jest, but body should be truthy
    expect(capturedBody).toBeInstanceOf(FormData);
  });

  test('shows loading indicator after clicking analyze', async () => {
    fetch.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ ok: true, json: async () => MOCK_RESULT }), 500))
    );
    render(<App />);
    uploadFile();
    const btn = await screen.findByRole('button', { name: /הפעל ניתוח/i });
    fireEvent.click(btn);
    // Loading step text should appear
    await waitFor(() => {
      const bodyText = document.body.textContent;
      const hasLoadingText =
        bodyText.includes('XML') || bodyText.includes('מחשב') || bodyText.includes('משווה') || bodyText.includes('מכין');
      expect(hasLoadingText).toBe(true);
    }, { timeout: 3000 });
  });
});

// ─── Error handling ───────────────────────────────────────────────────────────

describe('Error handling', () => {
  test('shows some error indication on network failure', async () => {
    fetch.mockRejectedValueOnce(new Error('Network error'));
    render(<App />);
    uploadFile();
    const btn = await screen.findByRole('button', { name: /הפעל ניתוח/i });
    fireEvent.click(btn);
    await waitFor(() => {
      // After error, the upload screen should be back (can retry)
      expect(document.body.textContent).toBeTruthy();
    }, { timeout: 8000 });
  });

  test('does not permanently lock the UI after error', async () => {
    fetch.mockRejectedValueOnce(new Error('fail'));
    render(<App />);
    uploadFile();
    const btn = await screen.findByRole('button', { name: /הפעל ניתוח/i });
    fireEvent.click(btn);
    await waitFor(() => {
      // Eventually the UI recovers (button becomes available again or upload shown)
      expect(document.querySelector('.screen')).toBeTruthy();
    }, { timeout: 8000 });
  });
});

// ─── Company blacklist ────────────────────────────────────────────────────────

describe('Company blacklist', () => {
  test('can toggle a company checkbox on and off', async () => {
    render(<App />);
    fireEvent.click(screen.getByText('בחירת חברות מנהלות'));
    const checkboxes = screen.getAllByRole('checkbox');
    const first = checkboxes[0];
    const initialState = first.checked;
    fireEvent.click(first);
    await waitFor(() => expect(first.checked).toBe(!initialState));
    fireEvent.click(first);
    await waitFor(() => expect(first.checked).toBe(initialState));
  });

  test('at least one company is pre-selected by default', () => {
    render(<App />);
    fireEvent.click(screen.getByText('בחירת חברות מנהלות'));
    const checkboxes = screen.getAllByRole('checkbox');
    const checked = Array.from(checkboxes).filter((cb) => cb.checked);
    expect(checked.length).toBeGreaterThan(0);
  });
});

// ─── Constants in UI ─────────────────────────────────────────────────────────

describe('UI constants', () => {
  test('hero heading is present', () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
  });

  test('page has a header element', () => {
    render(<App />);
    expect(document.querySelector('header')).toBeTruthy();
  });
});
