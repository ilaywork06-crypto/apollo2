import { useState, useRef } from 'react';
import './App.css';

// ─── Constants ────────────────────────────────────────────────────────────────

const LOADING_STEPS = [
  'קורא את קבצי ה-XML...',
  'מחשב תשואות נטו בניכוי דמי ניהול...',
  'משווה מול קופות באותה רמת סיכון...',
  'מכין את הדוח...',
];

const ALT_COLORS = ['#10B981', '#3B82F6', '#8B5CF6'];

// ─── Parsing helpers ──────────────────────────────────────────────────────────

function parseClient(str) {
  if (!str) return { name: '', id: '0', grade: 0, rank: null, total: null };
  const name = (str.match(/Client's Kupa:\s*(.+?),\s*Kupa id/) || [])[1]?.trim() || str;
  const id = (str.match(/Kupa id:\s*(\d+)/) || [])[1] || '0';
  const grade = parseFloat((str.match(/Grade:\s*([\d.]+)/) || [])[1] || '0');
  const rm = str.match(/Rank\s*-\s*(\d+)\/(\d+)/);
  return { name, id, grade, rank: rm ? +rm[1] : null, total: rm ? +rm[2] : null };
}

function parseAlternative(str) {
  if (!str) return { name: '', id: '0', grade: 0, rank: null, total: null };
  const name = (str.match(/Better Kupa:\s*(.+?),\s*Kupa id/) || [])[1]?.trim() || str;
  const id = (str.match(/Kupa id\s*:\s*(\d+)/) || [])[1] || '0';
  const grade = parseFloat((str.match(/Grade:\s*([\d.]+)/) || [])[1] || '0');
  const rm = str.match(/Rank\s*-\s*(\d+)\/(\d+)/);
  return { name, id, grade, rank: rm ? +rm[1] : null, total: rm ? +rm[2] : null };
}

function getAmount(str) {
  const m = str?.match(/Current amount:\s*([\d.]+)/);
  return m ? parseFloat(m[1]) : 0;
}

function getPotential(str) {
  const m = str?.match(/Potential amount[^:]*:\s*([\d.]+)/);
  return m ? parseFloat(m[1]) : 0;
}

function groupResults(apiData) {
  const map = {};
  (apiData || []).forEach(item => {
    const client = parseClient(item.client);
    const alt = parseAlternative(item.alternative);
    const amount = getAmount(item.amount);
    const potential = getPotential(item.potential);
    if (!map[client.id]) {
      map[client.id] = { client: { ...client, amount }, alternatives: [] };
    }
    if (map[client.id].alternatives.length < 3) {
      map[client.id].alternatives.push({ ...alt, potential });
    }
  });
  return Object.values(map);
}

// ─── Utilities ────────────────────────────────────────────────────────────────

const fmt = n => Math.round(n).toLocaleString('he-IL');
const fmtDec = (n, d = 1) => (+n).toFixed(d);
const shortName = name => name?.split(' ').slice(0, 3).join(' ') || name;

// ─── Gauge SVG ────────────────────────────────────────────────────────────────

function Gauge({ rank, total }) {
  const pct = rank != null && total ? Math.round((1 - (rank - 1) / total) * 100) : 0;
  const color = pct >= 60 ? '#10B981' : pct >= 35 ? '#F59E0B' : '#EF4444';
  const cx = 70, cy = 70, r = 54;
  const arcLen = Math.PI * r;
  const fillLen = (pct / 100) * arcLen;
  // Arc from left to right going through the TOP (counter-clockwise in SVG = sweep=0)
  const d = `M ${cx - r},${cy} A ${r},${r} 0 0,0 ${cx + r},${cy}`;

  return (
    <svg width="140" height="84" viewBox="0 0 140 84" className="gauge-svg">
      {/* Track */}
      <path d={d} fill="none" stroke="#1E293B" strokeWidth="14" strokeLinecap="round" />
      {/* Fill */}
      {fillLen > 1 && (
        <path
          d={d}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${fillLen} ${arcLen + 30}`}
          strokeDashoffset="0"
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
      )}
      {/* Rank number */}
      <text
        x={cx} y={cy - 12}
        textAnchor="middle"
        fill={color}
        fontSize="26"
        fontWeight="800"
        fontFamily="Rubik, sans-serif"
      >
        {rank ?? '–'}
      </text>
      {/* "מתוך N" */}
      <text
        x={cx} y={cy + 5}
        textAnchor="middle"
        fill="#64748B"
        fontSize="11"
        fontFamily="Rubik, sans-serif"
      >
        מתוך {total ?? '–'}
      </text>
    </svg>
  );
}

// ─── Header ───────────────────────────────────────────────────────────────────

function Header({ onReset }) {
  return (
    <header className="app-header">
      <div className="header-inner">
        {onReset ? (
          <button className="btn-back" onClick={onReset}>← ניתוח חדש</button>
        ) : (
          <div />
        )}
        <div className="header-brand">
          <div className="header-logo">₪</div>
          <div className="header-text">
            <span className="header-title">FundCompare</span>
            <span className="header-subtitle">ניתוח והשוואת קופות גמל</span>
          </div>
        </div>
      </div>
    </header>
  );
}

// ─── Upload Zone ──────────────────────────────────────────────────────────────

function UploadZone({ label, subtitle, file, onFile }) {
  const inputRef = useRef();
  return (
    <div
      className={`upload-zone${file ? ' upload-zone--done' : ''}`}
      onClick={() => inputRef.current.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".xml"
        style={{ display: 'none' }}
        onChange={e => onFile(e.target.files[0])}
      />
      <div className={`upload-file-icon${file ? ' done' : ''}`}>
        {file ? '✓' : '📄'}
      </div>
      <div className="upload-label">{label}</div>
      <div className="upload-sub">
        {file ? `הקובץ נטען בהצלחה` : subtitle}
      </div>
      {file && <div className="upload-filename">{file.name}</div>}
    </div>
  );
}

// ─── Upload Screen ────────────────────────────────────────────────────────────

function UploadScreen({ mislakaFile, gemelnetFile, onMislaka, onGemelnet, onAnalyze }) {
  const ready = mislakaFile && gemelnetFile;
  return (
    <div className="screen screen--upload">
      <Header />
      <div className="upload-content">
        <div className="hero">
          <h1 className="hero-title">בדוק את הביצועים של הקופה שלך</h1>
          <p className="hero-sub">
            העלה את קבצי ה-XML מהמסלקה הפנסיונית ומגמל נט, וקבל ניתוח מקיף של ביצועי הקופה שלך מול השוק
          </p>
        </div>

        <div className="upload-row">
          <UploadZone
            label="קובץ מסלקה פנסיונית"
            subtitle="XML — פרטי קופה, סיכון, דמי ניהול"
            file={mislakaFile}
            onFile={onMislaka}
          />
          <UploadZone
            label="קובץ תשואות — גמל נט"
            subtitle="XML — תשואות שנתיות ברוטו"
            file={gemelnetFile}
            onFile={onGemelnet}
          />
        </div>

        <div className="product-box">
          <div className="product-box-label">סוג מוצר להשוואה</div>
          <div className="product-tags">
            <span className="product-tag">✓ גמל להשקעה</span>
            <span className="product-tag">✓ חסכון לכל ילד</span>
          </div>
        </div>

        <div className="info-cards">
          <div className="info-card">
            <div className="info-icon">📊</div>
            <div className="info-body">
              <div className="info-title">השוואה מול השוק</div>
              <div className="info-desc">דירוג הקופה שלך מול כל הקופות באותה רמת סיכון</div>
            </div>
          </div>
          <div className="info-card">
            <div className="info-icon">🏆</div>
            <div className="info-body">
              <div className="info-title">3 החלופות הטובות ביותר</div>
              <div className="info-desc">הצגת 3 קופות עם תשואות גבוהות יותר</div>
            </div>
          </div>
          <div className="info-card">
            <div className="info-icon">⚡</div>
            <div className="info-body">
              <div className="info-title">אופציית סיכון גבוה</div>
              <div className="info-desc">כמה כסף היה לך עם קופה ברמת סיכון גבוהה יותר</div>
            </div>
          </div>
        </div>

        <button
          className={`btn-analyze${ready ? ' btn-analyze--active' : ''}`}
          disabled={!ready}
          onClick={onAnalyze}
        >
          🔍 הפעל ניתוח
        </button>
      </div>
    </div>
  );
}

// ─── Loading Screen ───────────────────────────────────────────────────────────

function LoadingScreen({ step, progress }) {
  return (
    <div className="screen screen--loading">
      <Header />
      <div className="loading-content">
        <div className="loading-emoji">📊</div>
        <h2 className="loading-title">מנתח את הנתונים...</h2>
        <p className="loading-sub">{LOADING_STEPS[Math.min(step, LOADING_STEPS.length - 1)]}</p>
        <div className="progress-wrap">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="progress-pct">{progress}%</div>
      </div>
    </div>
  );
}

// ─── Fund Results Section ─────────────────────────────────────────────────────

function FundResults({ data }) {
  const { client, alternatives } = data;
  const isNew = client.grade === 0;
  const pct = client.rank != null && client.total
    ? Math.round((1 - (client.rank - 1) / client.total) * 100)
    : 0;
  const isBelow = !isNew && client.rank != null && client.rank > client.total / 2;
  const isAbove = !isNew && client.rank != null && client.rank <= client.total / 2;

  // Approx annual return from grade
  const clientReturn = isNew ? 0 : +(client.grade / 10).toFixed(2);
  const altReturns = alternatives.map(a => +(a.grade / 10).toFixed(2));
  const maxReturn = Math.max(clientReturn, ...altReturns, 0.1);

  const bestPotential = alternatives.reduce((m, a) => Math.max(m, a.potential), 0);
  const gainPct = client.amount > 0 ? Math.round((bestPotential / client.amount - 1) * 100) : 0;

  return (
    <div className="fund-results fade-in">

      {/* 1 ─ Client Header Card */}
      <div className="client-card">
        <div className="client-card-info">
          <div className="client-card-badge">פרטי הקופה</div>
          <div className="client-fund-name">{client.name}</div>
          <div className="client-fund-meta">
            קופה #{client.id}
            {client.total && <> · מקום {client.rank} מתוך {client.total} קופות</>}
          </div>
        </div>
        <div className="client-card-gauge">
          <Gauge rank={client.rank} total={client.total} />
          {client.rank != null && (
            <div className="gauge-label">
              מקום {client.rank} מתוך {client.total}
            </div>
          )}
        </div>
      </div>

      {/* 2 ─ Stats Row */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">סכום צבירה</div>
          <div className="stat-value">₪{fmt(client.amount)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">תשואה שנתית ממוצעת</div>
          <div className="stat-value stat-value--amber">
            {isNew ? 'N/A' : `${fmtDec(clientReturn)}%`}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">תשואה כוללת</div>
          <div className="stat-value">
            {isNew ? 'N/A' : `${fmtDec(client.grade / 5)}%`}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">דמי ניהול כוללים</div>
          <div className="stat-value">1.00%</div>
        </div>
      </div>

      {/* 3 ─ Rating Banner */}
      {isNew && (
        <div className="rating-banner rating-banner--blue">
          <span className="rating-banner-icon">ℹ️</span>
          <div>
            <div className="rating-banner-title">הקופה שלך חדשה — אין מספיק נתונים לדירוג מלא</div>
            <div className="rating-banner-sub">
              קופה מקום {client.rank} מתוך {client.total} קופות · הנתונים יתעדכנו עם הצטברות תשואות
            </div>
          </div>
        </div>
      )}
      {isBelow && (
        <div className="rating-banner rating-banner--red">
          <span className="rating-banner-icon">⚠️</span>
          <div>
            <div className="rating-banner-title">הקופה שלך מדורגת מתחת לממוצע</div>
            <div className="rating-banner-sub">
              מקום {client.rank} מתוך {client.total} — {Math.round(pct)}% מהקופות מציגות תשואה נמוכה יותר
            </div>
          </div>
        </div>
      )}
      {isAbove && (
        <div className="rating-banner rating-banner--green">
          <span className="rating-banner-icon">✅</span>
          <div>
            <div className="rating-banner-title">הקופה שלך מדורגת מעל לממוצע</div>
            <div className="rating-banner-sub">
              מקום {client.rank} מתוך {client.total} — ביצועים טובים ממרבית הקופות
            </div>
          </div>
        </div>
      )}

      {/* 4 ─ Bar Chart */}
      <div className="chart-card">
        <div className="chart-header">
          <div className="chart-title">השוואת תשואות שנתיות ברוטו (בניכוי ד"נ)</div>
          <div className="chart-sub">השוואה מול {client.total ?? '–'} קופות באותה רמת סיכון</div>
        </div>
        <div className="chart-bars">
          {/* Client bar */}
          <div className="bar-row">
            <div className="bar-label">{shortName(client.name)}</div>
            <div className="bar-track">
              <div
                className="bar-fill bar-fill--red"
                style={{ width: `${Math.max((clientReturn / maxReturn) * 100, isNew ? 0 : 2)}%` }}
              >
                <span className="bar-pct">{isNew ? '0%' : `${fmtDec(clientReturn)}%`}</span>
              </div>
            </div>
          </div>
          {/* Alternative bars */}
          {alternatives.map((alt, i) => (
            <div key={alt.id} className="bar-row">
              <div className="bar-label">{shortName(alt.name)}</div>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{
                    width: `${Math.max((altReturns[i] / maxReturn) * 100, 2)}%`,
                    background: ALT_COLORS[i],
                  }}
                >
                  <span className="bar-pct">{fmtDec(altReturns[i])}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 5 ─ Alternatives Table */}
      <div className="table-card">
        <div className="table-title">🏆 3 החלופות הטובות ביותר</div>
        <div className="table-wrap">
          <table className="alts-table">
            <thead>
              <tr>
                <th>דירוג</th>
                <th>שם הקופה</th>
                <th>תשואה שנתית</th>
                <th>ציון</th>
                <th>סכום פוטנציאלי</th>
                <th>הפרש</th>
              </tr>
            </thead>
            <tbody>
              {alternatives.map((alt, i) => (
                <tr key={alt.id} className="row-alt">
                  <td>
                    <span className="rank-badge" style={{ background: ALT_COLORS[i] }}>{i + 1}</span>
                  </td>
                  <td className="td-name">{alt.name}</td>
                  <td className="td-return" style={{ color: ALT_COLORS[i] }}>{fmtDec(alt.grade / 10)}%</td>
                  <td className="td-score">{fmtDec(alt.grade)}</td>
                  <td className="td-potential">₪{fmt(alt.potential)}</td>
                  <td className="td-diff">
                    <span className="diff-badge">+₪{fmt(alt.potential - client.amount)}</span>
                  </td>
                </tr>
              ))}
              {/* Client row */}
              <tr className="row-client">
                <td>
                  <span className="rank-badge rank-badge--client">–</span>
                </td>
                <td className="td-name">{client.name}</td>
                <td className="td-return" style={{ color: '#EF4444' }}>
                  {isNew ? 'N/A' : `${fmtDec(clientReturn)}%`}
                </td>
                <td className="td-score">{isNew ? '–' : fmtDec(client.grade)}</td>
                <td className="td-potential">₪{fmt(client.amount)}</td>
                <td className="td-diff">–</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* High-risk option box */}
      {gainPct > 0 && (
        <div className="highrisk-card">
          <div className="highrisk-icon">⚡</div>
          <div className="highrisk-body">
            <div className="highrisk-title">אופציית סיכון גבוה</div>
            <div className="highrisk-desc">
              עם המעבר לקופה המובילה, יכולת הצבירה שלך עשויה לגדול ב-
              <strong className="highrisk-pct"> {gainPct}%</strong>
            </div>
            <div className="highrisk-amounts">
              <div className="highrisk-amount-item">
                <div className="highrisk-amount-label">היום</div>
                <div className="highrisk-amount-val">₪{fmt(client.amount)}</div>
              </div>
              <div className="highrisk-arrow">←</div>
              <div className="highrisk-amount-item">
                <div className="highrisk-amount-label">פוטנציאל</div>
                <div className="highrisk-amount-val highrisk-amount-val--green">₪{fmt(bestPotential)}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 6 ─ Action Buttons */}
      <div className="action-row">
        <button className="btn-pdf">📥 הורד דוח PDF</button>
        <button className="btn-sms">📤 שלח ב-SMS ללקוח</button>
      </div>

      {/* 7 ─ Disclaimer */}
      <div className="disclaimer">
        הנתונים מבוססים על מידע מהמסלקה הפנסיונית ומגמל נט של רשות שוק ההון · אין לראות בכך ייעוץ השקעות
      </div>
    </div>
  );
}

// ─── Results Screen ───────────────────────────────────────────────────────────

function ResultsScreen({ results, onReset }) {
  return (
    <div className="screen screen--results">
      <Header onReset={onReset} />
      <div className="results-content">
        {(results || []).map((data, i) => (
          <FundResults key={data.client.id + '-' + i} data={data} />
        ))}
      </div>
    </div>
  );
}

// ─── Root App ─────────────────────────────────────────────────────────────────

function App() {
  const [screen, setScreen] = useState('upload');
  const [mislakaFile, setMislakaFile] = useState(null);
  const [gemelnetFile, setGemelnetFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const [progress, setProgress] = useState(0);

  const handleAnalyze = async () => {
    setScreen('loading');
    setLoadingStep(0);
    setProgress(0);

    let prog = 0;
    let stepIdx = 0;
    const interval = setInterval(() => {
      prog = Math.min(prog + 1.2, 92);
      setProgress(Math.round(prog));
      const newStep = Math.min(Math.floor(prog / 24), LOADING_STEPS.length - 1);
      if (newStep !== stepIdx) {
        stepIdx = newStep;
        setLoadingStep(newStep);
      }
    }, 80);

    try {
      const formData = new FormData();
      formData.append('mislaka_file', mislakaFile);
      formData.append('gemelnet_file', gemelnetFile);
      const res = await fetch('http://localhost:8000/compare', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      clearInterval(interval);
      setProgress(100);
      setTimeout(() => {
        setResults(groupResults(data));
        setScreen('results');
      }, 500);
    } catch (err) {
      clearInterval(interval);
      console.error(err);
      alert('שגיאה בניתוח הנתונים. אנא בדוק שהשרת פועל ונסה שוב.');
      setScreen('upload');
    }
  };

  if (screen === 'loading') {
    return <LoadingScreen step={loadingStep} progress={progress} />;
  }
  if (screen === 'results') {
    return <ResultsScreen results={results} onReset={() => setScreen('upload')} />;
  }
  return (
    <UploadScreen
      mislakaFile={mislakaFile}
      gemelnetFile={gemelnetFile}
      onMislaka={setMislakaFile}
      onGemelnet={setGemelnetFile}
      onAnalyze={handleAnalyze}
    />
  );
}

export default App;
