// Pure helpers behind the results and bulk pages, checked on many random inputs.
import { aggregateResults, applyFeeMode, clientUpside, hasGrade, topMove, withFeeMode } from './App';
import { ALTERNATIVE, GOLDEN, holding } from './testing/fixtures';

// Small seeded PRNG (mulberry32) so a failing case can be reproduced from its seed
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const SUFFIXES = ['', '_3', '_5'];

function randomOption(r, amount) {
  const option = { id: String(Math.floor(r() * 1e6)), name: 'חלופה', grade: Math.round(r() * 100) };
  const gross = {};
  for (const s of SUFFIXES) {
    const pct = r() < 0.15 ? null : Math.round((r() * 60 - 20) * 10) / 10;
    option[`diff_percent${s}`] = pct;
    option[`potential_amount${s}`] = pct == null ? null : amount * (1 + pct / 100);
    option[`diff${s}`] = pct == null ? null : amount * pct / 100;
    const gpct = pct == null ? null : pct + Math.round(r() * 10) / 10;
    gross[`diff_percent${s}`] = gpct;
    gross[`potential_amount${s}`] = gpct == null ? null : amount * (1 + gpct / 100);
    gross[`diff${s}`] = gpct == null ? null : amount * gpct / 100;
  }
  return { ...option, gross };
}

function randomHolding(r, { id } = {}) {
  const amount = Math.round(r() * 1e6) + 1;
  const alternatives = Array.from({ length: Math.floor(r() * 4) }, () => randomOption(r, amount));
  return {
    client: { id: id ?? String(Math.floor(r() * 5)), name: 'קופה', amount, rank: 1 + Math.floor(r() * 10), grade: 50 },
    alternatives,
    golden: r() < 0.5 ? {} : randomOption(r, amount),
  };
}

const forSeeds = (count, fn) => {
  for (let seed = 1; seed <= count; seed++) fn(rng(seed), seed);
};

// ─── Fee mode ────────────────────────────────────────────────────────────────

describe('withFeeMode / applyFeeMode', () => {
  test('net mode returns the option untouched', () => {
    expect(withFeeMode(ALTERNATIVE, 'net')).toBe(ALTERNATIVE);
  });

  test('gross mode swaps in every gross figure and keeps identity fields', () => {
    const gross = withFeeMode(ALTERNATIVE, 'gross');
    expect(gross).toMatchObject({ ...ALTERNATIVE.gross, id: '200', name: 'הראל גמל', grade: 85 });
  });

  test('options without gross figures and empty golden options pass through', () => {
    const noGross = { ...ALTERNATIVE, gross: undefined };
    expect(withFeeMode(noGross, 'gross')).toBe(noGross);
    expect(withFeeMode({}, 'gross')).toEqual({});
    expect(withFeeMode(undefined, 'gross')).toBeUndefined();
  });

  test('never touches the client and never mutates its input', () => {
    forSeeds(200, r => {
      const h = randomHolding(r);
      const snapshot = JSON.parse(JSON.stringify(h));
      const view = applyFeeMode(h, 'gross');
      expect(view.client).toBe(h.client);
      expect(JSON.parse(JSON.stringify(h))).toEqual(snapshot);
      view.alternatives.forEach((alt, i) => expect(alt.potential_amount).toBe(h.alternatives[i].gross.potential_amount));
    });
  });
});

// ─── Upside ──────────────────────────────────────────────────────────────────

describe('clientUpside / topMove', () => {
  test('the fixture client: golden 175k vs alternative 160k on 150k', () => {
    const client = { funds: [holding({ golden: GOLDEN })] };
    expect(clientUpside(client, 'net')).toBe(25000);
    expect(clientUpside(client, 'gross')).toBe(26000);
    expect(clientUpside(client, 'net', '_5')).toBe(60000);
    expect(topMove(client, 'net').to.id).toBe('900');
  });

  test('invariants on random clients', () => {
    forSeeds(300, (r, seed) => {
      const client = { funds: Array.from({ length: 1 + Math.floor(r() * 4) }, () => randomHolding(r)) };
      for (const s of SUFFIXES) {
        const withGolden = clientUpside(client, 'net', s, true);
        const sameRisk = clientUpside(client, 'net', s, false);
        const gross = clientUpside(client, 'gross', s, true);
        const move = topMove(client, 'net', s, true);
        const context = `seed ${seed} suffix '${s}'`;
        expect([context, withGolden >= 0]).toEqual([context, true]);
        expect([context, withGolden >= sameRisk - 1e-6]).toEqual([context, true]);
        expect([context, gross >= withGolden - 1e-6]).toEqual([context, true]);
        expect([context, move === null]).toEqual([context, withGolden < 1e-9]);
        expect([context, move === null || move.gain <= withGolden + 1e-6]).toEqual([context, true]);
      }
    });
  });

  test('a client already in the best fund only counts the golden option', () => {
    const best = { funds: [holding({ client: { rank: 1 } })] };
    expect(clientUpside(best, 'net')).toBe(0);
    expect(topMove(best, 'net')).toBeNull();
    const bestWithGolden = { funds: [holding({ client: { rank: 1 }, golden: GOLDEN })] };
    expect(clientUpside(bestWithGolden, 'net', '', false)).toBe(0);
    expect(clientUpside(bestWithGolden, 'net')).toBe(25000);
  });
});

// ─── Merging identical funds ─────────────────────────────────────────────────

describe('aggregateResults', () => {
  test('keeps the total balance and merges by fund', () => {
    forSeeds(200, r => {
      const holdings = Array.from({ length: 1 + Math.floor(r() * 6) }, () => randomHolding(r));
      const merged = aggregateResults(holdings);
      const total = list => list.reduce((s, h) => s + h.client.amount, 0);
      expect(merged.map(h => h.client.id)).toEqual([...new Set(holdings.map(h => h.client.id))]);
      expect(total(merged)).toBeCloseTo(total(holdings), 6);
    });
  });

  test('a fund held once is returned exactly as it was', () => {
    forSeeds(100, r => {
      const single = randomHolding(r, { id: 'only' });
      expect(aggregateResults([single])[0]).toBe(single);
    });
  });

  test('merged projections keep their return ratio, net and gross, and "no data" stays null', () => {
    forSeeds(200, r => {
      const first = randomHolding(r, { id: 'x' });
      const second = randomHolding(r, { id: 'x' });
      const [merged] = aggregateResults([first, second]);
      const amount = first.client.amount + second.client.amount;
      expect(merged.client.amount).toBe(amount);
      merged.alternatives.forEach((alt, i) => {
        const original = first.alternatives[i];
        for (const s of SUFFIXES) {
          for (const [m, o] of [[alt, original], [alt.gross, original.gross]]) {
            const potential = m[`potential_amount${s}`];
            const hadData = o[`potential_amount${s}`] != null;
            // With data: same growth ratio on the merged balance, and potential − diff = balance.
            // Without: still null, never turned into a made-up number.
            const check = potential == null ? 'null' : [
              Math.abs(potential / amount - o[`potential_amount${s}`] / first.client.amount) < 1e-9,
              Math.abs(potential - m[`diff${s}`] - amount) < 1e-4,
            ].join();
            expect(check).toBe(hadData ? 'true,true' : 'null');
          }
        }
      });
    });
  });

  test('an empty golden option stays empty after merging', () => {
    const [merged] = aggregateResults([holding(), holding({ client: { amount: 50000 } })]);
    expect(merged.golden).toEqual({});
  });
});

describe('hasGrade', () => {
  test.each([
    [{ grade: 0, has_grade: true }, true],
    [{ grade: 0, has_grade: false }, false],
    [{ grade: 55 }, true],
    [{ grade: 0 }, false],
    [undefined, false],
  ])('%j -> %s', (fund, expected) => {
    expect(hasGrade(fund)).toBe(expected);
  });
});
