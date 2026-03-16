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
const ALT_GRADIENTS = [
  'linear-gradient(90deg,#10B981,#34D399)',
  'linear-gradient(90deg,#3B82F6,#60A5FA)',
  'linear-gradient(90deg,#8B5CF6,#A78BFA)',
];

// ─── Utilities ────────────────────────────────────────────────────────────────

const fmt = n => Math.round(n).toLocaleString('he-IL');
const fmtDec = (n, d = 1) => (+n).toFixed(d);
const shortName = name => name?.split(' ').slice(0, 3).join(' ') || name;

const formatDate = (dateStr) => {
  if (!dateStr || dateStr.length < 8) return dateStr;
  const year = dateStr.substring(0, 4);
  const month = dateStr.substring(4, 6);
  const day = dateStr.substring(6, 8);
  return `${day}/${month}/${year}`;
};

// ─── Gauge SVG ────────────────────────────────────────────────────────────────

function GaugeChart({ percentile, rank, total }) {
  const pct = percentile ?? 0;
  const percentage = pct / 100;
  const angle = percentage * Math.PI;
  const radius = 52;
  const cx = 65;
  const cy = 65;

  const startX = cx - radius; // 13
  const startY = cy;           // 65
  const endX = cx + radius * Math.cos(Math.PI - angle);
  const endY = cy - radius * Math.sin(Math.PI - angle);
  const largeArc = angle > Math.PI ? 1 : 0;

  const color = pct >= 60 ? '#10B981' : pct >= 30 ? '#F59E0B' : '#EF4444';

  return (
    <div style={{ textAlign: 'center', width: '140px' }}>
      <svg width="130" height="75" viewBox="0 0 130 75">
        {/* Gray track */}
        <path
          d="M 13 65 A 52 52 0 0 1 117 65"
          fill="none"
          stroke="#1E293B"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Colored fill */}
        {pct > 0 && (
          <path
            d={`M ${startX} ${startY} A ${radius} ${radius} 0 ${largeArc} 1 ${endX.toFixed(2)} ${endY.toFixed(2)}`}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
          />
        )}
        {/* Percentile number */}
        <text x="65" y="50" textAnchor="middle" fill="#F8FAFC" fontSize="26" fontWeight="700" fontFamily="Rubik, sans-serif">
          {pct}
        </text>
        <text x="65" y="67" textAnchor="middle" fill="#94A3B8" fontSize="10" fontFamily="Rubik, sans-serif">
          {`אחוזון ${pct}`}
        </text>
      </svg>
      {rank != null && total != null && (
        <div style={{ fontSize: '12px', fontWeight: '600', color: color, marginTop: '2px' }}>
          {`מקום ${rank} מתוך ${total}`}
        </div>
      )}
    </div>
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

function UploadScreen({ mislakaFile, onMislaka, onAnalyze }) {
  const ready = mislakaFile;
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

  const pct = client.percentile ?? 0;
  const isBelow = !isNew && pct < 50;
  const isAbove = !isNew && pct >= 50;

  // Bar chart: proportional to actual tsua_1 values (filter zeros for max)
  const clientTsua1 = client.tsua_1 ?? 0;
  const allTsua = [client.tsua_1, ...alternatives.map(a => a.tsua_1)].filter(v => v > 0);
  const maxTsua = Math.max(...allTsua, 0.1);

  // Best alternative for high-risk section
  const bestAlt = alternatives[0];
  const diffPct = bestAlt?.diff_percent ?? 0;

  return (
    <div className="fund-results fade-in fund-section">

      {/* 1 ─ Client Header Card */}
      <div className="client-card">
        <div className="client-card-info">
          <div className="client-card-badge">פרטי הקופה</div>
          <div className="client-fund-name">{client.name}</div>
          <div className="client-fund-meta">
            קופה #{client.id}
            {client.hevra && <> · {client.hevra}</>}
            {client.seniority_date && <> · ותק מ-{formatDate(client.seniority_date)}</>}
            {client.total_in_risk != null && (
              <> · מקום {client.rank} מתוך {client.total_in_risk} קופות</>
            )}
          </div>
        </div>
        <div className="gauge-container">
          <GaugeChart
            percentile={pct}
            rank={client.rank}
            total={client.total_in_risk}
          />
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
            {client.tsua_1 ? `${fmtDec(client.tsua_1)}%` : 'N/A'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">תשואה שנתית ממוצעת 3 שנים</div>
          <div className="stat-value">
            {isNew || !client.tsua_3 ? 'N/A' : `${fmtDec(client.tsua_3)}%`}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">דמי ניהול כוללים</div>
          <div className="stat-value">
            {client.dmei_nihul != null ? `${fmtDec(client.dmei_nihul)}%` : '—'}
          </div>
        </div>
      </div>

      {/* 3 ─ Rating Banner */}
      {isNew && (
        <div className="rating-banner rating-banner--blue">
          <span className="rating-banner-icon">ℹ️</span>
          <div>
            <div className="rating-banner-title">הקופה שלך חדשה — אין מספיק נתונים לדירוג מלא</div>
            <div className="rating-banner-sub">
              {client.total_in_risk != null && <>קופה מקום {client.rank} מתוך {client.total_in_risk} קופות · </>}
              הנתונים יתעדכנו עם הצטברות תשואות
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
              מקום {client.rank} מתוך {client.total_in_risk} — {pct}% מהקופות מציגות תשואה נמוכה יותר
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
              מקום {client.rank} מתוך {client.total_in_risk} — ביצועים טובים ממרבית הקופות
            </div>
          </div>
        </div>
      )}

      {/* 4 ─ Bar Chart */}
      <div className="chart-card">
        <div className="chart-header">
          <div className="chart-title">השוואת תשואות שנתיות ברוטו (בניכוי ד"נ)</div>
          <div className="chart-sub">השוואה מול {client.total_in_risk ?? '–'} קופות באותה רמת סיכון</div>
        </div>
        <div className="chart-bars">
          {/* Client bar */}
          <div className="bar-row">
            <div className="bar-label">{shortName(client.name)}</div>
            <div className="bar-track">
              <div
                className="bar-fill bar-fill--red"
                style={{ width: clientTsua1 > 0 ? `${(clientTsua1 / maxTsua) * 100}%` : '5%' }}
              >
                <span className="bar-pct">
                  {clientTsua1 > 0 ? `${fmtDec(clientTsua1)}%` : '—'}
                </span>
              </div>
            </div>
          </div>
          {/* Alternative bars */}
          {alternatives.map((alt, i) => {
            const tsua = alt.tsua_1 ?? 0;
            return (
              <div key={alt.id} className="bar-row">
                <div className="bar-label">{shortName(alt.name)}</div>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{
                      width: `${Math.max((tsua / maxTsua) * 100, 2)}%`,
                      background: ALT_GRADIENTS[i] || ALT_COLORS[i],
                    }}
                  >
                    <span className="bar-pct">{fmtDec(tsua)}%</span>
                  </div>
                </div>
              </div>
            );
          })}
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
              {alternatives.map((alt, i) => {
                const diffNeg = alt.diff < 0;
                return (
                  <tr key={alt.id} className="row-alt">
                    <td>
                      <span className="rank-badge" style={{ background: ALT_COLORS[i] }}>
                        {alt.rank}
                      </span>
                    </td>
                    <td className="td-name">
                      <div>{alt.name}</div>
                      {alt.hevra && <div className="td-name-sub">{alt.hevra}</div>}
                      <div className="td-name-sub">קופה #{alt.id}</div>
                    </td>
                    <td className="td-return" style={{ color: ALT_COLORS[i] }}>
                      {alt.tsua_1 != null ? `${fmtDec(alt.tsua_1)}%` : 'N/A'}
                    </td>
                    <td className="td-score">{fmtDec(alt.grade)}</td>
                    <td className="td-potential">
                      {alt.potential_amount != null ? `₪${fmt(alt.potential_amount)}` : '—'}
                    </td>
                    <td className="td-diff">
                      {alt.diff != null ? (
                        <div>
                          <span
                            className="diff-badge"
                            style={{ background: diffNeg ? 'rgba(239,68,68,0.15)' : undefined, color: diffNeg ? '#EF4444' : undefined }}
                          >
                            {diffNeg ? '' : '+'}₪{fmt(Math.abs(alt.diff))}
                          </span>
                          {alt.diff_percent != null && (
                            <div className="diff-pct" style={{ color: diffNeg ? '#EF4444' : '#10B981' }}>
                              {diffNeg ? '' : '+'}{fmtDec(alt.diff_percent)}%
                            </div>
                          )}
                        </div>
                      ) : '—'}
                    </td>
                  </tr>
                );
              })}
              {/* Client row */}
              <tr className="row-client">
                <td>
                  <span className="rank-badge rank-badge--client">{client.rank ?? '–'}</span>
                </td>
                <td className="td-name">
                  <div>{client.name}</div>
                  {client.hevra && <div className="td-name-sub">{client.hevra}</div>}
                  <div className="td-name-sub">קופה #{client.id}</div>
                  <div className="td-name-tag">הקופה שלך</div>
                </td>
                <td className="td-return" style={{ color: '#EF4444' }}>
                  {client.tsua_1 ? `${fmtDec(client.tsua_1)}%` : 'N/A'}
                </td>
                <td className="td-score">{isNew || !client.grade ? '–' : fmtDec(client.grade)}</td>
                <td className="td-potential">₪{fmt(client.amount)}</td>
                <td className="td-diff">—</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* 6 ─ High-risk option box */}
      {bestAlt && diffPct > 0 && (
        <div className="highrisk-card">
          <div className="highrisk-icon">⚡</div>
          <div className="highrisk-body">
            <div className="highrisk-title">אופציית סיכון גבוה</div>
            <div className="highrisk-desc">
              עם המעבר לקופה המובילה לפני שנה, יכולת הצבירה שלך הייתה גדלה ב-
              <strong className="highrisk-pct"> {fmtDec(diffPct)}%</strong>
            </div>
            <div className="highrisk-amounts">
              <div className="highrisk-amount-item">
                <div className="highrisk-amount-label">היום</div>
                <div className="highrisk-amount-val">₪{fmt(client.amount)}</div>
                {client.tsua_1 ? (
                  <div className="highrisk-amount-sub">{fmtDec(client.tsua_1)}% תשואה</div>
                ) : null}
              </div>
              <div className="highrisk-arrow">←</div>
              <div className="highrisk-amount-item">
                <div className="highrisk-amount-label">פוטנציאל</div>
                <div className="highrisk-amount-val highrisk-amount-val--green">
                  {bestAlt.potential_amount != null ? `₪${fmt(bestAlt.potential_amount)}` : '—'}
                </div>
                {bestAlt.tsua_1 ? (
                  <div className="highrisk-amount-sub">{fmtDec(bestAlt.tsua_1)}% תשואה</div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      )}

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
      <div id="results-content" className="results-content">
        {(results || []).map((data, i) => (
          <div key={(data.client?.id ?? i) + '-' + i}>
            <FundResults data={data} />
          </div>
        ))}
        <div className="pdf-button-container">
          <button
            className="download-pdf-btn"
            onClick={() => alert('בקרוב...')}
          >
            📥 הורד דוח PDF
          </button>
        </div>
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
      formData.append('weight_1', 100);
      formData.append('weight_3', 0);
      formData.append('weight_5', 0);
      formData.append('weight_sharp', 0);
      formData.append('mislaka_file', mislakaFile);
      const res = await fetch('http://localhost:8000/compare', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      clearInterval(interval);
      setProgress(100);
      setTimeout(() => {
        // New API returns { funds: [...] }
        const funds = data.funds ?? data;
        setResults(Array.isArray(funds) ? funds : [funds]);
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
