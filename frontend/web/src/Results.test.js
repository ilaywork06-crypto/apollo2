// Results page: fee mode across every widget, the portfolio score, merging, filtering and the PDF.
import { screen, fireEvent, waitFor } from '@testing-library/react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import {
  ALTERNATIVE, GOLDEN, MOCK_RESULT, PORTFOLIO, goToResults, holding,
} from './testing/fixtures';

jest.setTimeout(20000);

const text = selector => document.querySelector(selector)?.textContent ?? '';
const clickFeeMode = label => fireEvent.click(screen.getAllByRole('button', { name: label })[0]);
const WITH_GOLDEN = { funds: [holding({ golden: GOLDEN })], portfolio: PORTFOLIO };

// ─── Fee mode ────────────────────────────────────────────────────────────────

describe('Fee mode for the alternative funds', () => {
  test('defaults to "with fees" everywhere', async () => {
    await goToResults(WITH_GOLDEN);
    expect(screen.getAllByRole('button', { name: 'כולל דמי ניהול' })[0]).toHaveAttribute('aria-pressed', 'true');
    expect(text('.table-title-sub')).toMatch(/כל התשואות בניכוי דמי הניהול שלך \(0\.50%\)/);
  });

  test('switching to "without fees" updates the table but not the client row', async () => {
    await goToResults(WITH_GOLDEN);
    const altRow = () => document.querySelector('.alts-table .row-alt').textContent;
    const clientRow = () => document.querySelector('.alts-table .row-client').textContent;
    expect(altRow()).toMatch(/22\.0%.*₪160,000.*\+₪10,000.*\+6\.7%/);
    const clientBefore = clientRow();
    clickFeeMode('ללא דמי ניהול');
    expect(altRow()).toMatch(/22\.5%.*₪160,800.*\+₪10,800.*\+7\.2%/);
    expect(clientRow()).toBe(clientBefore);
    expect(clientRow()).toMatch(/19\.0%.*₪150,000/);
    expect(text('.table-title-sub')).toMatch(/ברוטו/);
  });

  test('scores and ranks are the same in both modes', async () => {
    await goToResults(WITH_GOLDEN);
    const scores = () => Array.from(document.querySelectorAll('.td-score')).map(td => td.textContent);
    const before = scores();
    clickFeeMode('ללא דמי ניהול');
    expect(scores()).toEqual(before);
  });

  test('summary, "what you missed" and golden cards follow the mode', async () => {
    await goToResults(WITH_GOLDEN);
    // best of (alternative 160,000, golden 175,000) over the 150,000 balance
    expect(text('.summary-hero')).toMatch(/\+₪25,000/);
    expect(text('.highrisk-card')).toMatch(/6\.7%/);
    expect(text('.gold-card')).toMatch(/16\.7%.*₪175,000/);
    clickFeeMode('ללא דמי ניהול');
    expect(text('.summary-hero')).toMatch(/\+₪26,000/);
    expect(text('.highrisk-card')).toMatch(/7\.2%.*₪160,800/);
    expect(text('.gold-card')).toMatch(/17\.3%.*₪176,000/);
  });

  test('the bar chart follows the mode', async () => {
    await goToResults();
    const bars = () => Array.from(document.querySelectorAll('.bar-pct')).map(b => b.textContent);
    expect(bars()).toEqual(['19.0%', '22.0%']);
    clickFeeMode('ללא דמי ניהול');
    expect(bars()).toEqual(['19.0%', '22.5%']);
  });

  test('the top toggle and the table toggle share one setting', async () => {
    await goToResults();
    const [top, table] = screen.getAllByRole('button', { name: 'ללא דמי ניהול' });
    fireEvent.click(table);
    expect(top).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(screen.getAllByRole('button', { name: 'כולל דמי ניהול' })[0]);
    expect(table).toHaveAttribute('aria-pressed', 'false');
  });

  test('other periods follow the mode too', async () => {
    await goToResults();
    fireEvent.click(screen.getByRole('button', { name: /תשואה שנתית/ }));
    fireEvent.click(screen.getByRole('button', { name: '3 שנים' }));
    const altRow = () => document.querySelector('.alts-table .row-alt').textContent;
    expect(altRow()).toMatch(/14\.0%.*₪180,000/);
    clickFeeMode('ללא דמי ניהול');
    expect(altRow()).toMatch(/14\.5%.*₪182,000/);
  });

  test('periods without data show a dash, not a made-up gain', async () => {
    const noThreeYears = { ...ALTERNATIVE, potential_amount_3: null, diff_3: null, diff_percent_3: null };
    await goToResults({ funds: [holding({ alternatives: [noThreeYears] })], portfolio: PORTFOLIO });
    fireEvent.click(screen.getByRole('button', { name: /תשואה שנתית/ }));
    fireEvent.click(screen.getByRole('button', { name: '3 שנים' }));
    const cells = document.querySelector('.alts-table .row-alt').querySelectorAll('td');
    expect(cells[4].textContent).toBe('—');
    expect(cells[5].textContent).toBe('—');
  });
});

// ─── Client card ─────────────────────────────────────────────────────────────

describe('Client card', () => {
  test('shows the equity split and the liquidity index', async () => {
    await goToResults();
    const line = text('.client-profile-line');
    expect(line).toMatch(/מניות 46\.4%:/);
    expect(line).toMatch(/ישראל 20% · חו״ל 80%/);
    expect(line).toMatch(/\+18\.8%/);
    expect(line).toMatch(/מדד נזילות 77 מתוך 100/);
  });

  test('a fund that scored 0 is weak, not "new"', async () => {
    await goToResults({ funds: [holding({ client: { grade: 0, has_grade: true, rank: 20, percentile: 0 } })] });
    expect(text('.gauge-amoscore-value')).toBe('0.0');
    expect(text('.client-verdict')).toMatch(/מתחת לממוצע/);
  });

  test('a fund without enough data is marked as new', async () => {
    await goToResults({ funds: [holding({ client: { grade: 0, has_grade: false } })] });
    expect(text('.gauge-amoscore-value')).toBe('–');
    expect(text('.client-verdict')).toMatch(/קופה חדשה/);
  });
});

// ─── Portfolio score ─────────────────────────────────────────────────────────

describe('Portfolio score card', () => {
  const card = () => text('.portfolio-card');

  test('score, verdict, score after moving and weighted percentile', async () => {
    await goToResults();
    expect(text('.score-ring')).toBe('72.5');
    expect(text('.portfolio-card-verdict')).toBe('מצוין');
    expect(card()).toMatch(/72\.5 ← 85\.0/);
    expect(card()).toMatch(/אחוזון 85/);
    expect(card()).not.toMatch(/לא נכללו בציון/);
  });

  test('warns about money that could not be scored', async () => {
    await goToResults({ ...MOCK_RESULT, portfolio: { ...PORTFOLIO, coverage: 62.5 } });
    expect(card()).toMatch(/37\.5% מהצבירה נמצאים בקופות ללא מספיק נתונים/);
  });

  test('no score at all', async () => {
    await goToResults({ ...MOCK_RESULT, portfolio: { ...PORTFOLIO, weighted_score: null, potential_score: null,
      weighted_percentile: null, coverage: 0 } });
    expect(text('.score-ring')).toBe('–');
    expect(text('.portfolio-card-verdict')).toBe('אין מספיק נתונים');
    expect(card()).not.toMatch(/אם תעבור/);
  });

  test('no "after moving" line when already at the best', async () => {
    await goToResults({ ...MOCK_RESULT, portfolio: { ...PORTFOLIO, potential_score: 72.5 } });
    expect(card()).not.toMatch(/אם תעבור לחלופה המובילה/);
  });

  test('breakdown lists each fund by its share of the money', async () => {
    const funds = [
      holding({ client: { id: '1', name: 'גדולה', amount: 300000, grade: 40 } }),
      holding({ client: { id: '2', name: 'קטנה', amount: 100000, grade: 0, has_grade: false } }),
    ];
    await goToResults({ funds, portfolio: PORTFOLIO });
    const items = Array.from(document.querySelectorAll('.portfolio-alloc-item')).map(i => i.textContent);
    expect(items).toEqual([expect.stringMatching(/גדולה.*75\.0% מהכסף.*40\.0/), expect.stringMatching(/קטנה.*25\.0% מהכסף.*–/)]);
    const widths = Array.from(document.querySelectorAll('.portfolio-alloc-seg')).map(s => s.style.width);
    expect(widths).toEqual(['75%', '25%']);
  });
});

// ─── Merging and filtering ───────────────────────────────────────────────────

describe('Several holdings', () => {
  const twoOfTheSameFund = {
    funds: [holding(), holding({ client: { amount: 50000 } })],
    portfolio: { ...PORTFOLIO, total_amount: 200000 },
  };

  test('identical funds are merged by default, with exactly scaled projections', async () => {
    await goToResults(twoOfTheSameFund);
    expect(document.querySelectorAll('.fund-results')).toHaveLength(1);
    expect(text('.client-stats-inline')).toMatch(/₪200,000/);
    // 160,000 on 150,000 -> 213,333 on 200,000
    expect(text('.alts-table .row-alt')).toMatch(/₪213,333/);
    expect(document.querySelector('.results-filter')).toBeNull();
  });

  test('merging can be switched off', async () => {
    await goToResults(twoOfTheSameFund, {
      before: () => {
        fireEvent.click(screen.getByText('איחוד קופות זהות'));
        fireEvent.click(document.querySelector('.fund-toggle input'));
      },
    });
    expect(document.querySelectorAll('.fund-results')).toHaveLength(2);
    expect(screen.getByRole('option', { name: /#103 — מיטב גמל \(×2\)/ })).toBeInTheDocument();
  });

  test('the fund selector shows one fund at a time', async () => {
    const other = holding({ client: { id: '555', name: 'קופה אחרת' } });
    await goToResults({ funds: [holding(), other], portfolio: PORTFOLIO });
    fireEvent.change(document.querySelector('.results-filter-select'), { target: { value: '555' } });
    expect(document.querySelectorAll('.fund-results')).toHaveLength(1);
    expect(text('.client-fund-name')).toBe('קופה אחרת');
    expect(document.querySelector('.portfolio-card')).toBeTruthy(); // the portfolio still covers everything
  });
});

// ─── Explanation and community ───────────────────────────────────────────────

describe('Page footer', () => {
  test('explains all five parameters with the chosen weights', async () => {
    await goToResults();
    const chips = Array.from(document.querySelectorAll('.weight-chip')).map(c => c.textContent);
    expect(chips).toEqual(['תשואה שנה10%', 'תשואה 3 שנים20%', 'תשואה 5 שנים25%', 'Sharp Ratio35%', 'מדד נזילות10%']);
    expect(text('.amoscore-explanation')).toMatch(/מדד הנזילות/);
  });

  test('invites the client to the community', async () => {
    await goToResults();
    fireEvent.click(screen.getByRole('button', { name: 'הצטרף' }));
    expect(await screen.findByText(/הצטרף לקהילת המשקיעים/)).toBeInTheDocument();
  });
});

// ─── PDF ─────────────────────────────────────────────────────────────────────

describe('PDF report', () => {
  let pages;
  beforeEach(() => {
    pages = [];
    html2canvas.mockImplementation((element) => {
      pages.push(element.textContent.replace(/\s+/g, ' '));
      return Promise.resolve({ toDataURL: () => 'data:image/jpeg;base64,', width: 794, height: 1123 });
    });
  });

  const download = async () => {
    fireEvent.click(screen.getByRole('button', { name: 'הורד דוח PDF' }));
    await waitFor(() => expect(jsPDF.mock.results[0].value.save).toHaveBeenCalled(), { timeout: 5000 });
  };

  test('a cover page plus one page per fund, saved under a dated name', async () => {
    await goToResults({ funds: [holding(), holding({ client: { id: '777', name: 'קופה שנייה' } })], portfolio: PORTFOLIO });
    await download();
    expect(pages).toHaveLength(3);
    expect(jsPDF.mock.results[0].value.save.mock.calls[0][0]).toMatch(/^AmoSight-.+_\d{2}-\d{2}-\d{2}\.pdf$/);
    expect(pages[2]).toMatch(/קופה שנייה/);
    expect(window.alert).not.toHaveBeenCalled();
  });

  test('the cover shows the portfolio score and all five weights', async () => {
    await goToResults();
    await download();
    expect(pages[0]).toMatch(/ציון תיק משוקלל 72\.5 מצוין/);
    expect(pages[0]).toMatch(/72\.5 ← 85\.0/);
    for (const label of ['תשואה שנה', 'תשואה 3 שנים', 'תשואה 5 שנים', 'Sharp Ratio', 'מדד נזילות']) {
      expect(pages[0]).toContain(label);
    }
    expect(pages[0]).toMatch(/5 פרמטרים/);
  });

  test('uses the fee mode on screen', async () => {
    await goToResults();
    clickFeeMode('ללא דמי ניהול');
    await download();
    expect(pages[0]).toMatch(/ברוטו, ללא דמי ניהול/);
    expect(pages[1]).toMatch(/₪160,800/);
    expect(pages[1]).toMatch(/22\.5%/);
  });

  test('a failure is reported and the button recovers', async () => {
    html2canvas.mockImplementation(() => Promise.reject(new Error('canvas broke')));
    await goToResults();
    fireEvent.click(screen.getByRole('button', { name: 'הורד דוח PDF' }));
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith('שגיאה: canvas broke'));
    expect(screen.getByRole('button', { name: 'הורד דוח PDF' })).not.toBeDisabled();
  });
});

describe('Client name on the page', () => {
  test('the client card shows fund metadata', async () => {
    await goToResults();
    const meta = text('.client-fund-meta');
    expect(meta).toMatch(/קופה #103/);
    expect(meta).toMatch(/ותק מ-01\/01\/2018/);
    expect(text('.client-card .rank-pill')).toBe('מקום 3 מתוך 20');
  });
});
