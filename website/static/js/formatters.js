/**
 * Formatting utilities for game development data.
 * Mirrors Python utils/formatters.py for client-side use.
 */

// ---------- Null Handling ----------

function safeValue(value, fallback = '—') {
    if (value === null || value === undefined || value === 'None' || value === 'null' || value === '') {
        return fallback;
    }
    if (typeof value === 'number' && isNaN(value)) {
        return fallback;
    }
    return value;
}

function safeNumber(value, fallback = '—') {
    const num = Number(value);
    if (isNaN(num) || value === null || value === undefined || value === '') {
        return fallback;
    }
    return num;
}

// ---------- Time Conversions ----------

function formatMonths(months, fallback = '—') {
    const val = safeNumber(months, fallback);
    if (typeof val === 'string') return val;
    
    const totalMonths = Math.floor(val);
    const years = Math.floor(totalMonths / 12);
    const remaining = totalMonths % 12;
    
    if (years === 0) {
        return `${remaining} month${remaining !== 1 ? 's' : ''}`;
    }
    if (remaining === 0) {
        return `${years} year${years !== 1 ? 's' : ''}`;
    }
    return `${years} year${years !== 1 ? 's' : ''} ${remaining} month${remaining !== 1 ? 's' : ''}`;
}

function formatMonthsShort(months, fallback = '—') {
    const val = safeNumber(months, fallback);
    if (typeof val === 'string') return val;
    
    const totalMonths = Math.floor(val);
    const years = Math.floor(totalMonths / 12);
    const remaining = totalMonths % 12;
    
    if (years === 0) return `${remaining}mo`;
    if (remaining === 0) return `${years}y`;
    return `${years}y ${remaining}mo`;
}

// ---------- File Size Conversions ----------

function formatFileSize(mb, fallback = '—') {
    const val = safeNumber(mb, fallback);
    if (typeof val === 'string') return val;
    
    if (val < 1024) {
        return `${Math.floor(val)} MB`;
    }
    
    const gb = val / 1024;
    return `${gb.toFixed(2)} GB`;
}

// ---------- Budget Formatting ----------

function formatBudget(usd, fallback = '—') {
    const val = safeNumber(usd, fallback);
    if (typeof val === 'string') return val;
    
    if (val >= 1_000_000_000) {
        const billions = val / 1_000_000_000;
        const formatted = billions % 1 === 0 ? billions.toString() : billions.toFixed(1);
        return `$${formatted}B`;
    }
    
    if (val >= 1_000_000) {
        const millions = val / 1_000_000;
        const formatted = millions % 1 === 0 ? millions.toString() : millions.toFixed(1);
        return `$${formatted}M`;
    }
    
    if (val >= 1_000) {
        return `$${Math.round(val).toLocaleString()}`;
    }
    
    return `$${val}`;
}

// ---------- Score & Team Size ----------

function formatScore(score, fallback = '—') {
    const val = safeNumber(score, fallback);
    if (typeof val === 'string') return val;
    return Math.round(val).toString();
}

function formatTeamSize(size, fallback = '—') {
    const val = safeNumber(size, fallback);
    if (typeof val === 'string') return val;
    return Math.round(val).toString();
}