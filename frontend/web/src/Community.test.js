// Community: joining from the results page, the leaderboard and profiles.
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { goToResults, holding, rowsText } from './testing/fixtures';

jest.setTimeout(20000);

const ME = {
  fake_name: 'נשר 42', weighted_tsua: 18.98, weighted_score: 70, dominant_risk: 'medium',
  weighted_equity_exposure: 46.4, funds: [{ name: 'מיטב גמל', id: '103', pct: 100 }], joined: '11/09/2026',
};
// In server order (by AmoScore, descending), as /community/leaderboard returns it
const LEADERBOARD = {
  profiles: [
    { fake_name: 'נשר 42', weighted_tsua: 18.98, weighted_score: 70, dominant_risk: 'medium', weighted_equity_exposure: 46.4, num_funds: 1, joined: '09/2026' },
    { fake_name: 'דוב 11', weighted_tsua: 25.0, weighted_score: 60, dominant_risk: 'high', weighted_equity_exposure: 90, num_funds: 2, joined: '08/2026' },
    { fake_name: 'שועל 77', weighted_tsua: 4.1, weighted_score: 55, dominant_risk: 'low', weighted_equity_exposure: 12, num_funds: 3, joined: '07/2026' },
  ],
};

const json = data => ({ ok: true, json: async () => data });

async function openInvite(result) {
  await goToResults(result);
  fireEvent.click(screen.getByRole('button', { name: 'הצטרף' }));
  await screen.findByText(/הצטרף לקהילת המשקיעים/);
}

async function joinCommunity() {
  await openInvite();
  fetch.mockResolvedValueOnce(json({ success: true, profile: ME })).mockResolvedValueOnce(json(LEADERBOARD));
  fireEvent.click(screen.getByRole('button', { name: 'הצטרף לקהילה' }));
  await screen.findByText(/טבלת המשקיעים/);
}

const names = () => rowsText('.leaderboard-row .lb-name').map(n => n.replace('אתה', ''));

describe('Invite', () => {
  test('previews the profile using the fixed community weights', async () => {
    const funds = [
      holding({ client: { amount: 150000, default_grade: 70, tsua_1: 20, equity_exposure: 40 } }),
      holding({ client: { id: '104', amount: 50000, default_grade: 90, tsua_1: 10, equity_exposure: 80 } }),
    ];
    await openInvite({ funds });
    const stats = rowsText('.community-stat-mini-val');
    // (70×150k + 90×50k)/200k, (20×150k + 10×50k)/200k, (40×150k + 80×50k)/200k
    expect(stats).toEqual(['75.0', '17.5%', '50.0%']);
    expect(document.querySelector('.community-weights-note').textContent).toMatch(/Sharp Ratio 35% · מדד נזילות 10%/);
  });

  test('joining sends an anonymous summary of each fund', async () => {
    await joinCommunity();
    const [url, options] = fetch.mock.calls.find(([u]) => u.endsWith('/community/join'));
    expect(url).toBe('http://localhost:8000/community/join');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({
      client_id: '987654321',
      funds: [{
        name: 'מיטב גמל', id: '103', risk_level: 'medium', tsua_1: 18.98, grade: 70,
        amount: 150000, equity_exposure: 46.44, pct_of_total: 100,
      }],
    });
  });

  test('a failed join is reported and the button recovers', async () => {
    await openInvite();
    fetch.mockRejectedValueOnce(new Error('down'));
    fireEvent.click(screen.getByRole('button', { name: 'הצטרף לקהילה' }));
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith('שגיאה בהצטרפות לקהילה. אנא בדוק שהשרת פועל ונסה שוב.'));
    expect(screen.getByRole('button', { name: 'הצטרף לקהילה' })).not.toBeDisabled();
  });

  test('back returns to the results', async () => {
    await openInvite();
    fireEvent.click(screen.getByRole('button', { name: '→ חזרה לתוצאות' }));
    expect(await screen.findByText('טבלת דירוג — AmoScore')).toBeInTheDocument();
  });
});

describe('Leaderboard', () => {
  test('ranks by AmoScore and marks my profile', async () => {
    await joinCommunity();
    expect(names()).toEqual(['נשר 42', 'דוב 11', 'שועל 77']);
    expect(document.querySelector('.leaderboard-row--me').textContent).toMatch(/נשר 42אתה/);
    expect(screen.getByText('3 משקיעים בקהילה')).toBeInTheDocument();
  });

  test('can rank by annual return instead', async () => {
    await joinCommunity();
    fireEvent.click(screen.getByRole('button', { name: 'תשואה שנתית' }));
    expect(names()).toEqual(['דוב 11', 'נשר 42', 'שועל 77']);
  });

  test.each([['גבוהה', ['דוב 11']], ['בינונית', ['נשר 42']], ['נמוכה', ['שועל 77']]])(
    'risk filter %s uses the equity exposure', async (label, expected) => {
      await joinCommunity();
      fireEvent.click(screen.getByRole('button', { name: label }));
      expect(names()).toEqual(expected);
    },
  );

  test('opening another profile fetches it', async () => {
    await joinCommunity();
    fetch.mockResolvedValueOnce(json({ ...LEADERBOARD.profiles[1], funds: [{ name: 'קופה', id: '1', pct: 100 }] }));
    fireEvent.click(screen.getByText('דוב 11'));
    await screen.findByText('הקצאת קופות');
    expect(fetch).toHaveBeenLastCalledWith(`http://localhost:8000/community/profile/${encodeURIComponent('דוב 11')}`);
    expect(rowsText('.profile-stat-val')).toEqual(['60.0', '25.0%', '90.0%', '#2']);
    fireEvent.click(screen.getByRole('button', { name: '→ חזרה לטבלה' }));
    await screen.findByText(/טבלת המשקיעים/);
  });

  test('my own profile opens without a request', async () => {
    await joinCommunity();
    const calls = fetch.mock.calls.length;
    fireEvent.click(document.querySelector('.leaderboard-row--me'));
    await screen.findByText('הפרופיל שלך ✨');
    expect(fetch.mock.calls.length).toBe(calls);
  });
});
