// Many-clients analysis: ranking, controls, CSV export and drill-down into one client.
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { ALTERNATIVE, GOLDEN, bulkClient, goToBulk, holding, rowsText } from './testing/fixtures';

jest.setTimeout(20000);

// Three clients: one who gains from a same-risk move and more from the golden option,
// one already in the best fund, and one whose fund could not be scored.
const MOVER = bulkClient('111', 'דנה כהן', [holding({ golden: GOLDEN })], { weighted_score: 40 });
const BEST = bulkClient('222', 'יוסי לוי', [holding({ client: { rank: 1, grade: 95 } })], { weighted_score: 95, total_amount: 400000 });
const NEW = bulkClient('333', 'רון גל', [holding({ client: { rank: 1, grade: 0, has_grade: false } })],
  { weighted_score: null, total_amount: 90000 });
const DATA = {
  clients: [BEST, NEW, MOVER],
  errors: [{ file: 'broken.xml', error: 'הקובץ אינו XML תקין' }],
  skipped: [{ file: 'pension.xml', reason: 'לא נמצאו בקובץ קופות גמל או השתלמות מגמל נט' }],
  files_received: 5,
};

const rows = () => rowsText('.bulk-table tbody tr');
const names = () => rows().map(r => ['דנה כהן', 'יוסי לוי', 'רון גל'].find(n => r.includes(n)));
const click = name => fireEvent.click(screen.getByRole('button', { name }));

describe('Summary', () => {
  test('counts clients, files, money and gains', async () => {
    await goToBulk(DATA);
    const stats = rowsText('.bulk-stat');
    expect(stats).toEqual([
      '3לקוחות', '5קבצים שהועלו', '₪640,000צבירה כוללת', '₪25,000רווח מניוד · שנה', '1לקוחות שירוויחו מניוד',
    ]);
  });

  test('files that were not analysed are listed with the reason', async () => {
    await goToBulk(DATA);
    click(/2 קבצים לא נותחו/);
    expect(rowsText('.bulk-issue')).toEqual([
      'broken.xml — הקובץ אינו XML תקין',
      'pension.xml — לא נמצאו בקובץ קופות גמל או השתלמות מגמל נט',
    ]);
  });

  test('no clients at all', async () => {
    await goToBulk({ clients: [], errors: [], skipped: [], files_received: 1 });
    expect(screen.getByText('לא נמצאו בקבצים קופות גמל או השתלמות לניתוח')).toBeInTheDocument();
  });
});

describe('Ranking', () => {
  test('by NIS gain; ties go to the weaker portfolio, unscored last', async () => {
    await goToBulk(DATA);
    expect(names()).toEqual(['דנה כהן', 'יוסי לוי', 'רון גל']);
    expect(rows()[0]).toMatch(/\+₪25,000.*\+16\.67% מהצבירה/);
    expect(rows()[0]).toMatch(/מיטב גמל← אלפא מור תגמולים/);
    expect(rows()[1]).toMatch(/אין רווח מניוד/);
  });

  test.each([
    ['ציון נמוך', ['דנה כהן', 'יוסי לוי', 'רון גל']],
    ['צבירה', ['יוסי לוי', 'דנה כהן', 'רון גל']],
    ['רווח %', ['דנה כהן', 'יוסי לוי', 'רון גל']],
  ])('sort by %s', async (label, expected) => {
    await goToBulk(DATA);
    click(label);
    expect(names()).toEqual(expected);
  });

  test('same-risk only ignores the golden option', async () => {
    await goToBulk(DATA);
    click('באותה רמת סיכון');
    expect(rows()[0]).toMatch(/\+₪10,000.*\+6\.67% מהצבירה/);
    expect(rows()[0]).toMatch(/← הראל גמל/);
    click(/כולל תפוח הזהב/);
    expect(rows()[0]).toMatch(/\+₪25,000/);
  });

  test('longer periods use the longer projections', async () => {
    await goToBulk(DATA);
    click('3 שנים');
    // golden and alternative share the 3-year projection in the fixture: 180,000 on 150,000
    expect(rows()[0]).toMatch(/\+₪30,000/);
    expect(rowsText('.bulk-stat')[3]).toBe('₪30,000רווח מניוד · 3 שנים');
    click('5 שנים');
    expect(rows()[0]).toMatch(/\+₪60,000/);
  });

  test('the fee mode changes the gains', async () => {
    await goToBulk(DATA);
    click('ללא דמי ניהול');
    expect(rows()[0]).toMatch(/\+₪26,000/);
  });
});

describe('Finding clients', () => {
  test.each([['שם', 'יוסי'], ['ת״ז', '333'], ['קובץ', '111.xml']])('search by %s', async (_, query) => {
    await goToBulk(DATA);
    fireEvent.change(screen.getByPlaceholderText(/חיפוש/), { target: { value: query } });
    expect(rows()).toHaveLength(1);
  });

  test('no match', async () => {
    await goToBulk(DATA);
    fireEvent.change(screen.getByPlaceholderText(/חיפוש/), { target: { value: 'אין כזה' } });
    expect(screen.getByText('אין לקוחות שתואמים לחיפוש')).toBeInTheDocument();
  });

  test('long lists are shown 200 at a time', async () => {
    const many = Array.from({ length: 205 }, (_, i) => bulkClient(String(1000 + i), `לקוח ${i}`, [holding()]));
    await goToBulk({ clients: many, errors: [], skipped: [], files_received: 205 });
    expect(rows()).toHaveLength(200);
    click(/הצג עוד 5 לקוחות/);
    expect(rows()).toHaveLength(205);
  });
});

describe('Excel export', () => {
  const exportedBlob = async () => {
    fireEvent.click(screen.getByRole('button', { name: /ייצוא ל-Excel/ }));
    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalled());
    return URL.createObjectURL.mock.calls[0][0];
  };
  // Reading the file as text decodes the UTF-8, which drops its byte-order mark
  const exportCsv = async () => (await exportedBlob()).text();
  const firstBytes = blob => new Promise(resolve => {
    const reader = new FileReader();
    reader.onload = () => resolve(Array.from(new Uint8Array(reader.result).slice(0, 3)));
    reader.readAsArrayBuffer(blob);
  });

  test('starts with a UTF-8 byte-order mark so Excel reads the Hebrew', async () => {
    await goToBulk(DATA);
    const blob = await exportedBlob();
    expect(blob.type).toBe('text/csv;charset=utf-8');
    expect(await firstBytes(blob)).toEqual([0xef, 0xbb, 0xbf]);
  });

  test('exports the table in its current order', async () => {
    await goToBulk(DATA);
    const lines = (await exportCsv()).split('\r\n');
    expect(lines[0]).toBe(
      'עדיפות,ת״ז,שם,קבצים,קופות,צבירה כוללת,ציון תיק משוקלל,ציון אחרי ניוד,כיסוי דירוג %,'
      + '"רווח מניוד — שנה, כולל דמי ניהול, כולל תפוח הזהב",רווח % מהצבירה,מהלך מומלץ',
    );
    expect(lines.slice(1).map(l => l.split(',')[1])).toEqual(['111', '222', '333']);
    expect(lines[1]).toMatch(/^1,111,דנה כהן,111\.xml,1,150000,40,85,100,25000,16\.67,/);
    expect(lines[1]).toMatch(/מיטב גמל \(#103\) ← אלפא מור תגמולים \(#900\)$/);
  });

  test('quotes values that contain commas or quotes', async () => {
    const tricky = bulkClient('444', 'כהן, "הבן"', [holding()]);
    await goToBulk({ clients: [tricky], errors: [], skipped: [], files_received: 1 });
    const csv = await exportCsv();
    expect(csv).toContain('"כהן, ""הבן"""');
  });

  test('follows the chosen period, fee mode and sort', async () => {
    await goToBulk(DATA);
    click('5 שנים');
    click('ללא דמי ניהול');
    click('צבירה');
    const lines = (await exportCsv()).split('\r\n');
    expect(lines[0]).toContain('רווח מניוד — 5 שנים, ללא דמי ניהול');
    expect(lines.slice(1).map(l => l.split(',')[1])).toEqual(['222', '111', '333']);
  });
});

describe('Opening a client', () => {
  test('shows their full report with the portfolio score, without the community invite', async () => {
    await goToBulk(DATA);
    fireEvent.click(screen.getAllByRole('button', { name: 'פתח דוח' })[0]);
    await screen.findByText('טבלת דירוג — AmoScore');
    expect(document.querySelector('.results-subject').textContent).toBe('📋 דוח עבור דנה כהן · ת״ז 111 · קובץ אחד');
    expect(document.querySelector('.score-ring').textContent).toBe('40.0');
    expect(screen.queryByText(/הצטרף לקהילה האנונימית/)).not.toBeInTheDocument();
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
  });

  test('the fee mode carries over both ways', async () => {
    await goToBulk(DATA);
    fireEvent.click(screen.getByRole('button', { name: 'ללא דמי ניהול' }));
    fireEvent.click(document.querySelector('.bulk-row'));
    await screen.findByText('טבלת דירוג — AmoScore');
    expect(document.querySelector('.alts-table .row-alt').textContent).toMatch(/22\.5%/);
    fireEvent.click(screen.getAllByRole('button', { name: 'כולל דמי ניהול' })[0]);
    fireEvent.click(screen.getByRole('button', { name: /חזרה לרשימת הלקוחות/ }));
    await screen.findByText('הלקוחות לפי דחיפות ניוד');
    expect(screen.getByRole('button', { name: 'כולל דמי ניהול' })).toHaveAttribute('aria-pressed', 'true');
  });

  test('a client without an ID is labelled by their file', async () => {
    const anonymous = { ...bulkClient(null, '', [holding({ alternatives: [ALTERNATIVE] })]), files: ['x.xml'] };
    await goToBulk({ clients: [anonymous], errors: [], skipped: [], files_received: 1 });
    expect(rows()[0]).toMatch(/x\.xml/);
  });

  test('"new analysis" leaves the list', async () => {
    await goToBulk(DATA);
    fireEvent.click(screen.getByRole('button', { name: '← ניתוח חדש' }));
    expect(screen.getByRole('tab', { name: /ניתוח מרובה לקוחות/ })).toHaveAttribute('aria-selected', 'true');
  });
});
