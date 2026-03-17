import { useState, useRef, useMemo } from 'react';
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

const RISK_LABELS = { low: 'נמוכה', medium: 'בינונית', high: 'גבוהה' };
const RISK_COLORS = { low: '#10B981', medium: '#3B82F6', high: '#F59E0B' };

const DEFAULT_WEIGHTS = { w1: 10, w3: 20, w5: 25, wSharp: 45 };

const WEIGHT_FIELDS = [
  { field: 'w1',     label: 'תשואה שנה' },
  { field: 'w3',     label: 'תשואה 3 שנים' },
  { field: 'w5',     label: 'תשואה 5 שנים' },
  { field: 'wSharp', label: 'Sharp Ratio' },
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

// ─── Stars Background ─────────────────────────────────────────────────────────

function Stars() {
  const stars = useMemo(() => Array.from({ length: 180 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: Math.random() * 1.8 + 0.4,
    opacity: Math.random() * 0.6 + 0.2,
    duration: Math.random() * 4 + 2,
    delay: Math.random() * 4,
  })), []);

  return (
    <div className="stars-bg" aria-hidden="true">
      {stars.map(s => (
        <div
          key={s.id}
          className="star"
          style={{
            left: `${s.x}%`,
            top: `${s.y}%`,
            width: `${s.size}px`,
            height: `${s.size}px`,
            opacity: s.opacity,
            animationDuration: `${s.duration}s`,
            animationDelay: `${s.delay}s`,
          }}
        />
      ))}
    </div>
  );
}

// ─── Gauge SVG ────────────────────────────────────────────────────────────────

function GaugeChart({ percentile, rank, total }) {
  const pct = percentile ?? 0;
  const percentage = pct / 100;
  const angle = percentage * Math.PI;
  const radius = 52;
  const cx = 65;
  const cy = 65;

  const startX = cx - radius;
  const startY = cy;
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
          <div className="header-logo">
            <svg width="46" height="46" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="logoGrad" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#60A5FA"/>
                  <stop offset="100%" stopColor="#A78BFA"/>
                </linearGradient>
                <linearGradient id="eyeGrad" x1="4" y1="16" x2="28" y2="16" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#fff" stopOpacity="0.15"/>
                  <stop offset="100%" stopColor="#fff" stopOpacity="0.05"/>
                </linearGradient>
              </defs>
              {/* Eye shape */}
              <path d="M4 16 C8 9, 24 9, 28 16 C24 23, 8 23, 4 16 Z" fill="url(#eyeGrad)" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
              {/* Pupil */}
              <circle cx="16" cy="16" r="4.5" fill="url(#logoGrad)" opacity="0.9"/>
              <circle cx="16" cy="16" r="2" fill="white" opacity="0.95"/>
              {/* Chart line inside eye */}
              <polyline points="7,18 10,15 13,17 16,13 19,15 22,11 25,13" stroke="url(#logoGrad)" strokeWidth="1.4" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
              {/* Top dot on chart */}
              <circle cx="22" cy="11" r="1.3" fill="#A78BFA"/>
            </svg>
          </div>
          <div className="header-text">
            <span className="header-title">AmoSight</span>
            <span className="header-subtitle">ניתוח והשוואת קופות גמל</span>
          </div>
        </div>
      </div>
    </header>
  );
}

// ─── Weights Form ─────────────────────────────────────────────────────────────

function WeightsForm({ weights, onChange }) {
  const fields = WEIGHT_FIELDS.map(f => f.field);
  const sum = fields.reduce((s, f) => s + weights[f], 0);
  const isValid = sum === 100;

  const handleStep = (idx, delta) => {
    const next = { ...weights };
    const target = fields[idx];
    const newVal = next[target] + delta;
    if (newVal < 0 || newVal > 100) return;

    let remaining = delta;
    let cursor = (idx + 1) % fields.length;
    const visited = new Set([idx]);

    while (remaining !== 0 && !visited.has(cursor)) {
      visited.add(cursor);
      const cur = next[fields[cursor]];
      if (remaining > 0) {
        const take = Math.min(remaining, cur);
        next[fields[cursor]] -= take;
        remaining -= take;
      } else {
        const give = Math.min(-remaining, 100 - cur);
        next[fields[cursor]] += give;
        remaining += give;
      }
      if (remaining !== 0) cursor = (cursor + 1) % fields.length;
    }

    if (remaining === 0) {
      next[target] = newVal;
      onChange(next);
    }
  };

  return (
    <div className="weights-form">
      <div className="weights-form-title">הגדרת משקלות לחישוב AmoScore</div>
      <div className="weights-grid">
        {WEIGHT_FIELDS.map(({ field, label }, idx) => (
          <div key={field} className="weight-field">
            <label className="weight-label">{label}</label>
            <div className="weight-stepper">
              <button className="weight-btn" onClick={() => handleStep(idx, -5)}>−</button>
              <span className="weight-val">{weights[field]}%</span>
              <button className="weight-btn" onClick={() => handleStep(idx, +5)}>+</button>
            </div>
          </div>
        ))}
      </div>
      <div className={`weights-sum${isValid ? ' weights-sum--valid' : ' weights-sum--invalid'}`}>
        סכום: <strong>{sum}</strong>/100
        {isValid ? ' ✓' : ` — נדרש בדיוק 100 (${sum < 100 ? `חסרים ${100 - sum}` : `עודף ${sum - 100}`})`}
      </div>
    </div>
  );
}

// ─── Multi Upload Zone ────────────────────────────────────────────────────────

function MultiUploadZone({ files, onFiles, onRemoveFile }) {
  const inputRef = useRef();

  const handleChange = (e) => {
    const newFiles = Array.from(e.target.files);
    const valid = newFiles.filter(f => /\.(xml|dat)$/i.test(f.name));
    const invalid = newFiles.filter(f => !/\.(xml|dat)$/i.test(f.name));
    if (invalid.length > 0) {
      alert(
        `הקבצים הבאים אינם נתמכים:\n${invalid.map(f => f.name).join('\n')}\n\nניתן להעלות קבצי XML ו-DAT בלבד.`
      );
    }
    if (valid.length > 0) {
      onFiles([...files, ...valid]);
    }
    e.target.value = '';
  };

  const hasFiles = files.length > 0;

  return (
    <div className="multi-upload-wrap">
      <div
        className={`upload-zone${hasFiles ? ' upload-zone--done' : ''}`}
        onClick={() => inputRef.current.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xml,.dat"
          multiple
          style={{ display: 'none' }}
          onChange={handleChange}
        />
        <div className={`upload-file-icon${hasFiles ? ' done' : ''}`}>
          {hasFiles ? '✓' : '📄'}
        </div>
        <div className="upload-label">קבצי מסלקה פנסיונית</div>
        <div className="upload-sub">
          {hasFiles
            ? files.length === 1 ? '1 קובץ נטען' : `${files.length} קבצים נטענו`
            : 'לחץ לבחירת קבצי XML או DAT (ניתן לבחור מספר קבצים)'}
        </div>
      </div>
      {hasFiles && (
        <div className="file-list">
          {files.map((f, i) => (
            <div key={i} className="file-list-item">
              <span className="file-list-name">📄 {f.name}</span>
              <button
                className="file-list-remove"
                onClick={(e) => { e.stopPropagation(); onRemoveFile(i); }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Upload Screen ────────────────────────────────────────────────────────────

function UploadScreen({ mislakaFiles, onMislakaFiles, onRemoveMislakaFile, weights, onWeightsChange, onAnalyze }) {
  const sum = weights.w1 + weights.w3 + weights.w5 + weights.wSharp;
  const ready = mislakaFiles.length > 0 && sum === 100;

  return (
    <div className="screen screen--upload">
      <Stars />
      <Header />
      <div className="upload-content">
        <div className="hero">
          <h1 className="hero-title">בדוק את הביצועים של הקופה שלך</h1>
          <p className="hero-sub">
            העלה את קבצי ה-XML מהמסלקה הפנסיונית וקבל ניתוח מקיף של ביצועי הקופה שלך מול השוק
          </p>
        </div>

        <div className="upload-row">
          <MultiUploadZone
            files={mislakaFiles}
            onFiles={onMislakaFiles}
            onRemoveFile={onRemoveMislakaFile}
          />
        </div>

        <WeightsForm weights={weights} onChange={onWeightsChange} />

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
              <div className="info-desc">הצגת 3 קופות עם AmoScore גבוה יותר</div>
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
      <Stars />
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

function FundResults({ data, weights }) {
  const { client, alternatives } = data;
  const isNew = client.grade === 0;

  const pct = client.percentile ?? 0;
  const isBelow = !isNew && pct < 50;
  const isAbove = !isNew && pct >= 50;

  // Bar chart: proportional to actual tsua_1 values
  const clientTsua1 = client.tsua_1 ?? 0;
  const allTsua = [client.tsua_1, ...alternatives.map(a => a.tsua_1)].filter(v => v > 0);
  const maxTsua = Math.max(...allTsua, 0.1);

  // Best alternative for high-risk section
  const bestAlt = alternatives[0];
  const diffPct = bestAlt?.diff_percent ?? 0;

  // Risk display
  const riskLabel = RISK_LABELS[client.risk_level] ?? client.risk_level ?? '—';
  const riskColor = RISK_COLORS[client.risk_level] ?? '#94A3B8';

  // Merge client + alternatives, sort by AmoScore descending
  const clientEntry = {
    ...client,
    isClient: true,
    potential_amount: client.amount,
    diff: null,
    diff_percent: null,
  };
  const sortedFunds = [
    ...alternatives.map(a => ({ ...a, isClient: false })),
    clientEntry,
  ].sort((a, b) => (b.grade ?? 0) - (a.grade ?? 0));

  // Assign colors: client green if rank 1-3, otherwise red; alts get ALT_COLORS in order
  const clientIsTop = client.rank != null && client.rank <= 3;
  let altColorIdx = 0;
  const fundColors = sortedFunds.map(f => {
    if (f.isClient) return clientIsTop ? '#10B981' : '#EF4444';
    const color = ALT_COLORS[altColorIdx % ALT_COLORS.length];
    altColorIdx++;
    return color;
  });

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
            {client.risk_level && (
              <> · רמת סיכון: <strong style={{ color: riskColor }}>{riskLabel}</strong></>
            )}
          </div>
        </div>
        <div className="gauge-container">
          <div className="gauge-amoscore-label">AmoScore</div>
          <div className="gauge-amoscore-value">{isNew || !client.grade ? '–' : fmtDec(client.grade)}</div>
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
                className={`bar-fill ${clientIsTop ? 'bar-fill--client' : 'bar-fill--red'}`}
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

      {/* 5 ─ Alternatives Table — sorted by AmoScore */}
      <div className="table-card">
        <div className="table-title">🏆 השוואת קופות לפי AmoScore</div>
        <div className="table-wrap">
          <table className="alts-table">
            <thead>
              <tr>
                <th>דירוג</th>
                <th>שם הקופה</th>
                <th>תשואה שנתית</th>
                <th>AmoScore</th>
                <th>סכום פוטנציאלי *</th>
                <th>הפרש</th>
              </tr>
            </thead>
            <tbody>
              {sortedFunds.map((fund, idx) => {
                const color = fundColors[idx];
                const diffNeg = fund.diff != null && fund.diff < 0;
                return (
                  <tr key={fund.id} className={fund.isClient ? (clientIsTop ? 'row-client' : 'row-client row-client--bad') : 'row-alt'}>
                    <td>
                      <span
                        className="rank-badge"
                        style={{
                          background: `${color}33`,
                          color: color,
                        }}
                      >
                        {fund.isClient ? (fund.rank ?? '–') : idx + 1}
                      </span>
                    </td>
                    <td className="td-name">
                      <div>{fund.name}</div>
                      {fund.hevra && <div className="td-name-sub">{fund.hevra}</div>}
                      <div className="td-name-sub">קופה #{fund.id}</div>
                      {fund.isClient && (
                        <div className={`td-name-tag ${clientIsTop ? 'td-name-tag--client' : 'td-name-tag--client-bad'}`}>הקופה שלך</div>
                      )}
                    </td>
                    <td className="td-return" style={{ color }}>
                      {fund.tsua_1 != null ? `${fmtDec(fund.tsua_1)}%` : 'N/A'}
                    </td>
                    <td className="td-score">
                      {fund.grade ? fmtDec(fund.grade) : '–'}
                    </td>
                    <td className="td-potential">
                      {fund.potential_amount != null ? `₪${fmt(fund.potential_amount)}` : '—'}
                    </td>
                    <td className="td-diff">
                      {fund.diff != null ? (
                        <div>
                          <span
                            className="diff-badge"
                            style={{
                              background: diffNeg ? 'rgba(239,68,68,0.15)' : undefined,
                              color: diffNeg ? '#EF4444' : undefined,
                            }}
                          >
                            {diffNeg ? '' : '+'}₪{fmt(Math.abs(fund.diff))}
                          </span>
                          {fund.diff_percent != null && (
                            <div className="diff-pct" style={{ color: diffNeg ? '#EF4444' : '#10B981' }}>
                              {diffNeg ? '' : '+'}{fmtDec(fund.diff_percent)}%
                            </div>
                          )}
                        </div>
                      ) : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="table-footnote">
          * לא נוכו דמי ניהול חיצוניים מהחישוב
        </div>
        <div className="risk-note">
          רמת הסיכון נקבעת על פי רמת החשיפה למניות בחודש האחרון
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

      {/* 7 ─ AmoScore Explanation */}
      <div className="amoscore-explanation">
        <div className="amoscore-explanation-title">כיצד מחושב AmoScore?</div>
        <div className="amoscore-explanation-body">
          <p>AmoScore מחושב על בסיס 4 פרמטרים: תשואה שנה, תשואה 3 שנים, תשואה 5 שנים, ו-Sharp Ratio.</p>
          <p>כל פרמטר עובר נורמליזציה לסקאלה של 0–100 ביחס לכלל הקופות בהשוואה. לאחר מכן כל פרמטר מוכפל במשקל שנבחר, והציון הסופי הוא הסכום המשוקלל של כל הפרמטרים.</p>
          {weights && (
            <p className="amoscore-weights-used">
              החישוב בוצע עם המשקלות הבאים:
              תשואה שנה {weights.w1}% ·
              תשואה 3 שנים {weights.w3}% ·
              תשואה 5 שנים {weights.w5}% ·
              Sharp Ratio {weights.wSharp}%
            </p>
          )}
        </div>
      </div>

      {/* 8 ─ Disclaimer */}
      <div className="disclaimer">
        הנתונים מבוססים על מידע מהמסלקה הפנסיונית ומגמל נט של רשות שוק ההון · אין לראות בכך ייעוץ השקעות
      </div>
    </div>
  );
}

// ─── Results Screen ───────────────────────────────────────────────────────────

function ResultsScreen({ results, weights, onReset }) {
  const [selectedId, setSelectedId] = useState('all');

  const filtered = selectedId === 'all'
    ? (results || [])
    : (results || []).filter(d => d.client?.id === selectedId);

  return (
    <div className="screen screen--results">
      <Stars />
      <Header onReset={onReset} />
      <div id="results-content" className="results-content">

        {results && results.length > 1 && (
          <div className="results-filter">
            <label className="results-filter-label">הצג קופה:</label>
            <select
              className="results-filter-select"
              value={selectedId}
              onChange={e => setSelectedId(e.target.value)}
            >
              <option value="all">כל הקופות ({results.length})</option>
              {results.map((d, i) => (
                <option key={d.client?.id ?? i} value={d.client?.id}>
                  #{d.client?.id} — {d.client?.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {filtered.map((data, i) => (
          <div key={(data.client?.id ?? i) + '-' + i}>
            <FundResults data={data} weights={weights} />
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
  const [mislakaFiles, setMislakaFiles] = useState([]);
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [results, setResults] = useState(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const [progress, setProgress] = useState(0);

  const handleRemoveMislakaFile = (idx) => {
    setMislakaFiles(prev => prev.filter((_, i) => i !== idx));
  };

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
      formData.append('weight_1', weights.w1);
      formData.append('weight_3', weights.w3);
      formData.append('weight_5', weights.w5);
      formData.append('weight_sharp', weights.wSharp);
      mislakaFiles.forEach(f => formData.append('mislaka_file', f));

      const res = await fetch('http://localhost:8000/compare', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      clearInterval(interval);
      setProgress(100);
      setTimeout(() => {
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
    return <ResultsScreen results={results} weights={weights} onReset={() => setScreen('upload')} />;
  }
  return (
    <UploadScreen
      mislakaFiles={mislakaFiles}
      onMislakaFiles={setMislakaFiles}
      onRemoveMislakaFile={handleRemoveMislakaFile}
      weights={weights}
      onWeightsChange={setWeights}
      onAnalyze={handleAnalyze}
    />
  );
}

export default App;
