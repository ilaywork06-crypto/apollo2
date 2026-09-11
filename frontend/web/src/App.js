import { useState, useRef, useMemo, useCallback, useEffect, createContext, useContext } from 'react';
import './App.css';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

const ThemeContext = createContext({ theme: 'dark', toggleTheme: () => {} });


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

const COMMUNITY_RISK_COLORS = { high: '#EF4444', medium: '#F59E0B', low: '#10B981' };
const ANIMAL_EMOJIS = {
  'נשר': '🦅', 'דולפין': '🐬', 'אריה': '🦁', 'פנתר': '🐆',
  'זאב': '🐺', 'נמר': '🐯', 'עיט': '🦅', 'ינשוף': '🦉',
  'שועל': '🦊', 'דרקון': '🐉', 'נץ': '🦅', 'פלמינגו': '🦩',
  'דוב': '🐻', 'טיגריס': '🐅', 'חתול': '🐱',
};
const FUND_PALETTE = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444', '#EC4899'];
const getCommunityAvatar = name => ANIMAL_EMOJIS[name?.split(' ')[0]] || '🦁';
const MEDALS = ['🥇', '🥈', '🥉'];
const getRiskExposure = (thresholds) => ({
  low:    `0–${thresholds.low}% חשיפה למניות`,
  medium: `${thresholds.low}–${thresholds.medium}% חשיפה למניות`,
  high:   `${thresholds.medium}–130% חשיפה למניות`,
});

const DEFAULT_WEIGHTS = { w1: 10, w3: 20, w5: 25, wSharp: 35, wLiquidity: 10 };

// Order here is the order of the AmoScore weights bar and every weights legend
const WEIGHT_SEGMENTS = [
  { key: 'w1',         label: 'תשואה שנה',    gradient: 'linear-gradient(90deg,#059669,#10B981)', color: '#10B981' },
  { key: 'w3',         label: 'תשואה 3 שנים', gradient: 'linear-gradient(90deg,#2563EB,#3B82F6)', color: '#3B82F6' },
  { key: 'w5',         label: 'תשואה 5 שנים', gradient: 'linear-gradient(90deg,#7C3AED,#8B5CF6)', color: '#8B5CF6' },
  { key: 'wSharp',     label: 'Sharp Ratio',  gradient: 'linear-gradient(90deg,#D97706,#F59E0B)', color: '#F59E0B' },
  { key: 'wLiquidity', label: 'מדד נזילות',   gradient: 'linear-gradient(90deg,#DB2777,#EC4899)', color: '#EC4899' },
];

const sumWeights = w => WEIGHT_SEGMENTS.reduce((s, seg) => s + (w[seg.key] ?? 0), 0);
const isSameWeights = (a, b) => WEIGHT_SEGMENTS.every(seg => a[seg.key] === b[seg.key]);
const DEFAULT_WEIGHTS_TEXT = WEIGHT_SEGMENTS.map(seg => `${seg.label} ${DEFAULT_WEIGHTS[seg.key]}%`).join(' · ');

// Israeli share of a fund's equity component (the rest is abroad); 0–100 = no preference
const DEFAULT_GEO = { min: 0, max: 100 };
const GEO_PRESETS = [
  { label: 'ללא העדפה', min: 0,  max: 100 },
  { label: 'מוטה ישראל', min: 60, max: 100 },
  { label: 'מאוזן',      min: 30, max: 70 },
  { label: 'מוטה חו״ל',  min: 0,  max: 40 },
];
const isGeoActive = geo => geo.min > 0 || geo.max < 100;

// Fee mode for the alternative funds. The client's own fund is always net of their fee.
const FEE_MODES = [
  { key: 'net',   label: 'כולל דמי ניהול' },
  { key: 'gross', label: 'ללא דמי ניהול' },
];

const ALL_HEVROT = [
  'מיטב גמל ופנסיה בע"מ',
  'אלטשולר שחם גמל ופנסיה בע"מ',
  'הראל פנסיה וגמל בע"מ',
  'גלובלנט ניהול קופות גמל בע"מ',
  'אינפיניטי השתלמות, גמל ופנסיה בע"מ',
  'מנורה מבטחים פנסיה וגמל בע"מ',
  'מגדל מקפת קרנות פנסיה וקופות גמל בע"מ',
  'סלייס גמל בע"מ',
  'אקטיון בע"מ',
  'ילין לפידות ניהול קופות גמל בע"מ',
  'מור גמל ופנסיה בע"מ',
  'כלל פנסיה וגמל בע"מ',
  'קרן מקפת מרכז לפנסיה ותגמולים אגודה שיתופית בע"מ',
  'מבטחים מוסד לביטוח סוציאלי של העובדים בע"מ',
  'אנליסט קופות גמל בע"מ',
  'הפניקס פנסיה וגמל בע"מ',
];

const DEFAULT_BAD_HEVROT = new Set([
  'אינפיניטי השתלמות, גמל ופנסיה בע"מ',
  'גלובלנט ניהול קופות גמל בע"מ',
  'סלייס גמל בע"מ',
  'אקטיון בע"מ',
  'קרן מקפת מרכז לפנסיה ותגמולים אגודה שיתופית בע"מ',
  'מבטחים מוסד לביטוח סוציאלי של העובדים בע"מ',
]);

// ─── Utilities ────────────────────────────────────────────────────────────────

const fmt = n => Math.round(n).toLocaleString('he-IL');

// Hebrew count phrase: "קובץ אחד" / "3 קבצים"
const countOf = (n, one, many) => (n === 1 ? one : `${n.toLocaleString('he-IL')} ${many}`);
const filesCount = n => countOf(n, 'קובץ אחד', 'קבצים');
const fundsCount = n => countOf(n, 'קופה אחת', 'קופות');

const scoreColor = score =>
  score == null ? '#64748B' : score >= 70 ? '#10B981' : score >= 50 ? '#3B82F6' : score >= 30 ? '#F59E0B' : '#EF4444';
// A grade of 0 is ambiguous: "weakest on every metric" or "not enough data to score".
// The server says which in has_grade; older responses only had the grade.
export const hasGrade = fund => fund?.has_grade ?? (fund?.grade > 0);
const gradeText = fund => (hasGrade(fund) ? fmtDec(fund.grade) : '–');
const gradeOrNull = fund => (hasGrade(fund) ? fund.grade : null);

const scoreVerdict = score =>
  score == null ? 'אין מספיק נתונים' : score >= 70 ? 'מצוין' : score >= 50 ? 'טוב' : score >= 30 ? 'בינוני' : 'חלש';

// ─── Fee Mode ─────────────────────────────────────────────────────────────────

// An alternative as it should be shown under the chosen fee mode: the server sends
// figures net of the client's fee at the top level and the fee-free ones under `gross`.
export function withFeeMode(option, feeMode) {
  if (!option || feeMode !== 'gross' || !option.gross) return option;
  return { ...option, ...option.gross };
}

export function applyFeeMode(holding, feeMode) {
  return {
    ...holding,
    alternatives: (holding.alternatives ?? []).map(a => withFeeMode(a, feeMode)),
    golden: withFeeMode(holding.golden, feeMode),
  };
}

// ─── Fund Aggregation ─────────────────────────────────────────────────────────

// Projections are proportional to the balance, so a merged holding's NIS figures are the
// first instance's scaled by the balance ratio (exact — unlike rebuilding them from the
// rounded diff_percent). "No data" (null) stays null.
function rescaleProjection(option, factor) {
  const scaled = { ...option };
  for (const suffix of ['', '_3', '_5']) {
    for (const key of [`potential_amount${suffix}`, `diff${suffix}`]) {
      if (option[key] != null) scaled[key] = option[key] * factor;
    }
  }
  if (option.gross) scaled.gross = rescaleProjection(option.gross, factor);
  return scaled;
}

export function aggregateResults(results) {
  const groups = new Map();
  for (const item of results) {
    const id = item.client?.id;
    if (!groups.has(id)) {
      groups.set(id, { item, amount: item.client.amount ?? 0, count: 1 });
    } else {
      const group = groups.get(id);
      group.amount += item.client.amount ?? 0;
      group.count += 1;
    }
  }
  return Array.from(groups.values()).map(({ item, amount, count }) => {
    if (count === 1) return item;
    const factor = item.client.amount ? amount / item.client.amount : 1;
    return {
      ...item,
      client: { ...item.client, amount },
      alternatives: (item.alternatives ?? []).map(alt => rescaleProjection(alt, factor)),
      golden: item.golden && item.golden.id ? rescaleProjection(item.golden, factor) : item.golden,
    };
  });
}

const fmtDec = (n, d = 1) => n != null ? (+n).toFixed(d) : '—';
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
          stroke="var(--border)"
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
        <text x="65" y="50" textAnchor="middle" fill="var(--text-primary)" fontSize="26" fontWeight="700" fontFamily="Rubik, sans-serif">
          {pct}
        </text>
        <text x="65" y="67" textAnchor="middle" fill="var(--text-secondary)" fontSize="10" fontFamily="Rubik, sans-serif">
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

function Header({ onReset, resetLabel = '← ניתוח חדש' }) {
  const { theme, toggleTheme } = useContext(ThemeContext);
  return (
    <header className="app-header">
      <div className="header-inner">
        {/* Logo — always on the left */}
        <div className="header-brand">
          <div className="header-logo">
            <svg width="34" height="42" viewBox="-3 -3 36 44" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="hg" x1="15" y1="0" x2="15" y2="38" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#A78BFA"/>
                  <stop offset="100%" stopColor="#3B82F6"/>
                </linearGradient>
              </defs>
              <line x1="15" y1="2" x2="1" y2="34" stroke="url(#hg)" strokeWidth="4" strokeLinecap="round"/>
              <line x1="15" y1="2" x2="29" y2="34" stroke="url(#hg)" strokeWidth="4" strokeLinecap="round"/>
              <line x1="7" y1="21" x2="23" y2="21" stroke="url(#hg)" strokeWidth="3.5" strokeLinecap="round"/>
              <circle cx="15" cy="2" r="4" fill="#A78BFA"/>
            </svg>
          </div>
          <div className="header-text">
            <span className="header-title">
              <span className="header-title-amo">Amo</span><span className="header-title-sight">Sight</span>
            </span>
            <span className="header-subtitle">ניתוח והשוואת קופות גמל</span>
          </div>
        </div>

        {/* Right side: back button (when present) + theme toggle */}
        <div className="header-actions">
          {onReset && (
            <button className="btn-back" onClick={onReset}>{resetLabel}</button>
          )}
          <button
            className="theme-toggle-btn"
            onClick={toggleTheme}
            title={theme === 'dark' ? 'עבור למצב בהיר' : 'עבור למצב כהה'}
            aria-label={theme === 'dark' ? 'light mode' : 'dark mode'}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>
      </div>
    </header>
  );
}

// ─── Weights Form ─────────────────────────────────────────────────────────────

// Sum of the first `upTo` segment weights. Divider i sits between segment i and
// segment i+1; dragging it trades weight between those two only, so the total stays 100%.
const cumulative = (w, upTo) => WEIGHT_SEGMENTS.slice(0, upTo).reduce((s, seg) => s + w[seg.key], 0);

function WeightsForm({ weights, onChange }) {
  const barRef = useRef(null);
  const dragging = useRef(null);
  const wRef = useRef(weights);
  const onChangeRef = useRef(onChange);
  wRef.current = weights;
  onChangeRef.current = onChange;

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (dragging.current == null || !barRef.current) return;
      const rect = barRef.current.getBoundingClientRect();
      const raw = Math.round(((e.clientX - rect.left) / rect.width) * 100);
      const w = wRef.current;
      const i = dragging.current;
      const lo = cumulative(w, i);
      const hi = cumulative(w, i + 2);
      const v = Math.max(lo, Math.min(raw, hi));
      const left = WEIGHT_SEGMENTS[i].key;
      const right = WEIGHT_SEGMENTS[i + 1].key;
      onChangeRef.current({ ...w, [left]: v - lo, [right]: hi - v });
    };
    const handleMouseUp = () => {
      dragging.current = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const startDrag = (id) => (e) => {
    e.preventDefault();
    dragging.current = id;
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
  };

  const dividers = WEIGHT_SEGMENTS.slice(0, -1).map((_, i) => ({ id: i, pos: cumulative(weights, i + 1) }));

  return (
    <div className="weights-form">
      <div className="risk-band-bar-wrap" dir="ltr" ref={barRef}>
        <div className="risk-band-bar">
          {WEIGHT_SEGMENTS.map((seg) => (
            <div
              key={seg.key}
              className="risk-band-seg"
              style={{ width: `${weights[seg.key]}%`, background: seg.gradient }}
            >
              {weights[seg.key] >= 10 && (
                <span className="risk-band-seg-label">{weights[seg.key]}%</span>
              )}
            </div>
          ))}
        </div>

        {dividers.map(({ id, pos }) => (
          <div
            key={id}
            className="risk-band-marker risk-band-marker--draggable"
            style={{ left: `${pos}%` }}
            onMouseDown={startDrag(id)}
          >
            <div className="risk-band-marker-handle" />
            <div className="risk-band-marker-line" />
            <div className="risk-band-marker-label">{pos}%</div>
          </div>
        ))}
      </div>

      <div className="risk-band-legend">
        {WEIGHT_SEGMENTS.map((seg) => (
          <div key={seg.key} className="risk-band-legend-item">
            <span className="risk-band-dot" style={{ background: seg.color }} />
            <span className="risk-band-legend-text">
              <strong>{seg.label}</strong> — {weights[seg.key]}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Multi Upload Zone ────────────────────────────────────────────────────────

// ─── XML Tree Viewer ──────────────────────────────────────────────────────────

function TreeNode({ node, depth = 0 }) {
  const [expanded, setExpanded] = useState(depth < 2);

  const childElements = Array.from(node.children || []);
  const hasChildren = childElements.length > 0;
  const textValue = (!hasChildren && node.textContent) ? node.textContent.trim() : null;
  const childCount = hasChildren ? childElements.length : 0;

  return (
    <div>
      <div
        className="tree-row"
        style={{ paddingRight: `${depth * 20 + 12}px` }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren ? (
          <span className="tree-arrow">{expanded ? '▼' : '▶'}</span>
        ) : (
          <span className="tree-dot">●</span>
        )}
        <span className="tree-tag">{node.tagName}</span>
        {hasChildren && <span className="tree-count">({childCount})</span>}
        {textValue && <span className="tree-value">{textValue}</span>}
      </div>
      {expanded && hasChildren && (
        <div>
          {childElements.map((child, i) => (
            <TreeNode key={i} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Upload Zone ───────────────────────────────────────────────────────────────

// Files picked twice (same name, size and date) are kept once
const fileKey = f => `${f.name}|${f.size}|${f.lastModified}`;
function mergeFiles(existing, added) {
  const seen = new Set(existing.map(fileKey));
  return [...existing, ...added.filter(f => !seen.has(fileKey(f)) && seen.add(fileKey(f)))];
}

const COMPACT_LIST_LIMIT = 12;

function MultiUploadZone({ files, onFiles, onRemoveFile, onViewFile, label = 'קבצי מסלקה פנסיונית', hint, compact = false }) {
  const fileInputRef = useRef();
  const folderInputRef = useRef();
  const [showAll, setShowAll] = useState(false);

  const handleChange = (fromFolder) => (e) => {
    const newFiles = Array.from(e.target.files);
    const valid = newFiles.filter(f => /\.(xml|dat)$/i.test(f.name));
    if (valid.length > 0) {
      onFiles(mergeFiles(files, valid));
    } else {
      alert(fromFolder
        ? 'לא נמצאו קבצי XML או DAT בתיקייה שנבחרה.'
        : 'ניתן להעלות קבצי XML ו-DAT בלבד.');
    }
    e.target.value = '';
  };

  const hasFiles = files.length > 0;
  const listed = compact && !showAll ? files.slice(0, COMPACT_LIST_LIMIT) : files;
  const hiddenCount = files.length - listed.length;

  return (
    <div className="multi-upload-wrap">
      <div className={`upload-zone${hasFiles ? ' upload-zone--done' : ''}`}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xml,.dat"
          multiple
          style={{ display: 'none' }}
          onChange={handleChange(false)}
        />
        <input
          ref={folderInputRef}
          type="file"
          accept=".xml,.dat"
          webkitdirectory=""
          directory=""
          style={{ display: 'none' }}
          onChange={handleChange(true)}
        />
        <div className={`upload-file-icon${hasFiles ? ' done' : ''}`}>
          {hasFiles ? '✓' : '📄'}
        </div>
        <div className="upload-label">{label}</div>
        <div className="upload-sub">
          {hasFiles
            ? files.length === 1 ? '1 קובץ נטען' : `${files.length.toLocaleString('he-IL')} קבצים נטענו`
            : hint ?? 'בחר קבצים בודדים או תיקייה שלמה — ייטענו רק קבצי XML ו-DAT'}
        </div>
        <div className="upload-pick-actions">
          <button
            type="button"
            className="upload-pick-btn"
            onClick={() => fileInputRef.current.click()}
          >
            📄 בחירת קבצים
          </button>
          <button
            type="button"
            className="upload-pick-btn"
            onClick={() => folderInputRef.current.click()}
          >
            📁 בחירת תיקייה
          </button>
        </div>
      </div>
      {hasFiles && (
        <div className="file-list">
          {listed.map((f, i) => (
            <div key={fileKey(f)} className="file-list-item">
              <span className="file-list-name">📄 {f.name}</span>
              <div className="file-list-actions">
                {/\.(xml|dat)$/i.test(f.name) && (
                  <button
                    className="view-file-btn"
                    onClick={(e) => { e.stopPropagation(); onViewFile(f); }}
                  >
                    👁 הצג קובץ
                  </button>
                )}
                <button
                  className="file-list-remove"
                  onClick={(e) => { e.stopPropagation(); onRemoveFile(i); }}
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
          {compact && files.length > COMPACT_LIST_LIMIT && (
            <button type="button" className="file-list-more" onClick={() => setShowAll(s => !s)}>
              {showAll ? 'הצג פחות' : `ועוד ${hiddenCount.toLocaleString('he-IL')} קבצים — הצג הכל`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Risk Band Editor ─────────────────────────────────────────────────────────

const DEFAULT_THRESHOLDS = { low: 25, medium: 75 };

function RiskBandEditor({ low, medium, onChange, overrideRiskLevel, onOverrideRiskLevelChange }) {
  const isDefault = low === DEFAULT_THRESHOLDS.low && medium === DEFAULT_THRESHOLDS.medium;

  const toggleOverride = (level) => {
    onOverrideRiskLevelChange(overrideRiskLevel === level ? null : level);
  };
  const barRef = useRef(null);
  const dragging = useRef(null);
  const lowRef = useRef(low);
  const mediumRef = useRef(medium);
  const onChangeRef = useRef(onChange);
  lowRef.current = low;
  mediumRef.current = medium;
  onChangeRef.current = onChange;

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!dragging.current || !barRef.current) return;
      const rect = barRef.current.getBoundingClientRect();
      const rawVal = Math.round(((e.clientX - rect.left) / rect.width) * 130);
      if (dragging.current === 'low') {
        const v = Math.max(0, Math.min(rawVal, mediumRef.current));
        onChangeRef.current({ low: v, medium: mediumRef.current });
      } else {
        const v = Math.max(lowRef.current, Math.min(rawVal, 130));
        onChangeRef.current({ low: lowRef.current, medium: v });
      }
    };
    const handleMouseUp = () => {
      dragging.current = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const startDrag = (which) => (e) => {
    e.preventDefault();
    dragging.current = which;
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
  };

  const lowW  = (low / 130) * 100;
  const medW  = ((medium - low) / 130) * 100;
  const highW = ((130 - medium) / 130) * 100;

  return (
    <div className="risk-band-editor">

      {/* ── Visual bar ── */}
      <div className="risk-band-bar-wrap" dir="ltr" ref={barRef}>
        <div className="risk-band-bar">
          <div
            className={`risk-band-seg risk-band-seg--low${overrideRiskLevel === 'low' ? ' risk-band-seg--selected' : ''}`}
            style={{ width: `${lowW}%` }}
            onClick={() => toggleOverride('low')}
          >
            {lowW >= 12 && <span className="risk-band-seg-label">נמוך</span>}
          </div>
          <div
            className={`risk-band-seg risk-band-seg--medium${overrideRiskLevel === 'medium' ? ' risk-band-seg--selected' : ''}`}
            style={{ width: `${medW}%` }}
            onClick={() => toggleOverride('medium')}
          >
            {medW >= 12 && <span className="risk-band-seg-label">בינוני</span>}
          </div>
          <div
            className={`risk-band-seg risk-band-seg--high${overrideRiskLevel === 'high' ? ' risk-band-seg--selected' : ''}`}
            style={{ width: `${highW}%` }}
            onClick={() => toggleOverride('high')}
          >
            {highW >= 12 && <span className="risk-band-seg-label">גבוה</span>}
          </div>
        </div>
        {overrideRiskLevel && (
          <div className="risk-band-override-hint">
            השוואה לקבוצת סיכון {overrideRiskLevel === 'low' ? 'נמוך' : overrideRiskLevel === 'medium' ? 'בינוני' : 'גבוה'} — לחץ שוב לביטול
          </div>
        )}

        {/* Draggable threshold markers */}
        <div
          className="risk-band-marker risk-band-marker--draggable"
          style={{ left: `${(low / 130) * 100}%` }}
          onMouseDown={startDrag('low')}
        >
          <div className="risk-band-marker-handle" />
          <div className="risk-band-marker-line" />
          <div className="risk-band-marker-label">{low}%</div>
        </div>
        <div
          className="risk-band-marker risk-band-marker--draggable"
          style={{ left: `${(medium / 130) * 100}%` }}
          onMouseDown={startDrag('medium')}
        >
          <div className="risk-band-marker-handle" />
          <div className="risk-band-marker-line" />
          <div className="risk-band-marker-label">{medium}%</div>
        </div>
      </div>

      {/* ── Zone legend ── */}
      <div className="risk-band-legend">
        <div className="risk-band-legend-item">
          <span className="risk-band-dot risk-band-dot--low" />
          <span className="risk-band-legend-text">
            <strong>נמוך</strong> — 0%–{low}% חשיפה
          </span>
        </div>
        <div className="risk-band-legend-item">
          <span className="risk-band-dot risk-band-dot--medium" />
          <span className="risk-band-legend-text">
            <strong>בינוני</strong> — {low}%–{medium}% חשיפה
          </span>
        </div>
        <div className="risk-band-legend-item">
          <span className="risk-band-dot risk-band-dot--high" />
          <span className="risk-band-legend-text">
            <strong>גבוה</strong> — {medium}%–130% חשיפה
          </span>
        </div>
      </div>

      {!isDefault && (
        <button
          className="quick-action-btn quick-action-btn--reset"
          style={{ marginTop: '14px' }}
          onClick={() => onChange(DEFAULT_THRESHOLDS)}
        >
          ↺ איפוס לברירת מחדל (25% / 75%)
        </button>
      )}
    </div>
  );
}

// ─── Equity Geography Editor ──────────────────────────────────────────────────

const GEO_MIN_GAP = 5;

function geoSummary(geo) {
  if (!isGeoActive(geo)) return 'ללא העדפה — כל הקופות יוצעו, בלי קשר לפיזור המניות';
  return `ישראל ${geo.min}%–${geo.max}% ממרכיב המניות · חו״ל ${100 - geo.max}%–${100 - geo.min}%`;
}

function GeoFilterEditor({ geo, onChange }) {
  const barRef = useRef(null);
  const dragging = useRef(null);
  const geoRef = useRef(geo);
  const onChangeRef = useRef(onChange);
  geoRef.current = geo;
  onChangeRef.current = onChange;

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!dragging.current || !barRef.current) return;
      const rect = barRef.current.getBoundingClientRect();
      const raw = Math.round(((e.clientX - rect.left) / rect.width) * 100);
      const g = geoRef.current;
      if (dragging.current === 'min') {
        onChangeRef.current({ ...g, min: Math.max(0, Math.min(raw, g.max - GEO_MIN_GAP)) });
      } else {
        onChangeRef.current({ ...g, max: Math.min(100, Math.max(raw, g.min + GEO_MIN_GAP)) });
      }
    };
    const handleMouseUp = () => {
      dragging.current = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const startDrag = (which) => (e) => {
    e.preventDefault();
    dragging.current = which;
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
  };

  return (
    <div className="geo-editor">
      <div className="geo-presets">
        {GEO_PRESETS.map(p => (
          <button
            key={p.label}
            type="button"
            className={`leaderboard-filter-btn${geo.min === p.min && geo.max === p.max ? ' active' : ''}`}
            onClick={() => onChange({ min: p.min, max: p.max })}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="geo-bar-ends">
        <span><span className="geo-dot geo-dot--il" />100% ישראל</span>
        <span>100% חו״ל<span className="geo-dot geo-dot--abroad" /></span>
      </div>
      <div className="risk-band-bar-wrap" dir="ltr" ref={barRef}>
        <div className="risk-band-bar geo-bar">
          <div className="geo-bar-dim" style={{ left: 0, width: `${geo.min}%` }} />
          <div className="geo-bar-dim" style={{ left: `${geo.max}%`, width: `${100 - geo.max}%` }} />
        </div>
        {[{ id: 'min', pos: geo.min }, { id: 'max', pos: geo.max }].map(({ id, pos }) => (
          <div
            key={id}
            className="risk-band-marker risk-band-marker--draggable"
            style={{ left: `${pos}%` }}
            onMouseDown={startDrag(id)}
          >
            <div className="risk-band-marker-handle" />
            <div className="risk-band-marker-line" />
            <div className="risk-band-marker-label">{pos}%</div>
          </div>
        ))}
      </div>

      <div className={`geo-summary${isGeoActive(geo) ? ' geo-summary--active' : ''}`}>{geoSummary(geo)}</div>
      <div className="geo-hint">
        הסינון חל על הקופות המוצעות בלבד — הקופה הנוכחית שלך תמיד משתתפת בדירוג.
        מניות ישראל = חשיפה למניות − חשיפה לחו״ל (לפי גמל נט). בקופות משולבות החשיפה לחו״ל כוללת גם אג״ח,
        ולכן חלקן של מניות ישראל מוערך שם באופן שמרני.
      </div>
    </div>
  );
}

// Compact "Israel X% · abroad Y%" line for a fund's equity component
function GeoSplit({ fund, compact = false }) {
  const share = fund?.israel_equity_share;
  if (share == null) return compact ? null : <span className="geo-split geo-split--na">—</span>;
  const il = Math.round(share);
  return (
    <span className={`geo-split${compact ? ' geo-split--compact' : ''}`} title="פיזור מרכיב המניות: ישראל / חו״ל">
      <span className="geo-split-bar" dir="ltr">
        <span className="geo-split-il" style={{ width: `${il}%` }} />
      </span>
      <span>ישראל {il}% · חו״ל {100 - il}%</span>
    </span>
  );
}

// ─── Hevrot Checklist ─────────────────────────────────────────────────────────

function HevrotChecklist({ badHevrot, onChange }) {
  const allChecked = ALL_HEVROT.every(h => !badHevrot.has(h));
  const noneChecked = ALL_HEVROT.every(h => badHevrot.has(h));

  const toggle = (h) => {
    const next = new Set(badHevrot);
    if (next.has(h)) next.delete(h);
    else next.add(h);
    onChange(next);
  };

  const toggleAll = () => {
    if (allChecked) onChange(new Set(ALL_HEVROT));
    else onChange(new Set());
  };

  return (
    <div className="hevrot-checklist">
      <div className="hevrot-toggle-all">
        <label className="hevrot-item">
          <input
            type="checkbox"
            checked={allChecked}
            ref={el => { if (el) el.indeterminate = !allChecked && !noneChecked; }}
            onChange={toggleAll}
          />
          <span className="hevrot-name hevrot-name--all">בחר / בטל הכל</span>
        </label>
      </div>
      <div className="hevrot-grid">
        {ALL_HEVROT.map(h => (
          <label key={h} className="hevrot-item">
            <input
              type="checkbox"
              checked={!badHevrot.has(h)}
              onChange={() => toggle(h)}
            />
            <span className="hevrot-name">{h}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

// ─── Upload Screen ────────────────────────────────────────────────────────────

function UploadScreen({ mode, onModeChange, mislakaFiles, onMislakaFiles, onRemoveMislakaFile, bulkFiles, onBulkFiles, onRemoveBulkFile, onViewFile, weights, onWeightsChange, thresholds, onThresholdsChange, geo, onGeoChange, sumSameFund, onSumSameFundChange, badHevrot, onBadHevrotChange, overrideRiskLevel, onOverrideRiskLevelChange, onAnalyze, onBulkAnalyze }) {
  const isBulk = mode === 'bulk';
  const files = isBulk ? bulkFiles : mislakaFiles;
  const sum = sumWeights(weights);
  const hasFiles = files.length > 0;
  const ready = hasFiles && sum === 100;
  const isDefaultWeights = isSameWeights(weights, DEFAULT_WEIGHTS);
  const [hevrotOpen, setHevrotOpen] = useState(false);
  const [aggregateOpen, setAggregateOpen] = useState(false);
  const [geoOpen, setGeoOpen] = useState(false);

  return (
    <div className="screen screen--upload">

      <Header />
      <div className="upload-content">

        {/* ── Mode switch ── */}
        <div className="mode-switch" role="tablist">
          <button
            role="tab"
            aria-selected={!isBulk}
            className={`mode-switch-btn${!isBulk ? ' mode-switch-btn--active' : ''}`}
            onClick={() => onModeChange('single')}
          >
            👤 לקוח בודד
          </button>
          <button
            role="tab"
            aria-selected={isBulk}
            className={`mode-switch-btn${isBulk ? ' mode-switch-btn--active' : ''}`}
            onClick={() => onModeChange('bulk')}
          >
            👥 ניתוח מרובה לקוחות
          </button>
        </div>

        {/* ── Hero ── */}
        {isBulk ? (
          <div className="hero">
            <div className="hero-badge">ניתוח תיק לקוחות · AmoSight</div>
            <h1 className="hero-title">מי מהלקוחות שלך<br/>צריך ניוד בדחיפות?</h1>
            <p className="hero-sub">
              העלה בבת אחת את קבצי המסלקה של כל הלקוחות — הקבצים יקובצו אוטומטית לפי תעודת זהות,
              וכל לקוח יקבל ציון תיק משוקלל וסכום הכסף שהיה מרוויח מניוד
            </p>
          </div>
        ) : (
          <div className="hero">
            <div className="hero-badge">השוואת קופות גמל · AmoSight</div>
            <h1 className="hero-title">בדוק את הביצועים<br/>של הקופות שלך</h1>
            <p className="hero-sub">
              העלה קבצים או תיקייה מהמסלקה הפנסיונית וגלה תוך שניות<br/>היכן הקופות שלך עומדת מול שוק הגמל
            </p>
          </div>
        )}

        {/* ── Feature strip ── */}
        {!isBulk && (
          <div className="feature-strip">
            <div className="feature-item">
              <div className="feature-text">
                <div className="feature-title">📊 השוואה מול השוק</div>
                <div className="feature-desc">דירוג מול כל הקופות ברמת הסיכון שלך</div>
              </div>
            </div>
            <div className="feature-divider" />
            <div className="feature-item">
              <div className="feature-text">
                <div className="feature-title">🏅 3 החלופות הטובות</div>
                <div className="feature-desc">קופות עם ציון גבוה יותר</div>
              </div>
            </div>
            <div className="feature-divider" />
            <div className="feature-item">
              <div className="feature-text">
                <div className="feature-title">💰 מה החמצת?</div>
                <div className="feature-desc">הפוטנציאל שאבדת ואיך לשחזר אותו</div>
              </div>
            </div>
          </div>
        )}

        {/* ── Step 1: Upload ── */}
        <div className="upload-step-card">
          <div className="step-card-header">
            <div className="step-card-num">01</div>
            <div className="step-card-label">{isBulk ? 'העלאת קבצי מסלקה של כל הלקוחות' : 'העלאת קבצי מסלקה'}</div>
            {hasFiles && (
              <button className="quick-action-btn quick-action-btn--clear" onClick={() => (isBulk ? onBulkFiles : onMislakaFiles)([])}>
                נקה הכל
              </button>
            )}
          </div>
          <div className="upload-row">
            {isBulk ? (
              <MultiUploadZone
                key="bulk"
                files={bulkFiles}
                onFiles={onBulkFiles}
                onRemoveFile={onRemoveBulkFile}
                onViewFile={onViewFile}
                label="קבצי מסלקה של לקוחות רבים"
                hint="בחר קבצים או תיקייה שלמה — אפשר אלפי קבצים. קבצים של אותו לקוח יאוחדו לפי ת״ז"
                compact
              />
            ) : (
              <MultiUploadZone
                key="single"
                files={mislakaFiles}
                onFiles={onMislakaFiles}
                onRemoveFile={onRemoveMislakaFile}
                onViewFile={onViewFile}
              />
            )}
          </div>
        </div>

        {/* ── Step 2: Weights ── */}
        <div className="upload-step-card">
          <div className="step-card-header">
            <div className="step-card-num">02</div>
            <div className="step-card-label">כיוון משקלות AmoScore</div>
            {!isDefaultWeights && (
              <button className="quick-action-btn quick-action-btn--reset" onClick={() => onWeightsChange(DEFAULT_WEIGHTS)}>
                ↺ איפוס
              </button>
            )}
          </div>
          <WeightsForm weights={weights} onChange={onWeightsChange} />
        </div>

        {/* ── Step 3: Risk Thresholds ── */}
        <div className="upload-step-card">
          <div className="step-card-header">
            <div className="step-card-num">03</div>
            <div className="step-card-label">הגדרת סף רמות סיכון</div>
          </div>
          <RiskBandEditor
            low={thresholds.low}
            medium={thresholds.medium}
            onChange={onThresholdsChange}
            overrideRiskLevel={overrideRiskLevel}
            onOverrideRiskLevelChange={onOverrideRiskLevelChange}
          />
        </div>

        {/* ── Step 4: Equity geography ── */}
        <div className="upload-step-card">
          <div className="step-card-header" style={{ cursor: 'pointer' }} onClick={() => setGeoOpen(o => !o)}>
            <div className="step-card-num">04</div>
            <div className="step-card-label">
              מניות ישראל / חו״ל
              {!geoOpen && isGeoActive(geo) && <span className="step-card-chip">{geoSummary(geo)}</span>}
            </div>
            <span style={{ marginRight: 'auto', marginLeft: '8px', fontSize: '12px', color: 'var(--text-muted, #888)' }}>
              {geoOpen ? '▲ סגור' : '▼ פתח'}
            </span>
            {isGeoActive(geo) && (
              <button className="quick-action-btn quick-action-btn--reset" onClick={e => { e.stopPropagation(); onGeoChange(DEFAULT_GEO); }}>
                ↺ איפוס
              </button>
            )}
          </div>
          {geoOpen && <GeoFilterEditor geo={geo} onChange={onGeoChange} />}
        </div>

        {/* ── Step 5: Aggregate ── */}
        <div className="upload-step-card">
          <div className="step-card-header" style={{ cursor: 'pointer' }} onClick={() => setAggregateOpen(o => !o)}>
            <div className="step-card-num">05</div>
            <div className="step-card-label">איחוד קופות זהות</div>
            <span style={{ marginRight: 'auto', marginLeft: '8px', fontSize: '12px', color: 'var(--text-muted, #888)' }}>
              {aggregateOpen ? '▲ סגור' : '▼ פתח'}
            </span>
          </div>
          {aggregateOpen && (
            <div className="aggregate-toggle-row">
              <div className="aggregate-toggle-info">
                <div className="aggregate-toggle-title">סכום מופעים של אותה קופה</div>
                <div className="aggregate-toggle-desc">
                  {sumSameFund
                    ? 'מופעים מרובים של אותה קופה (לפי מספר קופה) יאוחדו וסכום הצבירות יסוכם'
                    : 'כל מופע של קופה יוצג בנפרד, גם אם מספר הקופה זהה'}
                </div>
              </div>
              <label className="fund-toggle">
                <input
                  type="checkbox"
                  checked={sumSameFund}
                  onChange={e => onSumSameFundChange(e.target.checked)}
                />
                <span className="fund-toggle-slider" />
              </label>
            </div>
          )}
        </div>

        {/* ── Step 6: Hevrot ── */}
        <div className="upload-step-card">
          <div className="step-card-header" style={{ cursor: 'pointer' }} onClick={() => setHevrotOpen(o => !o)}>
            <div className="step-card-num">06</div>
            <div className="step-card-label">בחירת חברות מנהלות</div>
            <span style={{ marginRight: 'auto', marginLeft: '8px', fontSize: '12px', color: 'var(--text-muted, #888)' }}>
              {hevrotOpen ? '▲ סגור' : '▼ פתח'}
            </span>
            {hevrotOpen && (
              <button className="quick-action-btn quick-action-btn--reset" onClick={e => { e.stopPropagation(); onBadHevrotChange(new Set(DEFAULT_BAD_HEVROT)); }}>
                ↺ איפוס
              </button>
            )}
          </div>
          {hevrotOpen && <HevrotChecklist badHevrot={badHevrot} onChange={onBadHevrotChange} />}
        </div>

        {/* ── Analyze ── */}
        <div className="analyze-wrap">
          <button
            className={`btn-analyze${ready ? ' btn-analyze--active' : ''}`}
            disabled={!ready}
            onClick={isBulk ? onBulkAnalyze : onAnalyze}
          >
            {isBulk ? 'נתח את כל הלקוחות' : 'הפעל ניתוח'}
          </button>
          <div className="analyze-status">
            {!hasFiles && <span className="analyze-status-item">· העלה לפחות קובץ אחד</span>}
            {hasFiles && sum !== 100 && <span className="analyze-status-item">· המשקלות צריכים להסתכם ל-100% (כרגע {sum}%)</span>}
            {ready && <span className="analyze-status-item analyze-status-ready">· מוכן לניתוח{isBulk ? ` של ${files.length.toLocaleString('he-IL')} קבצים` : ''}</span>}
          </div>
        </div>

      </div>
    </div>
  );
}

// ─── Loading Screen ───────────────────────────────────────────────────────────

function LoadingScreen({ step, progress, title = 'מנתח את הנתונים...' }) {
  return (
    <div className="screen screen--loading">

      <Header />
      <div className="loading-content">
        <div className="loading-emoji">📊</div>
        <h2 className="loading-title">{title}</h2>
        <p className="loading-sub">{LOADING_STEPS[Math.min(step, LOADING_STEPS.length - 1)]}</p>
        <div className="progress-wrap">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="progress-pct">{progress}%</div>
      </div>
    </div>
  );
}

// ─── Fee Mode Toggle ──────────────────────────────────────────────────────────

function FeeModeToggle({ feeMode, onChange, compact = false }) {
  const buttons = (
    <div className="fee-toggle-buttons" role="group" aria-label="דמי ניהול בקופות החלופיות">
      {FEE_MODES.map(m => (
        <button
          key={m.key}
          type="button"
          aria-pressed={feeMode === m.key}
          className={`leaderboard-filter-btn${feeMode === m.key ? ' active' : ''}`}
          onClick={() => onChange(m.key)}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
  if (compact) return buttons;
  return (
    <div className="fee-toggle">
      <div className="fee-toggle-text">
        <div className="fee-toggle-title">💸 דמי ניהול בקופות החלופיות</div>
        <div className="fee-toggle-desc">
          {feeMode === 'net'
            ? 'תשואות החלופות מחושבות בניכוי אותם דמי ניהול שאתה משלם היום'
            : 'תשואות החלופות מוצגות ברוטו — כאילו תעבור ללא דמי ניהול'}
          {' · '}הקופה הנוכחית שלך מחושבת תמיד בניכוי דמי הניהול שלך
        </div>
      </div>
      {buttons}
    </div>
  );
}

// ─── Portfolio Score ──────────────────────────────────────────────────────────

function ScoreRing({ score, size = 132 }) {
  const r = size / 2 - 10;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(score ?? 0, 100)) / 100;
  const color = scoreColor(score);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="score-ring">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth="10" />
      {score != null && (
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={`${c * pct} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      )}
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" fill="var(--text-primary)"
        fontSize={size * 0.26} fontWeight="800" fontFamily="Rubik, sans-serif">
        {score != null ? fmtDec(score) : '–'}
      </text>
    </svg>
  );
}

function PortfolioScoreCard({ portfolio, results }) {
  if (!portfolio || !results?.length) return null;
  const score = portfolio.weighted_score;
  const potential = portfolio.potential_score;
  const total = results.reduce((s, f) => s + (f.client.amount ?? 0), 0);
  const holdings = [...results].sort((a, b) => (b.client.amount ?? 0) - (a.client.amount ?? 0));
  const uncovered = 100 - (portfolio.coverage ?? 0);

  return (
    <div className="portfolio-card">
      <div className="portfolio-card-title">🎯 הציון המשוקלל של התיק</div>
      <div className="portfolio-card-body">
        <div className="portfolio-card-score">
          <ScoreRing score={score} />
          <div className="portfolio-card-verdict" style={{ color: scoreColor(score) }}>{scoreVerdict(score)}</div>
        </div>
        <div className="portfolio-card-details">
          <p>
            ממוצע ה-AmoScore של הקופות שלך, כשכל קופה נספרת לפי החלק של הכסף שלך שנמצא בה —
            קופה שמחזיקה 70% מהצבירה משפיעה על הציון פי כמה מקופה קטנה.
          </p>
          {potential != null && score != null && potential > score && (
            <div className="portfolio-card-potential">
              <span>אם תעבור לחלופה המובילה בכל קופה:</span>
              <strong style={{ color: scoreColor(potential) }}>{fmtDec(score)} ← {fmtDec(potential)}</strong>
            </div>
          )}
          {portfolio.weighted_percentile != null && (
            <div className="portfolio-card-note">
              בממוצע משוקלל, הכסף שלך נמצא באחוזון {Math.round(portfolio.weighted_percentile)} ביחס לקופות המקבילות
            </div>
          )}
          {uncovered > 0.05 && (
            <div className="portfolio-card-note portfolio-card-note--warn">
              {fmtDec(uncovered)}% מהצבירה נמצאים בקופות ללא מספיק נתונים לדירוג (למשל קופה חדשה) — הם לא נכללו בציון
            </div>
          )}
        </div>
      </div>

      <div className="portfolio-alloc-bar" dir="ltr">
        {holdings.map((f, i) => (
          <div
            key={`${f.client.id}-${i}`}
            className="portfolio-alloc-seg"
            style={{ width: `${total > 0 ? (f.client.amount / total) * 100 : 0}%`, background: scoreColor(gradeOrNull(f.client)) }}
            title={`${f.client.name}: ${fmtDec(total > 0 ? f.client.amount / total * 100 : 0)}% · AmoScore ${gradeText(f.client)}`}
          />
        ))}
      </div>
      <div className="portfolio-alloc-legend">
        {holdings.map((f, i) => (
          <div key={`${f.client.id}-${i}`} className="portfolio-alloc-item">
            <span className="portfolio-alloc-dot" style={{ background: scoreColor(gradeOrNull(f.client)) }} />
            <span className="portfolio-alloc-name">{f.client.name}</span>
            <span className="portfolio-alloc-share">{fmtDec(total > 0 ? f.client.amount / total * 100 : 0)}% מהכסף</span>
            <span className="portfolio-alloc-score" style={{ color: scoreColor(gradeOrNull(f.client)) }}>
              {gradeText(f.client)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Fund Results Section ─────────────────────────────────────────────────────

function FundResults({ data, weights, thresholds, feeMode = 'net', onFeeModeChange }) {
  const { client, alternatives, golden: gold } = data;
  const isNew = !hasGrade(client);
  const [returnPeriod, setReturnPeriod] = useState(1);
  const [periodPickerOpen, setPeriodPickerOpen] = useState(false);

  const pct = client.percentile ?? 0;
  const isBelow = !isNew && pct < 50;

  // Bar chart: proportional to selected period's tsua
  const clientTsua = (returnPeriod === 1 ? client.tsua_1 : returnPeriod === 3 ? client.tsua_3 : client.tsua_5) ?? 0;
  const allTsua = [clientTsua, ...alternatives.map(a => (returnPeriod === 1 ? a.tsua_1 : returnPeriod === 3 ? a.tsua_3 : a.tsua_5) ?? 0)].filter(v => v > 0);
  const maxTsua = Math.max(...allTsua, 0.1);
  const periodLabel = returnPeriod === 1 ? 'שנתית' : returnPeriod === 3 ? '3 שנים' : '5 שנים';

  // Best alternative for high-risk section
  const bestAlt = alternatives[0];
  const diffPct = bestAlt?.diff_percent ?? 0;

  // Risk display
  const riskLabel = RISK_LABELS[client.risk_level] ?? client.risk_level ?? '—';
  const riskColor = RISK_COLORS[client.risk_level] ?? '#94A3B8';
  const riskExposure = getRiskExposure(thresholds ?? DEFAULT_THRESHOLDS);

  // Merge client + alternatives, sort by AmoScore descending
  const clientEntry = {
    ...client,
    isClient: true,
    // For the client's own row the "potential" is always their current balance —
    // they were already in this fund, so the realized amount equals client.amount
    // for every horizon. diff is 0 (no gain vs staying put).
    potential_amount:   client.amount,
    potential_amount_3: client.amount,
    potential_amount_5: client.amount,
    diff: 0, diff_percent: 0,
    diff_3: 0, diff_percent_3: 0,
    diff_5: 0, diff_percent_5: 0,
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

  const topRankColors = ['#F59E0B', '#94A3B8', '#C084FC'];
  const topRankBg = ['rgba(245,158,11,0.15)', 'rgba(148,163,184,0.15)', 'rgba(192,132,252,0.15)'];

  return (
    <div className="fund-results fade-in fund-section">

      {/* 1 ─ Client Header Card */}
      <div className="client-card">
        <div className="client-card-accent" style={{ background: riskColor }} />
        <div className="client-card-info">
          <div className="client-card-pills">
            <span
              className="risk-pill"
              style={{ background: `${riskColor}22`, color: riskColor, borderColor: `${riskColor}55` }}
              title={riskExposure[client.risk_level]}
            >
              ● רמת סיכון {riskLabel}
              {client.risk_level && (
                <span style={{ fontSize: '10px', opacity: 0.8, marginRight: '6px', fontWeight: 400 }}>
                  ({riskExposure[client.risk_level]})
                </span>
              )}
            </span>
            {!isNew && client.rank != null && (
              <span className={`rank-pill ${clientIsTop ? 'rank-pill--good' : 'rank-pill--bad'}`}>
                מקום {client.rank} מתוך {client.total_in_risk}
              </span>
            )}
          </div>
          <div className="client-fund-name">{client.name}</div>
          <div className="client-fund-meta">
            קופה #{client.id}
            {client.hevra && <> · {client.hevra}</>}
            {client.seniority_date && <> · ותק מ-{formatDate(client.seniority_date)}</>}
          </div>
          <div className="client-stats-inline">
            <div className="client-stat-item">
              <div className="client-stat-label">צבירה</div>
              <div className="client-stat-val">₪{fmt(client.amount)}</div>
            </div>
            <div className="client-stat-sep" />
            <div className="client-stat-item">
              <div className="client-stat-label">תשואה שנה</div>
              <div className="client-stat-val client-stat-val--amber">
                {client.tsua_1 ? `${fmtDec(client.tsua_1)}%` : 'N/A'}
              </div>
            </div>
            <div className="client-stat-sep" />
            <div className="client-stat-item">
              <div className="client-stat-label">תשואה 3 שנים</div>
              <div className="client-stat-val">
                {isNew || !client.tsua_3 ? 'N/A' : `${fmtDec(client.tsua_3)}%`}
              </div>
            </div>
            <div className="client-stat-sep" />
            <div className="client-stat-item">
              <div className="client-stat-label">דמי ניהול</div>
              <div className="client-stat-val">
                {client.dmei_nihul != null ? `${fmtDec(client.dmei_nihul, 2)}%` : '—'}
              </div>
            </div>
          </div>
          <div className="client-profile-line">
            {client.equity_exposure != null && (
              <span className="client-profile-item">
                <span className="client-profile-label">מניות {fmtDec(client.equity_exposure)}%:</span>
                <GeoSplit fund={client} />
              </span>
            )}
            {client.liquidity_index != null && (
              <span
                className="client-profile-item"
                title="צבירה נטו (הפקדות והעברות פנימה פחות משיכות והעברות החוצה) ב-12 החודשים האחרונים, ביחס לנכסי הקופה"
              >
                <span className="client-profile-label">צבירה נטו 12 ח׳:</span>
                <strong style={{ color: client.liquidity_index >= 0 ? '#10B981' : '#EF4444' }}>
                  {client.liquidity_index > 0 ? '+' : ''}{fmtDec(client.liquidity_index)}%
                </strong>
                {client.liquidity_score != null && (
                  <span className="client-profile-label">(מדד נזילות {Math.round(client.liquidity_score)} מתוך 100)</span>
                )}
              </span>
            )}
          </div>
        </div>
        <div className="client-score-wrap">
          <div className="gauge-amoscore-label">AmoScore</div>
          <div className="gauge-amoscore-value" style={{ color: isNew ? '#64748B' : '#F8FAFC' }}>
            {gradeText(client)}
          </div>
          <GaugeChart percentile={pct} rank={client.rank} total={client.total_in_risk} />
          <div className={`client-verdict ${isNew ? 'verdict--new' : isBelow ? 'verdict--bad' : 'verdict--good'}`}>
            {isNew ? 'קופה חדשה — מעט נתונים' : isBelow ? '⚠ מתחת לממוצע' : '✓ מעל הממוצע'}
          </div>
        </div>
      </div>

      {/* 2 ─ Bar Chart */}
      <div className="chart-card">
        <div className="chart-header">
          <div>
            <div className="chart-title">תשואה {periodLabel} — השוואה לשוק</div>
            <div className="chart-sub">{client.total_in_risk ?? '–'} קופות ברמת סיכון {riskLabel}</div>
          </div>
        </div>
        <div className="chart-bars">
          <div className="bar-row bar-row--client">
            <div className="bar-label bar-label--client">
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', direction: 'rtl' }}>
                {client.rank != null && (
                  <span style={{ fontWeight: 700, fontSize: '12px', color: clientIsTop ? '#F59E0B' : '#6B7280' }}>#{client.rank}</span>
                )}
                <span>{shortName(client.name)}</span>
              </div>
              <span className="bar-client-tag">הקופה שלך</span>
            </div>
            <div className="bar-track bar-track--client">
              <div
                className={`bar-fill ${clientIsTop ? 'bar-fill--client' : 'bar-fill--red'}`}
                style={{ width: clientTsua > 0 ? `${(clientTsua / maxTsua) * 100}%` : '5%' }}
              >
                <span className="bar-pct">{clientTsua > 0 ? `${fmtDec(clientTsua)}%` : '—'}</span>
              </div>
            </div>
          </div>
          {alternatives.map((alt, i) => {
            const tsua = (returnPeriod === 1 ? alt.tsua_1 : returnPeriod === 3 ? alt.tsua_3 : alt.tsua_5) ?? 0;
            const altRank = sortedFunds.findIndex(f => f.id === alt.id) + 1;
            const rankColorIdx = altRank - 1;
            return (
              <div key={alt.id} className="bar-row">
                <div className="bar-label">
                  <span style={{ marginLeft: '4px', display: 'inline-block', minWidth: '22px', textAlign: 'center', fontWeight: 700, fontSize: '12px', color: topRankColors[rankColorIdx] ?? '#6B7280' }}>#{altRank}</span>
                  {shortName(alt.name)}
                </div>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{ width: `${Math.max((tsua / maxTsua) * 100, 2)}%`, background: ALT_GRADIENTS[i] || ALT_COLORS[i] }}
                  >
                    <span className="bar-pct">{fmtDec(tsua)}%</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3 ─ Leaderboard Table */}
      <div className="table-card">
        <div className="table-header-row">
          <div>
            <div className="table-title">טבלת דירוג — AmoScore</div>
            <div className="table-title-sub">
              {feeMode === 'gross'
                ? 'תשואות החלופות ברוטו, ללא דמי ניהול · הקופה שלך בניכוי דמי הניהול שלך'
                : `כל התשואות בניכוי דמי הניהול שלך (${client.dmei_nihul != null ? fmtDec(client.dmei_nihul, 2) : '—'}%)`}
            </div>
          </div>
          {onFeeModeChange && <FeeModeToggle feeMode={feeMode} onChange={onFeeModeChange} compact />}
        </div>
        <div className="table-wrap">
          <table className="alts-table">
            <thead>
              <tr>
                <th>#</th>
                <th>שם הקופה</th>
                <th style={{ position: 'relative' }}>
                  <button className="period-picker-btn" onClick={() => setPeriodPickerOpen(o => !o)}>
                    {returnPeriod === 1 ? 'תשואה שנתית' : returnPeriod === 3 ? 'תשואה 3 שנים' : 'תשואה 5 שנים'}
                    <span className="period-picker-arrow">{periodPickerOpen ? '▲' : '▼'}</span>
                  </button>
                  {periodPickerOpen && (
                    <div className="period-picker-dropdown">
                      {[1, 3, 5].map(p => (
                        <button
                          key={p}
                          className={`period-picker-option${returnPeriod === p ? ' period-picker-option--active' : ''}`}
                          onClick={() => { setReturnPeriod(p); setPeriodPickerOpen(false); }}
                        >
                          {p === 1 ? 'שנה אחרונה' : `${p} שנים`}
                        </button>
                      ))}
                    </div>
                  )}
                </th>
                <th>AmoScore</th>
                <th>פוטנציאל *</th>
                <th>הפרש</th>
              </tr>
            </thead>
            <tbody>
              {sortedFunds.map((fund, idx) => {
                const color = fundColors[idx];
                const potentialAmt = returnPeriod === 1 ? fund.potential_amount : returnPeriod === 3 ? fund.potential_amount_3 : fund.potential_amount_5;
                const diffAmt      = returnPeriod === 1 ? fund.diff            : returnPeriod === 3 ? fund.diff_3            : fund.diff_5;
                const diffPct      = returnPeriod === 1 ? fund.diff_percent    : returnPeriod === 3 ? fund.diff_percent_3    : fund.diff_percent_5;
                const diffNeg = diffAmt != null && diffAmt < 0;
                const isTopThree = !fund.isClient && idx < 3;
                return (
                  <tr key={fund.id} className={fund.isClient ? (clientIsTop ? 'row-client' : 'row-client row-client--bad') : 'row-alt'}>
                    <td>
                      <span className="rank-badge" style={{
                        background: isTopThree ? topRankBg[idx] : `${color}33`,
                        color: isTopThree ? topRankColors[idx] : color,
                        fontWeight: isTopThree ? 700 : 600,
                      }}>
                        {fund.isClient ? (fund.rank ?? '–') : idx + 1}
                      </span>
                    </td>
                    <td className="td-name">
                      <div>{fund.name}</div>
                      {fund.hevra && <div className="td-name-sub">{fund.hevra}</div>}
                      <div className="td-name-sub">קופה #{fund.id}</div>
                      <GeoSplit fund={fund} compact />
                      {fund.isClient && (
                        <div className={`td-name-tag ${clientIsTop ? 'td-name-tag--client' : 'td-name-tag--client-bad'}`}>הקופה שלך</div>
                      )}
                    </td>
                    <td className="td-return" style={{ color }}>
                      {(() => { const v = returnPeriod === 1 ? fund.tsua_1 : returnPeriod === 3 ? fund.tsua_3 : fund.tsua_5; return v != null && v !== 0 ? `${fmtDec(v)}%` : 'N/A'; })()}
                    </td>
                    <td className="td-score">{gradeText(fund)}</td>
                    <td className="td-potential">{potentialAmt != null ? `₪${fmt(potentialAmt)}` : '—'}</td>
                    <td className="td-diff">
                      {!fund.isClient && diffAmt != null ? (
                        <div>
                          <span className="diff-badge" style={{ background: diffNeg ? 'rgba(239,68,68,0.15)' : undefined, color: diffNeg ? '#EF4444' : undefined }}>
                            {diffNeg ? '' : '+'}₪{fmt(Math.abs(diffAmt))}
                          </span>
                          {diffPct != null && (
                            <div className="diff-pct" style={{ color: diffNeg ? '#EF4444' : '#10B981' }}>
                              {diffNeg ? '' : '+'}{fmtDec(diffPct)}%
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
          * לא נוכו דמי ניהול חיצוניים מהחישוב · רמת הסיכון נקבעת לפי חשיפה למניות בחודש האחרון
          {' · '}ה-AmoScore והדירוג אינם תלויים בבחירת דמי הניהול — הם משווים את כל הקופות באותם תנאים
        </div>
      </div>

      {/* 6 ─ High-risk option box + Gold card */}
      <div className="bottom-cards-row">
        {bestAlt && (client.rank !== 1 || (gold && gold.potential_amount > client.amount)) && (bestAlt.potential_amount > client.amount) && (
          <div className="highrisk-card">
            <div className="highrisk-body">
              <div className="highrisk-title">⚡ מה החמצת?</div>
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

        {gold && gold.potential_amount != null && gold.potential_amount > client.amount && (
          <div className="gold-card">
            <div className="gold-body">
              <div className="gold-title">🏆🍎 תפוח הזהב</div>
              <div className="gold-subtitle">מקום #1 ברמת סיכון גבוה</div>
              <div className="gold-desc">
                אם היית עובר לקופה המובילה בסיכון הגבוה ביותר, הצבירה שלך הייתה גדלה ב-
                <strong> {fmtDec(gold.diff_percent)}%</strong>
              </div>
              <div className="gold-amounts">
                <div className="gold-amount-item">
                  <div className="gold-amount-label">היום</div>
                  <div className="gold-amount-val">₪{fmt(client.amount)}</div>
                </div>
                <div className="gold-arrow">←</div>
                <div className="gold-amount-item">
                  <div className="gold-amount-label">פוטנציאל</div>
                  <div className="gold-amount-val gold-amount-val--gold">₪{fmt(gold.potential_amount)}</div>
                  {gold.tsua_1 && <div className="gold-amount-sub">{fmtDec(gold.tsua_1)}% תשואה</div>}
                </div>
              </div>
              {gold.name && <div className="gold-fund-name">קופה: {gold.name}{gold.id && <span className="gold-fund-id"> · #{gold.id}</span>}</div>}
            </div>
          </div>
        )}
      </div>

      {/* 7 ─ Disclaimer */}
      <div className="disclaimer">
        הנתונים מבוססים על מידע מהמסלקה הפנסיונית ומגמל נט של רשות שוק ההון · אין לראות בכך ייעוץ השקעות
      </div>
    </div>
  );
}

// ─── PDF Generator ────────────────────────────────────────────────────────────

// Colors matching the app
const PDF_BLUE   = '#3B82F6';
const PDF_PURPLE = '#8B5CF6';
const PDF_DARK   = '#0F172A';
const PDF_TEXT   = '#1E293B';
const PDF_MUTED  = '#64748B';


function pdfHeader(today) {
  return `
    <div style="display:flex;align-items:center;justify-content:space-between;
      margin-bottom:24px;padding-bottom:16px;
      border-bottom:2px solid ${PDF_BLUE};">
      <div style="display:flex;align-items:center;gap:12px;">
        <svg width="30" height="38" viewBox="-3 -3 36 44" fill="none">
          <defs>
            <linearGradient id="pdfLg" x1="15" y1="0" x2="15" y2="38" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stop-color="#A78BFA"/>
              <stop offset="100%" stop-color="${PDF_BLUE}"/>
            </linearGradient>
          </defs>
          <line x1="15" y1="2" x2="1" y2="34" stroke="url(#pdfLg)" stroke-width="4" stroke-linecap="round"/>
          <line x1="15" y1="2" x2="29" y2="34" stroke="url(#pdfLg)" stroke-width="4" stroke-linecap="round"/>
          <line x1="7" y1="21" x2="23" y2="21" stroke="url(#pdfLg)" stroke-width="3.5" stroke-linecap="round"/>
          <circle cx="15" cy="2" r="4" fill="#A78BFA"/>
        </svg>
        <div>
          <div style="font-size:22px;font-weight:800;letter-spacing:-0.01em;line-height:1.15;">
            <span style="color:${PDF_DARK};">Amo</span><span style="color:${PDF_BLUE};">Sight</span>
          </div>
          <div style="font-size:11px;color:${PDF_MUTED};">ניתוח והשוואת קופות גמל</div>
        </div>
      </div>
      <div style="text-align:left;color:${PDF_MUTED};font-size:11px;line-height:1.6;">
        <div>דוח הופק: ${today}</div>
        <div>AmoSight Report</div>
      </div>
    </div>`;
}

function pdfFooter(pageNum, total) {
  return `
    <div style="margin-top:24px;padding-top:12px;border-top:1px solid #E2E8F0;
      display:flex;justify-content:space-between;align-items:center;">
      <div style="font-size:10px;color:${PDF_MUTED};">
        הנתונים מבוססים על מידע מהמסלקה הפנסיונית ומגמל נט · אין לראות בכך ייעוץ השקעות
      </div>
      <div style="font-size:10px;color:${PDF_MUTED};">עמוד ${pageNum} מתוך ${total}</div>
    </div>`;
}

async function generatePDF(funds, weights, { feeMode = 'net', portfolio = null } = {}) {
  const today = new Date().toLocaleDateString('he-IL');
  const portfolioScore = portfolio?.weighted_score;
  const feeNote = feeMode === 'gross'
    ? 'תשואות החלופות מוצגות ברוטו, ללא דמי ניהול · הקופה הנוכחית בניכוי דמי הניהול של הלקוח'
    : 'כל התשואות מוצגות בניכוי דמי הניהול שהלקוח משלם היום';
  const totalPages = 1 + funds.length;

  // ── Summary totals (same logic as SummaryHero) ───────────────────────────────
  const totalCurrent   = funds.reduce((s, f) => s + (f.client.amount ?? 0), 0);
  const totalPotential = funds.reduce((s, f) => s + getPotentialAmount(f), 0);
  const totalDiff      = totalPotential - totalCurrent;
  const totalDiffPct   = totalCurrent > 0 ? (totalDiff / totalCurrent) * 100 : 0;
  const hasUpside      = totalDiff > 0;

  // ── Page 1: Cover ────────────────────────────────────────────────────────────
  const coverHTML = `
    ${pdfHeader(today)}
    <div style="margin-bottom:18px;">
      <div style="font-size:18px;font-weight:800;color:${PDF_DARK};margin-bottom:4px;">דוח השוואת קופות גמל</div>
      <div style="font-size:13px;color:${PDF_MUTED};">${funds.length} קופ${funds.length === 1 ? 'ה' : 'ות'} נותחו בדוח זה</div>
    </div>

    ${hasUpside ? `
    <div style="background:#ffffff;border:1.5px solid rgba(234,179,8,0.5);
      border-radius:16px;padding:24px 28px;margin-bottom:18px;text-align:center;direction:rtl;">
      <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#B45309;margin-bottom:18px;">💎 סיכום כלל הקופות</div>
      <div style="display:flex;align-items:center;justify-content:center;gap:28px;flex-wrap:wrap;">
        <div style="text-align:center;">
          <div style="font-size:10px;color:#78716C;margin-bottom:5px;letter-spacing:0.04em;">צבירה נוכחית</div>
          <div style="font-size:32px;font-weight:900;color:#F87171;">₪${fmt(totalCurrent)}</div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:22px;color:#D97706;">←</div>
          <div style="background:rgba(234,179,8,0.12);border:1px solid rgba(234,179,8,0.45);
            color:#B45309;font-size:12px;font-weight:800;padding:4px 12px;border-radius:999px;margin-top:4px;">
            +₪${fmt(totalDiff)} (${fmtDec(totalDiffPct)}%)
          </div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:10px;color:#78716C;margin-bottom:5px;letter-spacing:0.04em;">פוטנציאל אם תעבור עכשיו</div>
          <div style="font-size:32px;font-weight:900;color:#D97706;">₪${fmt(totalPotential)}</div>
        </div>
      </div>
      <div style="margin-top:14px;font-size:11px;color:#92400E;border-top:1px solid rgba(234,179,8,0.2);padding-top:10px;">
        השנה החמצת <strong style="color:#B45309;">₪${fmt(totalDiff)}</strong> — עדיין לא מאוחר לעבור
      </div>
    </div>` : ''}

    ${portfolioScore != null ? `
    <div style="background:#F8FAFF;border:1px solid #DBEAFE;border-radius:12px;padding:18px 22px;margin-bottom:16px;
      display:flex;align-items:center;gap:22px;">
      <div style="text-align:center;min-width:110px;">
        <div style="font-size:10px;color:${PDF_MUTED};margin-bottom:4px;">ציון תיק משוקלל</div>
        <div style="font-size:38px;font-weight:900;color:${scoreColor(portfolioScore)};line-height:1;">${fmtDec(portfolioScore)}</div>
        <div style="font-size:11px;font-weight:700;color:${scoreColor(portfolioScore)};margin-top:4px;">${scoreVerdict(portfolioScore)}</div>
      </div>
      <div style="font-size:11px;color:${PDF_MUTED};line-height:1.7;">
        ממוצע ה-AmoScore של כל הקופות, משוקלל לפי החלק של הכסף בכל קופה.
        ${portfolio.potential_score != null && portfolio.potential_score > portfolioScore
          ? `<br/>אם כל קופה תעבור לחלופה המובילה: <strong style="color:${PDF_TEXT};">${fmtDec(portfolioScore)} ← ${fmtDec(portfolio.potential_score)}</strong>` : ''}
        ${portfolio.coverage < 99.95 ? `<br/>${fmtDec(100 - portfolio.coverage)}% מהצבירה בקופות ללא מספיק נתונים לדירוג — לא נכללו בציון.` : ''}
      </div>
    </div>` : ''}

    <div style="background:#F8FAFF;border:1px solid #DBEAFE;border-radius:12px;padding:18px 22px;margin-bottom:16px;">
      <div style="font-size:12px;font-weight:700;color:${PDF_BLUE};margin-bottom:12px;">פרמטרי החישוב — AmoScore</div>
      <div style="display:flex;gap:10px;">
        ${WEIGHT_SEGMENTS.map(seg => `
          <div style="flex:1;text-align:center;background:#fff;border:1px solid #DBEAFE;border-radius:10px;padding:12px 6px;">
            <div style="font-size:10px;color:${PDF_MUTED};margin-bottom:5px;">${seg.label}</div>
            <div style="font-size:20px;font-weight:800;color:${PDF_BLUE};">${weights[seg.key] ?? 0}%</div>
          </div>`).join('')}
      </div>
      <div style="font-size:11px;color:${PDF_MUTED};margin-top:10px;">${feeNote}</div>
    </div>
    <div style="background:#F8FAFF;border:1px solid #DBEAFE;border-radius:12px;padding:16px 22px;">
      <div style="font-size:11px;font-weight:700;color:${PDF_MUTED};margin-bottom:6px;text-transform:uppercase;letter-spacing:0.06em;">כיצד מחושב AmoScore?</div>
      <div style="font-size:11px;color:${PDF_MUTED};line-height:1.7;">
        AmoScore מחושב על בסיס 5 פרמטרים: תשואה שנה, תשואה 3 שנים, תשואה 5 שנים, Sharp Ratio ומדד נזילות.
        התשואות וה-Sharp עוברים נורמליזציה לסקאלה של 0–100 ביחס לכלל הקופות בהשוואה; מדד הנזילות
        (צבירה נטו ב-12 החודשים האחרונים ביחס לנכסי הקופה) מדורג באחוזונים — הקופה עם הצבירה הנטו הגבוהה ביותר
        מקבלת 100 וזו שיוצאים ממנה הכי הרבה כספים מקבלת 0. כל פרמטר מוכפל במשקל שנבחר.
      </div>
    </div>
    ${pdfFooter(1, totalPages)}`;

  // ── Per-fund pages ──────────────────────────────────────────────────────────
  const fundPages = funds.map(({ client, alternatives, golden }, fi) => {
    const clientIsTop3 = client.rank != null && client.rank <= 3;
    const allRows = [
      { ...client, isClient: true, potential_amount: client.amount, diff: null },
      ...alternatives.map(a => ({ ...a, isClient: false })),
    ].sort((a, b) => (b.grade ?? 0) - (a.grade ?? 0));

    const rowsHTML = allRows.map((f, idx) => {
      let bg = idx % 2 === 0 ? '#ffffff' : '#F8FAFC';
      if (f.isClient) bg = clientIsTop3 ? '#EFF6FF' : '#FEF2F2';
      const clientColor = clientIsTop3 ? PDF_BLUE : '#EF4444';

      return `
        <tr style="background:${bg};">
          <td style="padding:13px 16px;font-weight:600;color:${PDF_TEXT};font-size:14px;">
            ${f.isClient ? `<span style="color:${clientColor};font-weight:800;">${f.rank ?? idx+1}</span>`
                         : idx + 1}
            ${idx < 3 && !f.isClient
              ? `<span style="background:#EFF6FF;color:${PDF_BLUE};font-size:10px;
                  font-weight:700;padding:3px 7px;border-radius:8px;margin-right:4px;">מומלץ</span>`
              : ''}
          </td>
          <td style="padding:13px 16px;color:${PDF_TEXT};font-weight:${f.isClient ? '700' : '400'};font-size:14px;">
            ${f.name}
            ${f.hevra ? `<div style="font-size:11px;color:${PDF_MUTED};margin-top:2px;">${f.hevra}</div>` : ''}
            ${f.id ? `<div style="font-size:11px;color:${PDF_MUTED};">קופה #${f.id}</div>` : ''}
            ${f.isClient
              ? `<span style="background:${clientIsTop3 ? '#EFF6FF' : '#FEF2F2'};
                  color:${clientColor};font-size:10px;font-weight:700;
                  padding:3px 7px;border-radius:8px;margin-right:6px;">הקופה שלך</span>`
              : ''}
          </td>
          <td style="padding:13px 16px;text-align:center;color:${PDF_TEXT};font-weight:700;font-size:15px;">
            ${gradeText(f)}
          </td>
          <td style="padding:13px 16px;text-align:center;color:${PDF_TEXT};font-size:14px;">
            ${f.tsua_1 != null ? fmtDec(f.tsua_1) + '%' : '—'}
          </td>
          <td style="padding:13px 16px;text-align:center;color:${PDF_TEXT};font-size:14px;">
            ${RISK_LABELS[client.risk_level] ?? '—'}
          </td>
          <td style="padding:13px 16px;text-align:center;color:${PDF_TEXT};font-weight:700;font-size:15px;">
            ${f.potential_amount != null ? '₪' + fmt(f.potential_amount) : '—'}
          </td>
          <td style="padding:13px 16px;text-align:center;font-weight:700;font-size:14px;
            color:${f.diff == null ? PDF_MUTED : f.diff >= 0 ? '#16A34A' : '#EF4444'};">
            ${f.diff == null ? '—' : (f.diff >= 0 ? '+' : '') + '₪' + fmt(Math.abs(f.diff))
              + (f.diff_percent != null ? `<div style="font-size:11px;font-weight:600;">${f.diff >= 0 ? '+' : ''}${fmtDec(f.diff_percent)}%</div>` : '')}
          </td>
        </tr>`;
    }).join('');

    return `
      ${pdfHeader(today)}

      <div style="background:#F8FAFF;border:1px solid #DBEAFE;border-radius:12px;
        padding:18px 22px;margin-bottom:20px;">
        <div style="font-size:11px;font-weight:600;color:${PDF_BLUE};
          text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">פרטי הקופה</div>
        <div style="font-size:20px;font-weight:800;color:${PDF_DARK};margin-bottom:8px;">
          ${client.name}
        </div>
        <div style="font-size:12px;color:${PDF_MUTED};margin-bottom:14px;">
          קופה #${client.id}
          ${client.hevra ? ' · ' + client.hevra : ''}
          ${client.risk_level ? ' · רמת סיכון: ' + (RISK_LABELS[client.risk_level] ?? client.risk_level) : ''}
          ${client.rank != null ? ' · מקום ' + client.rank + ' מתוך ' + client.total_in_risk + ' קופות' : ''}
        </div>
        <div style="display:flex;gap:20px;">
          ${[
            ['סכום צבירה',     '₪' + fmt(client.amount)],
            ['תשואה שנתית',    client.tsua_1 ? fmtDec(client.tsua_1) + '%' : 'N/A'],
            ['AmoScore',       gradeText(client)],
            ['דמי ניהול',      client.dmei_nihul != null ? fmtDec(client.dmei_nihul, 2) + '%' : '—'],
          ].map(([label, val]) => `
            <div style="flex:1;background:#fff;border:1px solid #DBEAFE;
              border-radius:8px;padding:12px;text-align:center;">
              <div style="font-size:10px;color:${PDF_MUTED};margin-bottom:4px;">${label}</div>
              <div style="font-size:16px;font-weight:800;color:${PDF_DARK};">${val}</div>
            </div>`).join('')}
        </div>
      </div>

      <table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:8px;">
        <thead>
          <tr style="background:linear-gradient(135deg,${PDF_BLUE},${PDF_PURPLE});">
            <th style="padding:13px 16px;text-align:right;color:#fff;font-weight:700;font-size:13px;">דירוג</th>
            <th style="padding:13px 16px;text-align:right;color:#fff;font-weight:700;font-size:13px;">שם הקופה</th>
            <th style="padding:13px 16px;text-align:center;color:#fff;font-weight:700;font-size:13px;">AmoScore</th>
            <th style="padding:13px 16px;text-align:center;color:#fff;font-weight:700;font-size:13px;">תשואה שנתית</th>
            <th style="padding:13px 16px;text-align:center;color:#fff;font-weight:700;font-size:13px;">רמת סיכון</th>
            <th style="padding:13px 16px;text-align:center;color:#fff;font-weight:700;font-size:13px;">סכום פוטנציאלי</th>
            <th style="padding:13px 16px;text-align:center;color:#fff;font-weight:700;font-size:13px;">הפרש</th>
          </tr>
        </thead>
        <tbody>${rowsHTML}</tbody>
      </table>
      <div style="font-size:11px;color:${PDF_MUTED};margin-bottom:20px;">
        * לא נוכו דמי ניהול חיצוניים מהחישוב · ${feeNote}
      </div>

      ${(() => {
        const showMissed = alternatives[0] && client.rank !== 1 && alternatives[0].potential_amount > client.amount;
        const showGold   = golden && golden.potential_amount != null && golden.potential_amount > client.amount;
        if (!showMissed && !showGold) return '';
        const best = alternatives[0];
        const missedHTML = showMissed ? `
          <div style="flex:1;min-width:220px;display:flex;align-items:flex-start;gap:10px;
            background:linear-gradient(135deg,rgba(30,27,75,0.08),rgba(49,46,129,0.04));
            border:1.5px solid rgba(67,56,202,0.3);border-radius:12px;padding:16px 18px;">
            <div style="font-size:22px;flex-shrink:0;">⚡</div>
            <div style="flex:1;">
              <div style="font-size:13px;font-weight:800;color:#4F46E5;margin-bottom:5px;">מה החמצת?</div>
              <div style="font-size:11px;color:${PDF_MUTED};margin-bottom:10px;line-height:1.5;">
                מעבר לקופה המובילה היה מגדיל ב-<strong style="color:#4F46E5;">${fmtDec(best.diff_percent)}%</strong>
              </div>
              <div style="display:flex;align-items:flex-start;gap:14px;">
                <div>
                  <div style="font-size:9px;color:${PDF_MUTED};margin-bottom:2px;">היום</div>
                  <div style="font-size:16px;font-weight:800;color:${PDF_TEXT};">₪${fmt(client.amount)}</div>
                  ${client.tsua_1 ? `<div style="font-size:9px;color:${PDF_MUTED};">${fmtDec(client.tsua_1)}%</div>` : ''}
                </div>
                <div style="font-size:16px;color:#4F46E5;margin-top:12px;">←</div>
                <div>
                  <div style="font-size:9px;color:${PDF_MUTED};margin-bottom:2px;">פוטנציאל</div>
                  <div style="font-size:16px;font-weight:800;color:#16A34A;">₪${fmt(best.potential_amount)}</div>
                  ${best.tsua_1 ? `<div style="font-size:9px;color:${PDF_MUTED};">${fmtDec(best.tsua_1)}%</div>` : ''}
                </div>
              </div>
            </div>
          </div>` : '';
        const goldHTML = showGold ? `
          <div style="flex:1;min-width:220px;display:flex;align-items:flex-start;gap:10px;
            background:linear-gradient(135deg,rgba(120,83,15,0.08),rgba(161,110,20,0.04));
            border:1.5px solid rgba(234,179,8,0.5);border-radius:12px;padding:16px 18px;">
            <div style="font-size:22px;flex-shrink:0;">🏆</div>
            <div style="flex:1;">
              <div style="font-size:13px;font-weight:800;color:#B45309;margin-bottom:2px;">תפוח הזהב</div>
              <div style="font-size:9px;color:#D97706;font-weight:600;margin-bottom:8px;">מקום #1 סיכון גבוה${golden.name ? ' · ' + golden.name : ''}${golden.id ? ' · #' + golden.id : ''}</div>
              <div style="font-size:11px;color:${PDF_MUTED};margin-bottom:10px;line-height:1.5;">
                מעבר לסיכון גבוה הייתה מגדילה ב-<strong style="color:#B45309;">${fmtDec(golden.diff_percent)}%</strong>
              </div>
              <div style="display:flex;align-items:flex-start;gap:14px;">
                <div>
                  <div style="font-size:9px;color:${PDF_MUTED};margin-bottom:2px;">היום</div>
                  <div style="font-size:16px;font-weight:800;color:${PDF_TEXT};">₪${fmt(client.amount)}</div>
                </div>
                <div style="font-size:16px;color:#D97706;margin-top:12px;">←</div>
                <div>
                  <div style="font-size:9px;color:${PDF_MUTED};margin-bottom:2px;">פוטנציאל</div>
                  <div style="font-size:16px;font-weight:800;color:#B45309;">₪${fmt(golden.potential_amount)}</div>
                  ${golden.tsua_1 ? `<div style="font-size:9px;color:#D97706;">${fmtDec(golden.tsua_1)}%</div>` : ''}
                </div>
              </div>
            </div>
          </div>` : '';
        return `<div style="display:flex;gap:12px;flex-wrap:wrap;">${missedHTML}${goldHTML}</div>`;
      })()}

      ${pdfFooter(fi + 2, totalPages)}`;
  });

  // ── Per-page render: one small html2canvas per page (much faster for many funds) ──
  const pdf   = new jsPDF('p', 'mm', 'a4');
  const pageW = 210, pageH = 297;
  const allPages = [coverHTML, ...fundPages];
  const pageStyle = `padding:40px 48px;box-sizing:border-box;background:#ffffff;`;
  const wrapStyle = `position:absolute;top:0;left:-9999px;width:794px;background:#ffffff;direction:rtl;font-family:'Rubik',Arial,sans-serif;color:${PDF_TEXT};`;

  await document.fonts.ready;

  let firstPage = true;
  for (const html of allPages) {
    const wrap = document.createElement('div');
    wrap.style.cssText = wrapStyle;
    const page = document.createElement('div');
    page.style.cssText = pageStyle;
    page.innerHTML = html;
    wrap.appendChild(page);
    document.body.appendChild(wrap);

    // One RAF to let the browser paint before capture
    await new Promise(r => requestAnimationFrame(r));

    try {
      const canvas = await html2canvas(wrap, {
        scale: 1.5, backgroundColor: '#ffffff',
        useCORS: true, logging: false, scrollX: 0, scrollY: 0, windowWidth: 794,
      });

      const imgData = canvas.toDataURL('image/jpeg', 0.88);
      const imgH    = (canvas.height * pageW) / canvas.width;

      if (!firstPage) pdf.addPage();
      firstPage = false;

      let y = 0;
      while (y < imgH) {
        if (y > 0) pdf.addPage();
        pdf.addImage(imgData, 'JPEG', 0, -y, pageW, imgH);
        y += pageH;
      }
    } finally {
      document.body.removeChild(wrap);
    }
  }

  const dateStr = today.replace(/\//g, '-');
  const now     = new Date();
  const timeStr = `${String(now.getHours()).padStart(2,'0')}-${String(now.getMinutes()).padStart(2,'0')}-${String(now.getSeconds()).padStart(2,'0')}`;
  pdf.save(`AmoSight-${dateStr}_${timeStr}.pdf`);
}

// ─── Summary Hero helpers ─────────────────────────────────────────────────────

// Takes the best of (same-risk alt, golden) vs current — for the summary total.
// `suffix` picks the horizon: '' (1 year), '_3' or '_5'.
function getPotentialAmount(fund, suffix = '', includeGolden = true) {
  const { client, alternatives, golden } = fund;
  const bestAlt = alternatives?.[0];
  const sameRiskPotential = (bestAlt && client.rank !== 1) ? (bestAlt[`potential_amount${suffix}`] ?? 0) : 0;
  const goldenPotential   = includeGolden ? (golden?.[`potential_amount${suffix}`] ?? 0) : 0;
  const best = Math.max(sameRiskPotential, goldenPotential);
  return best > client.amount ? best : client.amount;
}

function SummaryHero({ results }) {
  const totalCurrent   = results.reduce((s, f) => s + (f.client.amount ?? 0), 0);
  const totalPotential = results.reduce((s, f) => s + getPotentialAmount(f), 0);
  const diff           = totalPotential - totalCurrent;
  const diffPct        = totalCurrent > 0 ? (diff / totalCurrent) * 100 : 0;
  const hasUpside      = diff > 0;

  return (
    <div className="summary-hero">
      <div className="summary-hero-label">📊 סיכום כלל הקופות</div>

      <div className="summary-hero-row">
        {/* Current */}
        <div className="summary-hero-block">
          <div className="summary-hero-block-label">צבירה נוכחית</div>
          <div className="summary-hero-amount summary-hero-amount--current">
            ₪{fmt(totalCurrent)}
          </div>
        </div>

        {/* Arrow */}
        <div className="summary-hero-vs">
          {hasUpside ? (
            <div className="summary-hero-arrow-wrap">
              <span className="summary-hero-arrow">←</span>
              <span className="summary-hero-diff-badge">
                +₪{fmt(diff)}<span className="summary-hero-diff-pct"> ({fmtDec(diffPct)}%)</span>
              </span>
            </div>
          ) : (
            <span className="summary-hero-checkmark">✓</span>
          )}
        </div>

        {/* Potential */}
        <div className="summary-hero-block">
          <div className="summary-hero-block-label">פוטנציאל</div>
          <div className={`summary-hero-amount ${hasUpside ? 'summary-hero-amount--potential' : 'summary-hero-amount--current'}`}>
            ₪{fmt(totalPotential)}
          </div>
        </div>
      </div>

      {hasUpside && (
        <div className="summary-hero-cta">
          השנה החמצת <strong>₪{fmt(diff)}</strong> — עדיין לא מאוחר לעבור
        </div>
      )}
    </div>
  );
}

// ─── Community: Invite Screen ─────────────────────────────────────────────────

function InviteScreen({ results, onJoined, onBack }) {
  const [joining, setJoining] = useState(false);

  // Always merge identical funds for community display/submission (fair representation)
  const mergedResults = aggregateResults(results || []);

  const totalAmount = mergedResults.reduce((s, f) => s + (f.client?.amount ?? 0), 0);
  const weightedTsua = totalAmount > 0
    ? mergedResults.reduce((s, f) => s + (f.client?.tsua_1 ?? 0) * (f.client?.amount ?? 0) / totalAmount, 0)
    : 0;
  const weightedScore = totalAmount > 0
    ? mergedResults.filter(f => (f.client?.default_grade ?? 0) > 0)
        .reduce((s, f) => s + (f.client?.default_grade ?? 0) * (f.client?.amount ?? 0) / totalAmount, 0)
    : 0;
  const fundsWithExposure = mergedResults.filter(f => f.client?.equity_exposure != null);
  const exposureWeightTotal = fundsWithExposure.reduce((s, f) => s + (f.client?.amount ?? 0), 0);
  const weightedExposure = exposureWeightTotal > 0
    ? fundsWithExposure.reduce((s, f) => s + (f.client.equity_exposure * (f.client?.amount ?? 0)), 0) / exposureWeightTotal
    : null;

  const handleJoin = async () => {
    setJoining(true);
    try {
      const clientId = mergedResults?.[0]?.client?.client_id || 'unknown';
      const joinData = {
        client_id: clientId,
        funds: mergedResults.map(f => ({
          name: f.client?.name || '',
          id: f.client?.id || '',
          risk_level: f.client?.risk_level || 'high',
          tsua_1: f.client?.tsua_1 ?? 0,
          grade: f.client?.default_grade ?? 0,
          amount: f.client?.amount ?? 0,
          equity_exposure: f.client?.equity_exposure ?? null,
          pct_of_total: totalAmount > 0
            ? Math.round((f.client?.amount ?? 0) / totalAmount * 1000) / 10
            : 0,
        })),
      };
      const res = await fetch('http://localhost:8000/community/join', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(joinData),
      });
      const data = await res.json();
      onJoined(data.profile);
    } catch (err) {
      console.error(err);
      alert('שגיאה בהצטרפות לקהילה. אנא בדוק שהשרת פועל ונסה שוב.');
    } finally {
      setJoining(false);
    }
  };

  return (
    <div className="screen community-screen">

      <Header onReset={onBack} />
      <div className="community-content">
        <button className="back-btn community-back" onClick={onBack}>→ חזרה לתוצאות</button>

        <div className="community-invite-hero">
          <h1 className="community-title">🏆 הצטרף לקהילת המשקיעים</h1>
          <p className="community-subtitle">
            גלה איך הפורטפוליו שלך ביחס למשקיעים אחרים — בצורה אנונימית לחלוטין.<br />
            הפרופיל שלך יוצג עם שם בדוי בלבד. אף אחד לא יידע מי אתה.
          </p>
        </div>

        <div className="community-invite-grid">
          <div className="community-card community-preview-card">
            <div className="community-card-label">כך ייראה הפרופיל שלך</div>
            <div className="community-preview-header">
              <div className="community-avatar-sm">🦁</div>
              <div>
                <div className="community-preview-name">משקיע מסתורי</div>
                <div className="community-preview-date">
                  הצטרף {new Date().toLocaleDateString('he-IL', { month: '2-digit', year: 'numeric' })}
                </div>
              </div>
            </div>
            <div className="community-preview-stats">
              <div className="community-stat-mini">
                <div className="community-stat-mini-val" style={{ color: '#3B82F6' }}>{fmtDec(weightedScore)}</div>
                <div className="community-stat-mini-label">AmoScore*</div>
              </div>
              <div className="community-stat-mini">
                <div className="community-stat-mini-val" style={{ color: '#10B981' }}>{fmtDec(weightedTsua)}%</div>
                <div className="community-stat-mini-label">תשואה שנתית</div>
              </div>
              <div className="community-stat-mini">
                <div className="community-stat-mini-val" style={{ color: '#F59E0B' }}>
                  {weightedExposure != null ? `${fmtDec(weightedExposure)}%` : '—'}
                </div>
                <div className="community-stat-mini-label">חשיפה למניות</div>
              </div>
            </div>
          </div>

          <div className="community-card community-privacy-card">
            <div className="community-card-label">מה מוצג בפרופיל?</div>
            <ul className="community-privacy-list">
              <li className="privacy-item privacy-yes">✓ אחוז מהתיק לכל קופה</li>
              <li className="privacy-item privacy-yes">✓ תשואה שנתית משוקללת</li>
              <li className="privacy-item privacy-yes">✓ ציון AmoScore</li>
              <li className="privacy-item privacy-yes">✓ רמת סיכון דומיננטית</li>
              <li className="privacy-item privacy-no">✗ שם אמיתי — לעולם לא</li>
              <li className="privacy-item privacy-no">✗ סכומים בשקלים — לעולם לא</li>
            </ul>
          </div>
        </div>

        <button className="community-join-btn" onClick={handleJoin} disabled={joining}>
          {joining ? 'מצטרף...' : 'הצטרף לקהילה'}
        </button>
        <p className="community-disclaimer-small">
          ניתן לעזוב בכל עת · המידע שלך מאוחסן באופן מקומי בלבד
        </p>
        <p className="community-weights-note">
          * AmoScore בקהילה מחושב לפי משקלים קבועים וסטנדרטיים ({DEFAULT_WEIGHTS_TEXT}) — כדי להבטיח השוואה הוגנת בין כל המשקיעים, ללא תלות בהגדרות האישיות שלך.
        </p>
      </div>
    </div>
  );
}

// ─── Community: Leaderboard Screen ────────────────────────────────────────────

function LeaderboardScreen({ leaderboard, myProfile, onViewProfile, onBack }) {
  const [sortBy, setSortBy] = useState('score');
  const [riskFilter, setRiskFilter] = useState('all');

  const exposureToRisk = (exposure) => {
    if (exposure == null) return null;
    if (exposure <= 25) return 'low';
    if (exposure <= 75) return 'medium';
    return 'high';
  };

  const filtered = (leaderboard || [])
    .filter(p => {
      if (riskFilter === 'all') return true;
      const risk = exposureToRisk(p.weighted_equity_exposure) ?? p.dominant_risk;
      return risk === riskFilter;
    })
    .slice()
    .sort((a, b) =>
      sortBy === 'score'
        ? b.weighted_score - a.weighted_score
        : b.weighted_tsua - a.weighted_tsua
    );

  return (
    <div className="screen community-screen">

      <Header onReset={onBack} />
      <div className="community-content">
        <button className="back-btn community-back" onClick={onBack}>→ חזרה לתוצאות</button>

        <div className="leaderboard-hero">
          <h1 className="community-title">🏅 טבלת המשקיעים</h1>
          <div className="leaderboard-count">{(leaderboard || []).length} משקיעים בקהילה</div>
          <div className="leaderboard-weights-note">
            * AmoScore מחושב לפי משקלים קבועים: {DEFAULT_WEIGHTS_TEXT}
          </div>
        </div>

        <div className="leaderboard-controls">
          <div className="leaderboard-sort-group">
            <span className="leaderboard-control-label">מיין לפי:</span>
            <button
              className={`leaderboard-filter-btn${sortBy === 'score' ? ' active' : ''}`}
              onClick={() => setSortBy('score')}
            >AmoScore</button>
            <button
              className={`leaderboard-filter-btn${sortBy === 'tsua' ? ' active' : ''}`}
              onClick={() => setSortBy('tsua')}
            >תשואה שנתית</button>
          </div>
          <div className="leaderboard-risk-group">
            <span className="leaderboard-control-label">סיכון:</span>
            {['all', 'high', 'medium', 'low'].map(risk => (
              <button
                key={risk}
                className={`leaderboard-filter-btn${riskFilter === risk ? ' active' : ''}`}
                onClick={() => setRiskFilter(risk)}
                style={riskFilter === risk && risk !== 'all'
                  ? { borderColor: COMMUNITY_RISK_COLORS[risk], color: COMMUNITY_RISK_COLORS[risk] }
                  : {}}
              >
                {risk === 'all' ? 'הכל' : RISK_LABELS[risk]}
              </button>
            ))}
          </div>
        </div>

        <div className="leaderboard-table-wrap">
          <div className="leaderboard-table">
            <div className="leaderboard-header-row">
              <div className="lb-col lb-col-rank">#</div>
              <div className="lb-col lb-col-investor">משקיע</div>
              <div className="lb-col lb-col-score">AmoScore</div>
              <div className="lb-col lb-col-tsua">תשואה</div>
              <div className="lb-col lb-col-risk">חשיפה</div>
            </div>
            {filtered.map((profile, idx) => {
              const isMe = myProfile && profile.fake_name === myProfile.fake_name;
              return (
                <div
                  key={profile.fake_name}
                  className={`leaderboard-row${isMe ? ' leaderboard-row--me' : ''}${idx < 3 ? ` leaderboard-row--top${idx + 1}` : ''}`}
                  onClick={() => onViewProfile(profile.fake_name)}
                >
                  <div className="lb-col lb-col-rank">
                    {idx < 3 ? MEDALS[idx] : <span className="lb-rank-num">{idx + 1}</span>}
                  </div>
                  <div className="lb-col lb-col-investor">
                    <div className="lb-avatar">{getCommunityAvatar(profile.fake_name)}</div>
                    <div className="lb-investor-info">
                      <div className="lb-name">
                        {profile.fake_name}
                        {isMe && <span className="lb-me-badge">אתה</span>}
                      </div>
                      <div className="lb-meta">{profile.num_funds} קופות · {profile.joined}</div>
                    </div>
                  </div>
                  <div className="lb-col lb-col-score">
                    <span style={{ color: '#3B82F6', fontWeight: 700 }}>{fmtDec(profile.weighted_score)}</span>
                  </div>
                  <div className="lb-col lb-col-tsua">
                    <span style={{ color: '#10B981', fontWeight: 700 }}>{fmtDec(profile.weighted_tsua)}%</span>
                  </div>
                  <div className="lb-col lb-col-risk">
                    {profile.weighted_equity_exposure != null ? (
                      <span className="lb-exposure-badge">
                        {fmtDec(profile.weighted_equity_exposure)}%
                      </span>
                    ) : (
                      <span className="lb-risk-badge" style={{
                        background: COMMUNITY_RISK_COLORS[profile.dominant_risk] + '22',
                        color: COMMUNITY_RISK_COLORS[profile.dominant_risk],
                      }}>
                        {RISK_LABELS[profile.dominant_risk]}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
            {filtered.length === 0 && (
              <div className="leaderboard-empty">אין משקיעים תואמים לפילטר הנוכחי</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Community: Profile Screen ────────────────────────────────────────────────

function ProfileScreen({ fakeName, myProfile, leaderboard, onBack }) {
  const isMe = myProfile && fakeName === myProfile.fake_name;
  const [profile, setProfile] = useState(isMe ? myProfile : null);
  const [loading, setLoading] = useState(!isMe);

  useEffect(() => {
    if (isMe && myProfile) { setProfile(myProfile); setLoading(false); return; }
    setLoading(true);
    fetch(`http://localhost:8000/community/profile/${encodeURIComponent(fakeName)}`)
      .then(r => r.json())
      .then(data => { setProfile(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [fakeName, isMe, myProfile]);

  const rank = (leaderboard || []).findIndex(p => p.fake_name === fakeName) + 1;
  const totalInCommunity = (leaderboard || []).length;

  return (
    <div className="screen community-screen">

      <Header onReset={onBack} />
      <div className="community-content">
        <button className="back-btn community-back" onClick={onBack}>→ חזרה לטבלה</button>

        {loading && <div className="community-loading">טוען פרופיל...</div>}

        {!loading && profile && (
          <>
            <div className="community-card profile-header-card">
              <div className="profile-header-inner">
                <div className="profile-avatar-big">{getCommunityAvatar(profile.fake_name)}</div>
                <div className="profile-header-text">
                  <div className="profile-name-big">{profile.fake_name}</div>
                  <div className="profile-joined-date">הצטרף {profile.joined}</div>
                  {isMe && <span className="profile-me-badge">הפרופיל שלך ✨</span>}
                </div>
              </div>
            </div>

            <div className="profile-stats-grid">
              <div className="community-card profile-stat-card">
                <div className="profile-stat-icon">📊</div>
                <div className="profile-stat-val" style={{ color: '#3B82F6' }}>{fmtDec(profile.weighted_score)}</div>
                <div className="profile-stat-label">AmoScore</div>
              </div>
              <div className="community-card profile-stat-card">
                <div className="profile-stat-icon">📈</div>
                <div className="profile-stat-val" style={{ color: '#10B981' }}>{fmtDec(profile.weighted_tsua)}%</div>
                <div className="profile-stat-label">תשואה שנתית</div>
              </div>
              <div className="community-card profile-stat-card">
                <div className="profile-stat-icon">📉</div>
                <div className="profile-stat-val" style={{ color: '#F59E0B' }}>
                  {profile.weighted_equity_exposure != null
                    ? `${fmtDec(profile.weighted_equity_exposure)}%`
                    : RISK_LABELS[profile.dominant_risk]}
                </div>
                <div className="profile-stat-label">חשיפה למניות</div>
              </div>
              <div className="community-card profile-stat-card">
                <div className="profile-stat-icon">🏆</div>
                <div className="profile-stat-val" style={{ color: '#F59E0B' }}>
                  {rank > 0 ? `#${rank}` : '—'}
                </div>
                <div className="profile-stat-label">
                  דירוג{totalInCommunity > 0 ? ` מתוך ${totalInCommunity}` : ''}
                </div>
              </div>
            </div>

            {profile.funds && profile.funds.length > 0 && (
              <div className="community-card profile-funds-card">
                <div className="community-card-label">הקצאת קופות</div>
                <div className="fund-allocation-bar">
                  {profile.funds.map((fund, i) => (
                    <div
                      key={fund.id}
                      className="fund-allocation-segment"
                      style={{ width: `${fund.pct}%`, background: FUND_PALETTE[i % FUND_PALETTE.length] }}
                      title={`${fund.name}: ${fund.pct}%`}
                    />
                  ))}
                </div>
                <div className="fund-allocation-list">
                  {profile.funds.map((fund, i) => (
                    <div key={fund.id} className="fund-allocation-item">
                      <div className="fund-dot" style={{ background: FUND_PALETTE[i % FUND_PALETTE.length] }} />
                      <div className="fund-alloc-name">{fund.name}</div>
                      <div className="fund-alloc-id">#{fund.id}</div>
                      <div className="fund-alloc-pct" style={{ color: FUND_PALETTE[i % FUND_PALETTE.length] }}>
                        {fmtDec(fund.pct)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="community-disclaimer">
              * הנתונים מוצגים באחוזים בלבד לשמירה על פרטיות המשתמש. אין חשיפה של סכומים כספיים.
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Results Screen ───────────────────────────────────────────────────────────

function ResultsScreen({ results, portfolio, weights, thresholds, feeMode, onFeeModeChange, onReset, resetLabel, subject, onGoToInvite }) {
  const [selectedId, setSelectedId] = useState('all');
  const [pdfLoading, setPdfLoading] = useState(false);
  const [atBottom, setAtBottom] = useState(false);

  // Alternatives as shown under the chosen fee mode; the client's own fund is never affected
  const viewResults = useMemo(() => (results || []).map(h => applyFeeMode(h, feeMode)), [results, feeMode]);

  useEffect(() => {
    const onScroll = () => {
      const nearBottom = window.innerHeight + window.scrollY >= document.body.scrollHeight - 150;
      setAtBottom(nearBottom);
    };
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const handleScrollToggle = () => {
    if (atBottom) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    }
  };

  const handleDownloadPDF = async () => {
    setPdfLoading(true);
    try {
      await generatePDF(viewResults, weights, { feeMode, portfolio });
    } catch (e) {
      console.error('PDF Error:', e);
      alert('שגיאה: ' + (e?.message ?? e));
    } finally {
      setPdfLoading(false);
    }
  };

  const filtered = selectedId === 'all'
    ? viewResults
    : viewResults.filter(d => d.client?.id === selectedId);

  return (
    <div className="screen screen--results">

      <Header onReset={onReset} resetLabel={resetLabel} />
      <div id="results-content" className="results-content">

        {viewResults.length > 0 && (
          <div className="results-top">
            {subject && <div className="results-subject">{subject}</div>}
            <SummaryHero results={viewResults} />
            <FeeModeToggle feeMode={feeMode} onChange={onFeeModeChange} />
          </div>
        )}

        {viewResults.length > 1 && (() => {
          const grouped = [];
          const seen = new Map();
          for (const d of viewResults) {
            const id = d.client?.id;
            if (seen.has(id)) { seen.get(id).count++; } else { const entry = { id, name: d.client?.name, count: 1 }; seen.set(id, entry); grouped.push(entry); }
          }
          return (
            <div className="results-filter">
              <label className="results-filter-label">הצג קופה:</label>
              <select
                className="results-filter-select"
                value={selectedId}
                onChange={e => setSelectedId(e.target.value)}
              >
                <option value="all">כל הקופות ({viewResults.length})</option>
                {grouped.map(({ id, name, count }) => (
                  <option key={id} value={id}>
                    #{id} — {name}{count > 1 ? ` (×${count})` : ''}
                  </option>
                ))}
              </select>
            </div>
          );
        })()}

        {filtered.map((data, i) => (
          <div key={(data.client?.id ?? i) + '-' + i}>
            <FundResults data={data} weights={weights} thresholds={thresholds} feeMode={feeMode} onFeeModeChange={onFeeModeChange} />
          </div>
        ))}

        <PortfolioScoreCard portfolio={portfolio} results={results} />

        <div className="amoscore-explanation">
          <div className="amoscore-explanation-header">
            <span className="amoscore-explanation-icon">📐</span>
            <div className="amoscore-explanation-title">כיצד מחושב AmoScore?</div>
          </div>
          <div className="amoscore-explanation-body">
            <p>
              AmoScore הוא ציון מורכב המשקלל חמישה פרמטרים של ביצועי קופת הגמל: תשואה לשנה, תשואה ל-3 שנים, תשואה ל-5 שנים, Sharp Ratio — מדד לתשואה מתואמת סיכון — ומדד נזילות.
            </p>
            <p>
              התשואות וה-Sharp עוברים נורמליזציה לסקאלה של 0–100 ביחס לכלל הקופות בהשוואה, כך שהקופה הטובה ביותר בכל פרמטר מקבלת 100 והחלשה ביותר מקבלת 0. לאחר מכן כל פרמטר מוכפל במשקל שבחרת, והציון הסופי הוא הסכום המשוקלל — מספר בין 0 ל-100 שמאפשר השוואה ישירה בין קופות.
            </p>
            <p>
              מדד הנזילות הוא הצבירה נטו של הקופה ב-12 החודשים האחרונים (כניסות פחות יציאות) ביחס ליתרת הנכסים שלה, לפי גמל נט. הוא מדורג באחוזונים: הקופה שנכנס אליה הכי הרבה כסף ביחס לגודלה מקבלת 100, וזו שיוצאים ממנה הכי הרבה כספים מקבלת 0.
            </p>
            {weights && (
              <div className="amoscore-weights-chips">
                {WEIGHT_SEGMENTS.map(seg => (
                  <div key={seg.key} className="weight-chip">
                    <div className="weight-chip-label">{seg.label}</div>
                    <div className="weight-chip-val">{weights[seg.key] ?? 0}%</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {onGoToInvite && (
          <div className="community-invite-banner">
            <div className="invite-banner-text">
              <div className="invite-banner-title">🏅 רוצה לראות איך אתה ביחס למשקיעים אחרים?</div>
              <div className="invite-banner-subtitle">הצטרף לקהילה האנונימית שלנו וגלה את הדירוג שלך</div>
            </div>
            <button className="invite-banner-btn" onClick={onGoToInvite}>הצטרף</button>
          </div>
        )}

        <div className="pdf-button-container">
          <button
            className="download-pdf-btn"
            onClick={handleDownloadPDF}
            disabled={pdfLoading}
          >
            {pdfLoading ? 'מפיק PDF...' : 'הורד דוח PDF'}
          </button>
        </div>

        <div className="portfolio-footer">
          נבנה ב ❤️ על ידי{' '}
          <a href="https://techiloli.vercel.app/" target="_blank" rel="noopener noreferrer">
            Ilay Atia
          </a>
        </div>

      </div>

      <button className={`scroll-nav-btn${atBottom ? ' scroll-nav-btn--up' : ''}`} onClick={handleScrollToggle}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points={atBottom ? "18 15 12 9 6 15" : "6 9 12 15 18 9"} />
        </svg>
        <span>{atBottom ? 'חזור לראש' : 'לסוף הדף'}</span>
      </button>
    </div>
  );
}

// ─── Bulk Results Screen ──────────────────────────────────────────────────────

const HORIZONS = [
  { years: 1, suffix: '',   label: 'שנה' },
  { years: 3, suffix: '_3', label: '3 שנים' },
  { years: 5, suffix: '_5', label: '5 שנים' },
];
const BULK_PAGE_SIZE = 200;

const clientLabel = c => c.client_name || (c.client_id ? `ת״ז ${c.client_id}` : c.files[0]);
const clientKey = c => c.client_id ?? `file:${c.files[0]}`;

// A client's total NIS gain from moving, over all holdings — the same figure the
// summary at the top of their full report shows (with the same golden-option rule).
export function clientUpside(client, feeMode, suffix = '', includeGolden = true) {
  return client.funds.reduce((sum, raw) => {
    const h = applyFeeMode(raw, feeMode);
    return sum + (getPotentialAmount(h, suffix, includeGolden) - h.client.amount);
  }, 0);
}

// The client's holding whose move gains the most, and the fund it should move to
export function topMove(client, feeMode, suffix = '', includeGolden = true) {
  let best = null;
  for (const raw of client.funds) {
    const h = applyFeeMode(raw, feeMode);
    const gain = getPotentialAmount(h, suffix, includeGolden) - h.client.amount;
    if (gain <= 0 || (best && gain <= best.gain)) continue;
    const alt = h.alternatives?.[0];
    const altPotential = alt && h.client.rank !== 1 ? (alt[`potential_amount${suffix}`] ?? 0) : 0;
    const goldPotential = includeGolden ? (h.golden?.[`potential_amount${suffix}`] ?? 0) : 0;
    best = { gain, from: h.client, to: goldPotential > altPotential ? h.golden : alt };
  }
  return best;
}

function csvCell(value) {
  const s = value == null ? '' : String(value);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function downloadCsv(filename, rows) {
  const csv = rows.map(r => r.map(csvCell).join(',')).join('\r\n');
  // The BOM makes Excel open the Hebrew text as UTF-8
  const blob = new Blob(['\ufeff', csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const BULK_SORTS = [
  { key: 'upside',    label: 'רווח ₪' },
  { key: 'upsidePct', label: 'רווח %' },
  { key: 'score',     label: 'ציון נמוך' },
  { key: 'amount',    label: 'צבירה' },
];

function BulkResultsScreen({ data, feeMode, onFeeModeChange, onBack, onOpenClient }) {
  const [horizon, setHorizon] = useState(HORIZONS[0]);
  const [includeGolden, setIncludeGolden] = useState(true);
  const [sortBy, setSortBy] = useState('upside');
  const [query, setQuery] = useState('');
  const [issuesOpen, setIssuesOpen] = useState(false);
  const [limit, setLimit] = useState(BULK_PAGE_SIZE);

  const rows = useMemo(() => (data?.clients ?? []).map(c => {
    const upside = clientUpside(c, feeMode, horizon.suffix, includeGolden);
    return {
      client: c,
      upside,
      upsidePct: c.portfolio.total_amount > 0 ? upside / c.portfolio.total_amount * 100 : 0,
      move: topMove(c, feeMode, horizon.suffix, includeGolden),
    };
  }), [data, feeMode, horizon, includeGolden]);

  const visible = useMemo(() => {
    const q = query.trim();
    const matched = q
      ? rows.filter(r => [r.client.client_id, r.client.client_name, ...r.client.files].some(v => v && String(v).includes(q)))
      : rows;
    const score = r => r.client.portfolio.weighted_score ?? 101; // unscored clients sort last
    const sorters = {
      upside:    (a, b) => b.upside - a.upside || score(a) - score(b),
      upsidePct: (a, b) => b.upsidePct - a.upsidePct || score(a) - score(b),
      score:     (a, b) => score(a) - score(b) || b.upside - a.upside,
      amount:    (a, b) => b.client.portfolio.total_amount - a.client.portfolio.total_amount,
    };
    return [...matched].sort(sorters[sortBy]);
  }, [rows, query, sortBy]);

  const totalAmount = rows.reduce((s, r) => s + r.client.portfolio.total_amount, 0);
  const totalUpside = rows.reduce((s, r) => s + r.upside, 0);
  const needMove = rows.filter(r => r.upside > 0).length;
  const maxUpside = Math.max(1, ...rows.map(r => r.upside));
  const issues = [
    ...(data?.errors ?? []).map(e => ({ file: e.file, text: e.error, kind: 'error' })),
    ...(data?.skipped ?? []).map(s => ({ file: s.file, text: s.reason, kind: 'skip' })),
  ];
  const feeLabel = FEE_MODES.find(m => m.key === feeMode)?.label;

  const handleExport = () => {
    const header = [
      'עדיפות', 'ת״ז', 'שם', 'קבצים', 'קופות', 'צבירה כוללת', 'ציון תיק משוקלל', 'ציון אחרי ניוד',
      'כיסוי דירוג %',
      `רווח מניוד — ${horizon.label}, ${feeLabel}, ${includeGolden ? 'כולל תפוח הזהב' : 'באותה רמת סיכון'}`,
      'רווח % מהצבירה', 'מהלך מומלץ',
    ];
    const body = visible.map((r, i) => {
      const p = r.client.portfolio;
      return [
        i + 1, r.client.client_id ?? '', r.client.client_name, r.client.files.join(' | '), r.client.funds.length,
        Math.round(p.total_amount), p.weighted_score ?? '', p.potential_score ?? '', p.coverage,
        Math.round(r.upside), r.upsidePct.toFixed(2),
        r.move ? `${r.move.from.name} (#${r.move.from.id}) ← ${r.move.to.name} (#${r.move.to.id})` : '',
      ];
    });
    downloadCsv(`AmoSight-clients-${new Date().toISOString().slice(0, 10)}.csv`, [header, ...body]);
  };

  return (
    <div className="screen screen--results">

      <Header onReset={onBack} />
      <div className="results-content bulk-content">

        <div className="bulk-summary">
          <div className="summary-hero-label">👥 ניתוח מרובה לקוחות</div>
          <div className="bulk-stats">
            <div className="bulk-stat">
              <div className="bulk-stat-val">{rows.length.toLocaleString('he-IL')}</div>
              <div className="bulk-stat-label">לקוחות</div>
            </div>
            <div className="bulk-stat">
              <div className="bulk-stat-val">{(data?.files_received ?? 0).toLocaleString('he-IL')}</div>
              <div className="bulk-stat-label">קבצים שהועלו</div>
            </div>
            <div className="bulk-stat">
              <div className="bulk-stat-val">₪{fmt(totalAmount)}</div>
              <div className="bulk-stat-label">צבירה כוללת</div>
            </div>
            <div className="bulk-stat">
              <div className="bulk-stat-val bulk-stat-val--gain">₪{fmt(totalUpside)}</div>
              <div className="bulk-stat-label">רווח מניוד · {horizon.label}</div>
            </div>
            <div className="bulk-stat">
              <div className="bulk-stat-val">{needMove.toLocaleString('he-IL')}</div>
              <div className="bulk-stat-label">לקוחות שירוויחו מניוד</div>
            </div>
          </div>
        </div>

        <FeeModeToggle feeMode={feeMode} onChange={onFeeModeChange} />

        <div className="bulk-controls">
          <div className="bulk-control-group">
            <span className="leaderboard-control-label">תקופה:</span>
            {HORIZONS.map(h => (
              <button key={h.years} className={`leaderboard-filter-btn${horizon.years === h.years ? ' active' : ''}`} onClick={() => setHorizon(h)}>
                {h.label}
              </button>
            ))}
          </div>
          <div className="bulk-control-group">
            <span className="leaderboard-control-label">חלופות:</span>
            <button
              className={`leaderboard-filter-btn${!includeGolden ? ' active' : ''}`}
              onClick={() => setIncludeGolden(false)}
              title="רק מעבר לקופה טובה יותר באותה רמת סיכון — הלקוחות שנמצאים בקופה חלשה"
            >
              באותה רמת סיכון
            </button>
            <button
              className={`leaderboard-filter-btn${includeGolden ? ' active' : ''}`}
              onClick={() => setIncludeGolden(true)}
              title="כולל מעבר לקופה המובילה בסיכון גבוה, כמו בסיכום של כל דוח"
            >
              כולל תפוח הזהב 🍎
            </button>
          </div>
          <div className="bulk-control-group">
            <span className="leaderboard-control-label">מיין לפי:</span>
            {BULK_SORTS.map(s => (
              <button key={s.key} className={`leaderboard-filter-btn${sortBy === s.key ? ' active' : ''}`} onClick={() => setSortBy(s.key)}>
                {s.label}
              </button>
            ))}
          </div>
          <div className="bulk-control-group bulk-control-group--grow">
            <input
              className="bulk-search"
              type="search"
              placeholder="חיפוש לפי ת״ז, שם או קובץ"
              value={query}
              onChange={e => { setQuery(e.target.value); setLimit(BULK_PAGE_SIZE); }}
            />
            <button className="leaderboard-filter-btn" onClick={handleExport} disabled={visible.length === 0}>
              ⬇ ייצוא ל-Excel
            </button>
          </div>
        </div>

        {issues.length > 0 && (
          <div className="bulk-issues">
            <button className="bulk-issues-toggle" onClick={() => setIssuesOpen(o => !o)}>
              ⚠ {issues.length === 1 ? 'קובץ אחד לא נותח' : `${issues.length.toLocaleString('he-IL')} קבצים לא נותחו`} {issuesOpen ? '▲' : '▼'}
            </button>
            {issuesOpen && (
              <ul className="bulk-issues-list">
                {issues.map((it, i) => (
                  <li key={i} className={`bulk-issue bulk-issue--${it.kind}`}>
                    <strong>{it.file}</strong> — {it.text}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <div className="table-card">
          <div className="table-header-row">
            <div>
              <div className="table-title">הלקוחות לפי דחיפות ניוד</div>
              <div className="table-title-sub">לחץ על לקוח כדי לפתוח את הדוח המלא שלו</div>
            </div>
          </div>
          {visible.length === 0 ? (
            <div className="leaderboard-empty">
              {rows.length === 0 ? 'לא נמצאו בקבצים קופות גמל או השתלמות לניתוח' : 'אין לקוחות שתואמים לחיפוש'}
            </div>
          ) : (
            <div className="table-wrap">
              <table className="alts-table bulk-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>לקוח</th>
                    <th>צבירה</th>
                    <th>ציון תיק</th>
                    <th>רווח מניוד</th>
                    <th>המהלך הכדאי ביותר</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {visible.slice(0, limit).map((r, i) => {
                    const p = r.client.portfolio;
                    const score = p.weighted_score;
                    const color = scoreColor(score);
                    const urgent = i < 3 && r.upside > 0 && sortBy === 'upside';
                    return (
                      <tr key={clientKey(r.client)} className="row-alt bulk-row" onClick={() => onOpenClient(r.client)}>
                        <td>
                          <span className="rank-badge" style={{
                            background: urgent ? 'rgba(239,68,68,0.16)' : 'rgba(148,163,184,0.12)',
                            color: urgent ? '#EF4444' : 'var(--text-secondary)',
                          }}>
                            {i + 1}
                          </span>
                        </td>
                        <td className="td-name">
                          <div>{clientLabel(r.client)}</div>
                          {r.client.client_id && r.client.client_name && <div className="td-name-sub">ת״ז {r.client.client_id}</div>}
                          <div className="td-name-sub">{fundsCount(r.client.funds.length)} · {filesCount(r.client.files.length)}</div>
                        </td>
                        <td className="td-potential">₪{fmt(p.total_amount)}</td>
                        <td>
                          <span className="score-pill" style={{ color, background: `${color}1f`, borderColor: `${color}55` }}>
                            {score != null ? fmtDec(score) : '–'}
                          </span>
                          {p.potential_score != null && score != null && p.potential_score > score && (
                            <div className="td-name-sub">אחרי ניוד: {fmtDec(p.potential_score)}</div>
                          )}
                        </td>
                        <td className="bulk-upside">
                          {r.upside > 0 ? (
                            <>
                              <div className="bulk-upside-val">+₪{fmt(r.upside)}</div>
                              <div className="bulk-upside-bar"><div style={{ width: `${(r.upside / maxUpside) * 100}%` }} /></div>
                              <div className="td-name-sub">+{fmtDec(r.upsidePct, 2)}% מהצבירה</div>
                            </>
                          ) : (
                            <span className="td-name-sub">אין רווח מניוד</span>
                          )}
                        </td>
                        <td className="bulk-move">
                          {r.move ? (
                            <>
                              <div className="td-name-sub">{r.move.from.name}</div>
                              <div>← {r.move.to.name}</div>
                            </>
                          ) : '—'}
                        </td>
                        <td>
                          <button className="bulk-open-btn" onClick={e => { e.stopPropagation(); onOpenClient(r.client); }}>
                            פתח דוח
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {visible.length > limit && (
            <button className="file-list-more" onClick={() => setLimit(l => l + BULK_PAGE_SIZE)}>
              הצג עוד {Math.min(BULK_PAGE_SIZE, visible.length - limit).toLocaleString('he-IL')} לקוחות (מוצגים {limit.toLocaleString('he-IL')} מתוך {visible.length.toLocaleString('he-IL')})
            </button>
          )}
          <div className="table-footnote">
            רווח מניוד = כמה כסף היה ללקוח היום אילו עבר לפני {horizon.label} לחלופה הטובה ביותר לכל קופה
            ({includeGolden ? 'החלופה המובילה באותה רמת סיכון, או תפוח הזהב בסיכון גבוה' : 'רק חלופות באותה רמת סיכון'}),
            {' '}{feeMode === 'net' ? 'בניכוי דמי הניהול שלו' : 'ללא דמי ניהול בקופה החדשה'}.
            ציון תיק = ממוצע AmoScore של הקופות, משוקלל לפי הצבירה בכל קופה.
          </div>
        </div>

      </div>
    </div>
  );
}

// ─── Root App ─────────────────────────────────────────────────────────────────

function App() {
  const [screen, setScreen] = useState('upload');
  const [mode, setMode] = useState('single');
  const [mislakaFiles, setMislakaFiles] = useState([]);
  const [bulkFiles, setBulkFiles] = useState([]);
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [rawResults, setRawResults] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [bulkData, setBulkData] = useState(null);
  const [bulkClient, setBulkClient] = useState(null);
  const [feeMode, setFeeMode] = useState('net');
  const [sumSameFund, setSumSameFund] = useState(true);
  const [thresholds, setThresholds] = useState(DEFAULT_THRESHOLDS);
  const [geo, setGeo] = useState(DEFAULT_GEO);
  const [badHevrot, setBadHevrot] = useState(DEFAULT_BAD_HEVROT);
  const [overrideRiskLevel, setOverrideRiskLevel] = useState(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [loadingTitle, setLoadingTitle] = useState(undefined);
  const [viewingFile, setViewingFile] = useState(null);
  const [myProfile, setMyProfile] = useState(null);
  const [leaderboardData, setLeaderboardData] = useState([]);
  const [selectedProfileName, setSelectedProfileName] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem('amo-theme') || 'dark');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('amo-theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(t => t === 'dark' ? 'light' : 'dark');
  }, []);

  const results = useMemo(() => {
    if (!rawResults) return null;
    return sumSameFund ? aggregateResults(rawResults) : rawResults;
  }, [rawResults, sumSameFund]);

  const bulkClientResults = useMemo(() => {
    if (!bulkClient) return null;
    return sumSameFund ? aggregateResults(bulkClient.funds) : bulkClient.funds;
  }, [bulkClient, sumSameFund]);

  const handleRemoveMislakaFile = (idx) => {
    setMislakaFiles(prev => prev.filter((_, i) => i !== idx));
  };

  const handleRemoveBulkFile = (idx) => {
    setBulkFiles(prev => prev.filter((_, i) => i !== idx));
  };

  const handleViewFile = useCallback(async (file) => {
    const text = await file.text();
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(text, 'text/xml');
    setViewingFile({ doc: xmlDoc, name: file.name });
    setScreen('viewer');
  }, []);

  const handleExportWord = useCallback(() => {
    if (!viewingFile) return;

    function nodeToHtml(node, depth) {
      const children = Array.from(node.children || []);
      const hasChildren = children.length > 0;
      const textValue = !hasChildren && node.textContent ? node.textContent.trim() : null;
      const indent = depth * 20;
      const tag = `<span style="color:#1E40AF;font-family:Consolas,monospace;font-weight:600">${node.tagName}</span>`;
      const count = hasChildren ? ` <span style="color:#6B7280;font-size:11px">(${children.length})</span>` : '';
      const val = textValue ? ` <span style="color:#065F46;background:#D1FAE5;padding:1px 6px;border-radius:3px;font-family:Consolas,monospace">${textValue}</span>` : '';
      const bullet = hasChildren ? '▶ ' : '● ';
      let html = `<div style="padding-right:${indent}px;margin:2px 0;direction:rtl">${bullet}${tag}${count}${val}</div>`;
      if (hasChildren) {
        for (const child of children) html += nodeToHtml(child, depth + 1);
      }
      return html;
    }

    const treeHtml = nodeToHtml(viewingFile.doc.documentElement, 0);
    const docHtml = `
      <html xmlns:o="urn:schemas-microsoft-com:office:office"
            xmlns:w="urn:schemas-microsoft-com:office:word"
            xmlns="http://www.w3.org/TR/REC-html40">
      <head><meta charset="utf-8">
      <title>${viewingFile.name}</title>
      <style>
        body { font-family: Arial, sans-serif; direction: rtl; background: #fff; color: #111; padding: 24px; }
        h1 { font-size: 18px; color: #1E3A5F; margin-bottom: 16px; border-bottom: 2px solid #E2E8F0; padding-bottom: 8px; }
      </style>
      </head>
      <body>
        <h1>תצוגת קובץ XML — ${viewingFile.name}</h1>
        ${treeHtml}
      </body></html>`;

    const blob = new Blob(['\ufeff', docHtml], { type: 'application/msword' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = viewingFile.name.replace(/\.[^.]+$/, '') + '.doc';
    a.click();
    URL.revokeObjectURL(url);
  }, [viewingFile]);

  // Uploads `files` with the current settings to `endpoint`, animating the loading
  // screen until the response arrives, then hands the parsed JSON to `onDone`.
  const runAnalysis = async (endpoint, files, onDone, title) => {
    setScreen('loading');
    setLoadingTitle(title);
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
      formData.append('weight_liquidity', weights.wLiquidity);
      formData.append('low_exposure_threshold', thresholds.low);
      formData.append('medium_exposure_threshold', thresholds.medium);
      formData.append('israel_share_min', geo.min);
      formData.append('israel_share_max', geo.max);
      formData.append('client_id', 'amo_sight_user');
      files.forEach(f => formData.append('mislaka_file', f));
      badHevrot.forEach(h => formData.append('bad_hevrot', h));
      if (overrideRiskLevel) formData.append('override_risk_level', overrideRiskLevel);

      const res = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      clearInterval(interval);
      setProgress(100);
      setTimeout(() => onDone(data), 500);
    } catch (err) {
      clearInterval(interval);
      console.error(err);
      alert('שגיאה בניתוח הנתונים. אנא בדוק שהשרת פועל ונסה שוב.');
      setScreen('upload');
    }
  };

  const handleAnalyze = () => runAnalysis('/compare', mislakaFiles, (data) => {
    const funds = data.funds ?? data;
    setRawResults(Array.isArray(funds) ? funds : [funds]);
    setPortfolio(data.portfolio ?? null);
    setScreen('results');
  });

  const handleBulkAnalyze = () => runAnalysis('/compare/bulk', bulkFiles, (data) => {
    setBulkData(data);
    setBulkClient(null);
    setScreen('bulk-results');
  }, `מנתח ${bulkFiles.length.toLocaleString('he-IL')} קבצים...`);

  const screenContent = (() => {
    if (screen === 'loading') {
      return <LoadingScreen step={loadingStep} progress={progress} title={loadingTitle} />;
    }
    if (screen === 'results') {
      return (
        <ResultsScreen
          results={results}
          portfolio={portfolio}
          weights={weights}
          thresholds={thresholds}
          feeMode={feeMode}
          onFeeModeChange={setFeeMode}
          onReset={() => setScreen('upload')}
          onGoToInvite={() => setScreen('invite')}
        />
      );
    }
    if (screen === 'bulk-results' && bulkData) {
      return (
        <BulkResultsScreen
          data={bulkData}
          feeMode={feeMode}
          onFeeModeChange={setFeeMode}
          onBack={() => setScreen('upload')}
          onOpenClient={(client) => {
            setBulkClient(client);
            setScreen('bulk-client');
            window.scrollTo(0, 0);
          }}
        />
      );
    }
    if (screen === 'bulk-client' && bulkClient) {
      // No community invite here: the report belongs to one of the advisor's clients
      return (
        <ResultsScreen
          key={clientKey(bulkClient)}
          results={bulkClientResults}
          portfolio={bulkClient.portfolio}
          weights={weights}
          thresholds={thresholds}
          feeMode={feeMode}
          onFeeModeChange={setFeeMode}
          onReset={() => setScreen('bulk-results')}
          resetLabel="← חזרה לרשימת הלקוחות"
          subject={
            <>
              📋 דוח עבור <strong>{clientLabel(bulkClient)}</strong>
              {bulkClient.client_id && bulkClient.client_name && <> · ת״ז {bulkClient.client_id}</>}
              {' · '}{filesCount(bulkClient.files.length)}
            </>
          }
        />
      );
    }
    if (screen === 'invite') {
      return (
        <InviteScreen
          results={results}
          onBack={() => setScreen('results')}
          onJoined={async (profile) => {
            setMyProfile(profile);
            try {
              const res = await fetch('http://localhost:8000/community/leaderboard');
              const data = await res.json();
              setLeaderboardData(data.profiles || []);
            } catch (err) {
              console.error(err);
            }
            setScreen('leaderboard');
          }}
        />
      );
    }
    if (screen === 'leaderboard') {
      return (
        <LeaderboardScreen
          leaderboard={leaderboardData}
          myProfile={myProfile}
          onBack={() => setScreen('results')}
          onViewProfile={(fakeName) => {
            setSelectedProfileName(fakeName);
            setScreen('profile');
          }}
        />
      );
    }
    if (screen === 'profile') {
      return (
        <ProfileScreen
          fakeName={selectedProfileName}
          myProfile={myProfile}
          leaderboard={leaderboardData}
          onBack={() => setScreen('leaderboard')}
        />
      );
    }
    if (screen === 'viewer' && viewingFile) {
      return (
        <div className="screen screen--viewer">
    
          <div className="viewer-header">
            <button className="back-btn" onClick={() => setScreen('upload')}>→ חזרה</button>
            <h2>תצוגת קובץ XML</h2>
            <button className="export-word-btn" onClick={handleExportWord}>⬇ ייצא ל-Word</button>
          </div>
          <div className="viewer-card">
            <TreeNode node={viewingFile.doc.documentElement} depth={0} />
          </div>
        </div>
      );
    }
    return (
      <UploadScreen
        mode={mode}
        onModeChange={setMode}
        mislakaFiles={mislakaFiles}
        onMislakaFiles={setMislakaFiles}
        onRemoveMislakaFile={handleRemoveMislakaFile}
        bulkFiles={bulkFiles}
        onBulkFiles={setBulkFiles}
        onRemoveBulkFile={handleRemoveBulkFile}
        onViewFile={handleViewFile}
        weights={weights}
        onWeightsChange={setWeights}
        thresholds={thresholds}
        onThresholdsChange={setThresholds}
        geo={geo}
        onGeoChange={setGeo}
        sumSameFund={sumSameFund}
        onSumSameFundChange={setSumSameFund}
        badHevrot={badHevrot}
        onBadHevrotChange={setBadHevrot}
        overrideRiskLevel={overrideRiskLevel}
        onOverrideRiskLevelChange={setOverrideRiskLevel}
        onAnalyze={handleAnalyze}
        onBulkAnalyze={handleBulkAnalyze}
      />
    );
  })();

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {screenContent}
    </ThemeContext.Provider>
  );
}

export default App;
