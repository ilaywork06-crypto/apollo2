// Upload screen: settings, files, the request that is sent, and error recovery.
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import App from './App';
import {
  MOCK_RESULT, analyzeButton, drag, goToResults, mockFetchJson, stubWidth, uploadFiles, waitForRequest, xmlFile,
} from './testing/fixtures';

jest.setTimeout(20000);

const legend = () => document.querySelector('.weights-form .risk-band-legend').textContent;
const weightMarkers = () => document.querySelectorAll('.weights-form .risk-band-marker--draggable');
const openStep = (label) => fireEvent.click(screen.getByText(label));

async function submit() {
  mockFetchJson(MOCK_RESULT);
  uploadFiles([xmlFile()]);
  fireEvent.click(analyzeButton());
  return waitForRequest();
}

// ─── Initial state ───────────────────────────────────────────────────────────

describe('Initial upload screen', () => {
  test('offers file and folder pickers', () => {
    render(<App />);
    expect(screen.getByRole('button', { name: /בחירת קבצים/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /בחירת תיקייה/ })).toBeInTheDocument();
    expect(document.querySelector('input[webkitdirectory]')).toBeTruthy();
  });

  test('analyze is disabled until a file is chosen', () => {
    render(<App />);
    expect(analyzeButton()).toBeDisabled();
    expect(screen.getByText(/העלה לפחות קובץ אחד/)).toBeInTheDocument();
  });

  test('five weights with the new defaults (Sharpe 35%, liquidity 10%)', () => {
    render(<App />);
    expect(document.querySelectorAll('.weights-form .risk-band-seg')).toHaveLength(5);
    expect(weightMarkers()).toHaveLength(4);
    expect(legend()).toMatch(/תשואה שנה — 10%/);
    expect(legend()).toMatch(/תשואה 3 שנים — 20%/);
    expect(legend()).toMatch(/תשואה 5 שנים — 25%/);
    expect(legend()).toMatch(/Sharp Ratio — 35%/);
    expect(legend()).toMatch(/מדד נזילות — 10%/);
    expect(screen.queryByRole('button', { name: /איפוס/ })).not.toBeInTheDocument();
  });

  test('risk bands default to 25% / 75%', () => {
    render(<App />);
    const editor = document.querySelector('.risk-band-editor');
    expect(editor.textContent).toMatch(/נמוך — 0%–25% חשיפה/);
    expect(editor.textContent).toMatch(/בינוני — 25%–75% חשיפה/);
  });

  test('collapsible steps start closed', () => {
    render(<App />);
    expect(document.querySelector('.geo-editor')).toBeNull();
    expect(document.querySelector('.hevrot-checklist')).toBeNull();
    expect(document.querySelector('.aggregate-toggle-row')).toBeNull();
  });
});

// ─── The request ─────────────────────────────────────────────────────────────

describe('Request sent on analyze', () => {
  test('carries every setting with its default', async () => {
    render(<App />);
    const { url, body } = await submit();
    expect(url).toBe('http://localhost:8000/compare');
    expect(Object.fromEntries(['weight_1', 'weight_3', 'weight_5', 'weight_sharp', 'weight_liquidity',
      'low_exposure_threshold', 'medium_exposure_threshold', 'israel_share_min', 'israel_share_max']
      .map(k => [k, body.get(k)]))).toEqual({
      weight_1: '10', weight_3: '20', weight_5: '25', weight_sharp: '35', weight_liquidity: '10',
      low_exposure_threshold: '25', medium_exposure_threshold: '75', israel_share_min: '0', israel_share_max: '100',
    });
    expect(body.getAll('mislaka_file').map(f => f.name)).toEqual(['test.xml']);
    expect(body.getAll('bad_hevrot')).toHaveLength(6);
    expect(body.has('override_risk_level')).toBe(false);
  });

  test('an unchecked company is excluded and a checked one is not', async () => {
    render(<App />);
    openStep('בחירת חברות מנהלות');
    const checklist = document.querySelector('.hevrot-checklist');
    fireEvent.click(within(checklist).getByLabelText('מיטב גמל ופנסיה בע"מ'));
    fireEvent.click(within(checklist).getByLabelText('סלייס גמל בע"מ'));
    const { body } = await submit();
    expect(body.getAll('bad_hevrot')).toContain('מיטב גמל ופנסיה בע"מ');
    expect(body.getAll('bad_hevrot')).not.toContain('סלייס גמל בע"מ');
  });

  test('"select all" clears the exclusion list', async () => {
    render(<App />);
    openStep('בחירת חברות מנהלות');
    fireEvent.click(screen.getByLabelText('בחר / בטל הכל'));
    const { body } = await submit();
    expect(body.getAll('bad_hevrot')).toEqual([]);
  });
});

// ─── Weights ─────────────────────────────────────────────────────────────────

describe('Dragging the AmoScore weights', () => {
  const renderWeights = () => {
    render(<App />);
    stubWidth(document.querySelector('.weights-form .risk-band-bar-wrap'));
  };

  test('moving the Sharpe/liquidity divider trades weight between just those two', async () => {
    renderWeights();
    drag(weightMarkers()[3], 800); // 90% -> 80%
    expect(legend()).toMatch(/Sharp Ratio — 25%/);
    expect(legend()).toMatch(/מדד נזילות — 20%/);
    expect(legend()).toMatch(/תשואה 5 שנים — 25%/);
    const { body } = await submit();
    expect([body.get('weight_sharp'), body.get('weight_liquidity')]).toEqual(['25', '20']);
  });

  test('a divider cannot pass its neighbours', () => {
    renderWeights();
    drag(weightMarkers()[3], 100); // would cross the 5Y divider at 55%
    expect(legend()).toMatch(/Sharp Ratio — 0%/);
    expect(legend()).toMatch(/מדד נזילות — 45%/);
    drag(weightMarkers()[0], 1200); // beyond the bar: stops at the next divider (30%)
    expect(legend()).toMatch(/תשואה שנה — 30%/);
    expect(legend()).toMatch(/תשואה 3 שנים — 0%/);
  });

  test('weights always total 100% and can be reset', () => {
    renderWeights();
    drag(weightMarkers()[1], 400);
    drag(weightMarkers()[2], 700);
    const values = legend().match(/— (\d+)%/g).map(s => Number(s.match(/\d+/)[0]));
    expect(values.reduce((a, b) => a + b, 0)).toBe(100);
    fireEvent.click(screen.getByRole('button', { name: /איפוס/ }));
    expect(legend()).toMatch(/Sharp Ratio — 35%/);
  });
});

// ─── Risk bands ──────────────────────────────────────────────────────────────

describe('Risk bands', () => {
  test('dragging the thresholds changes the request', async () => {
    render(<App />);
    stubWidth(document.querySelector('.risk-band-editor .risk-band-bar-wrap'));
    const [low, medium] = document.querySelectorAll('.risk-band-editor .risk-band-marker--draggable');
    drag(low, 400);      // 40% of 130 -> 52
    drag(medium, 700);   // 70% of 130 -> 91
    expect(document.querySelector('.risk-band-editor').textContent).toMatch(/נמוך — 0%–52% חשיפה/);
    const { body } = await submit();
    expect([body.get('low_exposure_threshold'), body.get('medium_exposure_threshold')]).toEqual(['52', '91']);
  });

  test('clicking a band compares against it; clicking again cancels', async () => {
    render(<App />);
    const high = document.querySelector('.risk-band-seg--high');
    fireEvent.click(high);
    expect(screen.getByText(/השוואה לקבוצת סיכון גבוה/)).toBeInTheDocument();
    fireEvent.click(high);
    fireEvent.click(document.querySelector('.risk-band-seg--low'));
    const { body } = await submit();
    expect(body.get('override_risk_level')).toBe('low');
  });
});

// ─── Israel / abroad ─────────────────────────────────────────────────────────

describe('Israel / abroad equity filter', () => {
  const renderGeo = () => {
    render(<App />);
    openStep('מניות ישראל / חו״ל');
  };
  const summary = () => document.querySelector('.geo-summary').textContent;
  const geoMarkers = () => document.querySelectorAll('.geo-editor .risk-band-marker--draggable');

  test('no preference by default', () => {
    renderGeo();
    expect(summary()).toMatch(/ללא העדפה/);
    expect(screen.getByRole('button', { name: 'ללא העדפה' })).toHaveClass('active');
  });

  test.each([
    ['מוטה ישראל', '60', '100', /ישראל 60%–100% ממרכיב המניות · חו״ל 0%–40%/],
    ['מאוזן', '30', '70', /ישראל 30%–70%/],
    ['מוטה חו״ל', '0', '40', /ישראל 0%–40% ממרכיב המניות · חו״ל 60%–100%/],
  ])('preset "%s" sends %s–%s', async (preset, min, max, text) => {
    renderGeo();
    fireEvent.click(screen.getByRole('button', { name: preset }));
    expect(summary()).toMatch(text);
    const { body } = await submit();
    expect([body.get('israel_share_min'), body.get('israel_share_max')]).toEqual([min, max]);
  });

  test('handles keep at least 5 points apart', async () => {
    renderGeo();
    stubWidth(document.querySelector('.geo-editor .risk-band-bar-wrap'));
    const [min, max] = geoMarkers();
    drag(min, 700);
    drag(max, 710);
    expect(summary()).toMatch(/ישראל 70%–75%/);
    drag(min, 900);
    expect(summary()).toMatch(/ישראל 70%–75%/);
    const { body } = await submit();
    expect([body.get('israel_share_min'), body.get('israel_share_max')]).toEqual(['70', '75']);
  });

  test('closed step shows the active range and can be reset', () => {
    renderGeo();
    fireEvent.click(screen.getByRole('button', { name: 'מוטה חו״ל' }));
    openStep('מניות ישראל / חו״ל');
    expect(document.querySelector('.step-card-chip').textContent).toMatch(/ישראל 0%–40%/);
    fireEvent.click(screen.getAllByRole('button', { name: /איפוס/ })[0]);
    expect(document.querySelector('.step-card-chip')).toBeNull();
  });
});

// ─── Files ───────────────────────────────────────────────────────────────────

describe('Choosing files', () => {
  test('XML and DAT files are accepted, anything else is refused', () => {
    render(<App />);
    uploadFiles([xmlFile('a.xml'), new File(['x'], 'b.DAT'), new File(['x'], 'c.pdf')]);
    expect(screen.getByText(/a\.xml/)).toBeInTheDocument();
    expect(screen.getByText(/b\.DAT/)).toBeInTheDocument();
    expect(screen.queryByText(/c\.pdf/)).not.toBeInTheDocument();
    uploadFiles([new File(['x'], 'd.pdf')]);
    expect(window.alert).toHaveBeenCalledWith('ניתן להעלות קבצי XML ו-DAT בלבד.');
  });

  test('picking the same file twice lists it once', () => {
    render(<App />);
    const file = xmlFile('same.xml');
    uploadFiles([file]);
    uploadFiles([file]);
    expect(screen.getAllByText(/same\.xml/)).toHaveLength(1);
    expect(screen.getByText('1 קובץ נטען')).toBeInTheDocument();
  });

  test('files can be removed one by one or all at once', () => {
    render(<App />);
    uploadFiles([xmlFile('a.xml'), xmlFile('b.xml')]);
    fireEvent.click(screen.getAllByRole('button', { name: '✕' })[0]);
    expect(screen.queryByText(/a\.xml/)).not.toBeInTheDocument();
    expect(screen.getByText(/b\.xml/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'נקה הכל' }));
    expect(analyzeButton()).toBeDisabled();
  });

  test('the file viewer shows the XML tree and returns to the upload screen', async () => {
    render(<App />);
    uploadFiles([xmlFile('v.xml', '<Root><Client><ID>123</ID></Client></Root>')]);
    fireEvent.click(screen.getByRole('button', { name: /הצג קובץ/ }));
    await screen.findByText('תצוגת קובץ XML');
    expect(screen.getByText('Client')).toBeInTheDocument();
    expect(screen.getByText('123')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '→ חזרה' }));
    expect(screen.getByText(/v\.xml/)).toBeInTheDocument();
  });
});

describe('Single / many-clients mode', () => {
  const bulkTab = () => screen.getByRole('tab', { name: /ניתוח מרובה לקוחות/ });
  const singleTab = () => screen.getByRole('tab', { name: /לקוח בודד/ });

  test('each mode keeps its own files', () => {
    render(<App />);
    uploadFiles([xmlFile('mine.xml')]);
    fireEvent.click(bulkTab());
    expect(bulkTab()).toHaveAttribute('aria-selected', 'true');
    expect(screen.queryByText(/mine\.xml/)).not.toBeInTheDocument();
    expect(analyzeButton()).toHaveTextContent('נתח את כל הלקוחות');
    uploadFiles([xmlFile('theirs.xml')]);
    fireEvent.click(singleTab());
    expect(screen.getByText(/mine\.xml/)).toBeInTheDocument();
    expect(screen.queryByText(/theirs\.xml/)).not.toBeInTheDocument();
  });

  test('a long bulk list is shortened and can be expanded', () => {
    render(<App />);
    fireEvent.click(bulkTab());
    uploadFiles(Array.from({ length: 15 }, (_, i) => xmlFile(`client-${i}.xml`)));
    expect(document.querySelectorAll('.file-list-item')).toHaveLength(12);
    fireEvent.click(screen.getByRole('button', { name: /ועוד 3 קבצים — הצג הכל/ }));
    expect(document.querySelectorAll('.file-list-item')).toHaveLength(15);
    expect(screen.getByText(/מוכן לניתוח של 15 קבצים/)).toBeInTheDocument();
  });

  test('bulk mode posts to the bulk endpoint with the same settings', async () => {
    render(<App />);
    fireEvent.click(bulkTab());
    mockFetchJson({ clients: [], errors: [], skipped: [], files_received: 2 });
    uploadFiles([xmlFile('a.xml'), xmlFile('b.xml')]);
    fireEvent.click(analyzeButton());
    const { url, body } = await waitForRequest();
    expect(url).toBe('http://localhost:8000/compare/bulk');
    expect(body.getAll('mislaka_file').map(f => f.name)).toEqual(['a.xml', 'b.xml']);
    expect(body.get('weight_liquidity')).toBe('10');
  });
});

// ─── Errors ──────────────────────────────────────────────────────────────────

describe('Error recovery', () => {
  test.each([
    ['a network failure', () => fetch.mockRejectedValueOnce(new Error('offline'))],
    ['a server error', () => fetch.mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({}) })],
  ])('after %s the user is told and can retry with the same files', async (_, failWith) => {
    render(<App />);
    failWith();
    uploadFiles([xmlFile('keep.xml')]);
    fireEvent.click(analyzeButton());
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith('שגיאה בניתוח הנתונים. אנא בדוק שהשרת פועל ונסה שוב.'));
    expect(screen.getByText(/keep\.xml/)).toBeInTheDocument();
    expect(analyzeButton()).not.toBeDisabled();
  });

  test('a failed bulk run returns to bulk mode', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('tab', { name: /ניתוח מרובה לקוחות/ }));
    fetch.mockRejectedValueOnce(new Error('offline'));
    uploadFiles([xmlFile('x.xml')]);
    fireEvent.click(analyzeButton());
    await waitFor(() => expect(window.alert).toHaveBeenCalled());
    expect(screen.getByRole('tab', { name: /ניתוח מרובה לקוחות/ })).toHaveAttribute('aria-selected', 'true');
  });

  test('the loading screen is shown while waiting', async () => {
    render(<App />);
    fetch.mockImplementationOnce(() => new Promise(() => {}));
    uploadFiles([xmlFile()]);
    fireEvent.click(analyzeButton());
    expect(await screen.findByText('מנתח את הנתונים...')).toBeInTheDocument();
    expect(document.querySelector('.screen--upload')).toBeNull();
  });
});

describe('Theme', () => {
  test('toggles and remembers the colour theme', () => {
    render(<App />);
    const toggle = screen.getByRole('button', { name: /light mode|dark mode/ });
    const before = document.documentElement.getAttribute('data-theme');
    fireEvent.click(toggle);
    const after = document.documentElement.getAttribute('data-theme');
    expect(after).not.toBe(before);
    expect(localStorage.getItem('amo-theme')).toBe(after);
  });
});

describe('Navigation', () => {
  test('"new analysis" returns to the upload screen keeping the files', async () => {
    await goToResults();
    fireEvent.click(screen.getByRole('button', { name: '← ניתוח חדש' }));
    expect(screen.getByText(/test\.xml/)).toBeInTheDocument();
  });
});
