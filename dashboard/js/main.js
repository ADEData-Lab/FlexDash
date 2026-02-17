/**
 * FlexDash Main Dashboard Controller
 *
 * Handles:
 * - Page navigation
 * - Data loading
 * - UI updates
 * - Event handling
 */

// Dashboard state
const DashboardState = {
    currentPage: 'overview',
    data: null,
    charts: {},
    isLoading: false
};

// Configuration
const CONFIG = {
    dataPath: 'data/dashboard_data.json',
    refreshInterval: null, // Set to milliseconds for auto-refresh
    formatOptions: {
        locale: 'en-GB',
        maximumFractionDigits: 0
    }
};

/**
 * Initialize the dashboard
 */
async function initDashboard() {
    console.log('Initializing FlexDash...');

    // Set up theme
    setupTheme();

    // Set up navigation
    setupNavigation();

    // Load data
    await loadDashboardData();

    // Initialize charts (if data loaded)
    if (DashboardState.data) {
        initializeCharts();
        updateUI();
    }

    console.log('FlexDash initialized');
}

/**
 * Set up theme selector and load saved preference
 */
function setupTheme() {
    const themeSelect = document.getElementById('theme-select');
    if (!themeSelect) return;

    // Load saved theme or default to 'dashboard-dark'
    const savedTheme = localStorage.getItem('flexdash-theme') || 'dashboard-dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    themeSelect.value = savedTheme;

    // Handle theme changes
    themeSelect.addEventListener('change', (e) => {
        const theme = e.target.value;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('flexdash-theme', theme);

        // Reinitialize charts with new colors
        if (DashboardState.data) {
            updateChartColors();
        }
    });
}

/**
 * Update chart colors when theme changes
 */
function updateChartColors() {
    // Get computed styles for current theme
    const styles = getComputedStyle(document.documentElement);
    const domesticColor = styles.getPropertyValue('--chart-domestic').trim() || '#45c3d3';
    const icColor = styles.getPropertyValue('--chart-ic').trim() || '#6eb43f';
    const illustrativeColor = styles.getPropertyValue('--chart-illustrative').trim() || '#eb8800';

    // Update CHART_COLORS
    if (window.CHART_COLORS) {
        window.CHART_COLORS.domestic = domesticColor;
        window.CHART_COLORS.ic = icColor;
        window.CHART_COLORS.illustrative = illustrativeColor;
        window.CHART_COLORS.primary = domesticColor;
        window.CHART_COLORS.secondary = icColor;
        window.CHART_COLORS.tertiary = illustrativeColor;
    }

    // Reinitialize charts
    if (typeof initializeCharts === 'function') {
        initializeCharts();
    }
}

/**
 * Set up navigation event handlers
 */
function setupNavigation() {
    // Handle nav link clicks
    document.querySelectorAll('.nav-link, .sector-link, [data-page]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.dataset.page || link.getAttribute('href').replace('#', '');
            navigateToPage(page);
        });
    });

    // Handle browser back/forward
    window.addEventListener('popstate', (e) => {
        const page = e.state?.page || 'overview';
        navigateToPage(page, false);
    });

    // Check URL hash on load
    const hash = window.location.hash.replace('#', '');
    if (hash && ['overview', 'domestic', 'ic', 'benchmarks', 'projections', 'methodology'].includes(hash)) {
        navigateToPage(hash, false);
    }
}

/**
 * Navigate to a page
 */
function navigateToPage(pageId, pushState = true) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });

    // Show target page
    const targetPage = document.getElementById(pageId);
    if (targetPage) {
        targetPage.classList.add('active');
    }

    // Update nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.page === pageId);
    });

    // Update state
    DashboardState.currentPage = pageId;

    // Update URL
    if (pushState) {
        history.pushState({ page: pageId }, '', `#${pageId}`);
    }

    // Refresh charts if needed
    if (DashboardState.charts[pageId]) {
        DashboardState.charts[pageId].forEach(chart => chart.update());
    }

    // Scroll to top
    window.scrollTo(0, 0);
}

/**
 * Load dashboard data from JSON or embedded data
 */
async function loadDashboardData() {
    DashboardState.isLoading = true;
    document.body.classList.add('loading');

    try {
        const isFileProtocol = window.location.protocol === 'file:';

        // Prefer embedded data for local file:// access (fetch is typically blocked)
        if (isFileProtocol && typeof DASHBOARD_DATA !== 'undefined') {
            console.log('Using embedded dashboard data');
            DashboardState.data = DASHBOARD_DATA;
        } else {
            // Fall back to fetching JSON file (works on web server)
            try {
                const response = await fetch(CONFIG.dataPath, { cache: 'no-store' });
                if (!response.ok) {
                    throw new Error(`Failed to load data: ${response.status}`);
                }
                DashboardState.data = await response.json();
                console.log('Data loaded from JSON file');
            } catch (fetchError) {
                // If serving a static build without pipeline outputs, fall back to embedded data.
                if (typeof DASHBOARD_DATA !== 'undefined') {
                    console.warn('Falling back to embedded dashboard data:', fetchError.message);
                    DashboardState.data = DASHBOARD_DATA;
                } else {
                    throw fetchError;
                }
            }
        }
        console.log('Dashboard data:', DashboardState.data);

        // Check if this is demonstration data and show banner
        checkDemoBanner(DashboardState.data);
    } catch (error) {
        console.warn('Could not load data, using demo data:', error.message);
        DashboardState.data = getDemoData();
        checkDemoBanner(DashboardState.data);
    } finally {
        DashboardState.isLoading = false;
        document.body.classList.remove('loading');
    }
}

/**
 * Check if data is demonstration/synthetic and show banner accordingly
 */
function checkDemoBanner(data) {
    const banner = document.getElementById('demo-banner');
    if (!banner) return;

    // Show banner if is_demo flag is set or if subtitle contains "DEMONSTRATION"
    const isDemo = data?.is_demo ||
                   data?.subtitle?.toLowerCase().includes('demonstration') ||
                   data?.subtitle?.toLowerCase().includes('synthetic');

    if (isDemo) {
        banner.style.display = 'block';
    }
}

/**
 * Get demo data for development/preview
 */
function getDemoData() {
    return {
        generated_at: new Date().toISOString(),
        study_period: 'Nov 2024–Feb 2025',
        metrics: {
            total_available_mw: 2450,
            total_delivered_mw: 980,
            delivery_factor_pct: 40,
            contributor_count: 7,
            domestic: {
                available_mw: 1200,
                delivered_mw: 520
            },
            ic: {
                available_mw: 1250,
                delivered_mw: 460
            }
        },
        sector_breakdown: [
            { sector: 'domestic', capacity_mw: 1200, capacity_mw_illustrative: false },
            { sector: 'ic', capacity_mw: 1250, capacity_mw_illustrative: false }
        ],
        asset_breakdown: [
            { asset_class: 'ev_charger', capacity_mw: 650, capacity_mw_illustrative: false },
            { asset_class: 'heat_pump', capacity_mw: 350, capacity_mw_illustrative: true },
            { asset_class: 'battery_storage', capacity_mw: 200, capacity_mw_illustrative: false },
            { asset_class: 'cold_storage', capacity_mw: 480, capacity_mw_illustrative: false },
            { asset_class: 'water_treatment', capacity_mw: 420, capacity_mw_illustrative: true },
            { asset_class: 'manufacturing', capacity_mw: 350, capacity_mw_illustrative: false }
        ],
        narratives: {
            headline: 'This dashboard presents flexibility data from 7 contributing organisations for the study period Nov 2024–Feb 2025. Total available flexibility capacity is 2,450 MW.',
            sector: 'Domestic flexibility accounts for 49% of total capacity (1,200 MW), with I&C contributing 51% (1,250 MW).',
            coverage: 'Data for this dashboard was provided by 7 organisations. Where fewer than 3 contributors exist for a metric, illustrative values are shown to protect commercial confidentiality.'
        },
        data_quality: {
            total_submissions: 7,
            valid_submissions: 7,
            validation_rate: 1.0,
            average_completeness: 0.85
        },
        colors: {
            domestic: '#2E86AB',
            ic: '#A23B72',
            illustrative: '#FF9800'
        }
    };
}

/**
 * Update UI with loaded data
 */
function updateUI() {
    const data = DashboardState.data;
    if (!data) return;

    // Update study period
    updateElement('study-period', data.study_period || 'Nov 2024-Feb 2025');

    // Update headline metrics (use ranges when published values are illustrative)
    const totalBadge = document.getElementById('total-available-badge');
    if (data.metrics.total_available_mw_illustrative && data.metrics.total_available_range) {
        updateElement('total-available', data.metrics.total_available_range);
        updateElement('total-available-badge', 'Range');
        if (totalBadge) totalBadge.classList.add('illustrative');
    } else {
        updateElement('total-available', formatNumber(data.metrics.total_available_mw));
        updateElement('total-available-badge', '');
        if (totalBadge) totalBadge.classList.remove('illustrative');
    }
    updateElement('contributor-count', data.metrics.contributor_count);

    // Methodology v7: Delivered MW (ranges when illustrative)
    const deliveredBadge = document.getElementById('total-delivered-badge');
    if (data.metrics.total_delivered_mw_illustrative && data.metrics.total_delivered_range) {
        updateElement('total-delivered', data.metrics.total_delivered_range);
        updateElement('total-delivered-badge', 'Range');
        if (deliveredBadge) deliveredBadge.classList.add('illustrative');
    } else if (data.metrics.total_delivered_mw > 0) {
        updateElement('total-delivered', formatNumber(data.metrics.total_delivered_mw));
        updateElement('total-delivered-badge', '');
        if (deliveredBadge) deliveredBadge.classList.remove('illustrative');
    }
    if (data.metrics.delivery_factor_pct > 0) {
        updateElement('delivery-factor', `${formatNumber(data.metrics.delivery_factor_pct)}%`);
        const factorEl = document.getElementById('delivery-factor');
        if (factorEl) factorEl.classList.remove('not-available');
    }

    // Update sector metrics
    if (data.metrics.domestic?.available_mw_illustrative && data.metrics.domestic?.available_range) {
        updateElement('domestic-available', data.metrics.domestic.available_range);
    } else {
        updateElement('domestic-available', formatNumber(data.metrics.domestic?.available_mw));
    }
    if (data.metrics.ic?.available_mw_illustrative && data.metrics.ic?.available_range) {
        updateElement('ic-available', data.metrics.ic.available_range);
    } else {
        updateElement('ic-available', formatNumber(data.metrics.ic?.available_mw));
    }

    if (data.metrics.domestic?.delivered_mw > 0) {
        updateElement('domestic-delivered', formatNumber(data.metrics.domestic?.delivered_mw));
        const domDeliveredEl = document.getElementById('domestic-delivered');
        if (domDeliveredEl) domDeliveredEl.classList.remove('not-available');
    }
    if (data.metrics.ic?.delivered_mw > 0) {
        updateElement('ic-delivered', formatNumber(data.metrics.ic?.delivered_mw));
        const icDeliveredEl = document.getElementById('ic-delivered');
        if (icDeliveredEl) icDeliveredEl.classList.remove('not-available');
    }

    // Update domestic page
    if (data.metrics.domestic?.available_mw_illustrative && data.metrics.domestic?.available_range) {
        updateElement('domestic-total-mw', data.metrics.domestic.available_range);
    } else {
        updateElement('domestic-total-mw', formatNumber(data.metrics.domestic?.available_mw));
    }

    // Update I&C page
    if (data.metrics.ic?.available_mw_illustrative && data.metrics.ic?.available_range) {
        updateElement('ic-total-mw', data.metrics.ic.available_range);
    } else {
        updateElement('ic-total-mw', formatNumber(data.metrics.ic?.available_mw));
    }

    // Update narratives
    if (data.narratives) {
        updateElement('narrative-headline', data.narratives.headline);
        updateElement('narrative-domestic', data.narratives.domestic || document.getElementById('narrative-domestic')?.textContent);
        updateElement('narrative-ic', data.narratives.ic || document.getElementById('narrative-ic')?.textContent);
    }

    // Update quality metrics
    if (data.data_quality) {
        updateElement('quality-contributors', data.data_quality.total_submissions);
        updateElement('quality-validation', `${formatNumber(data.data_quality.validation_rate * 100)}%`);
        updateElement('quality-completeness', `${formatNumber(data.data_quality.average_completeness * 100)}%`);
    }

    // Update last updated
    updateElement('last-updated', formatDate(data.generated_at));

    // Methodology v7: Update new metrics
    updateV7Metrics(data);

    // Benchmarks tab (external sense-checks)
    updateBenchmarks(data);
}

/**
 * Update Methodology v7 specific metrics
 */
function updateV7Metrics(data) {
    const formatRangeGW = (minMw, maxMw) => {
        if (minMw === null || minMw === undefined || maxMw === null || maxMw === undefined) return '--';
        const minGw = minMw / 1000;
        const maxGw = maxMw / 1000;
        const decimals = maxGw < 1 ? 2 : 1;
        return `${minGw.toFixed(decimals)}-${maxGw.toFixed(decimals)}`;
    };

    // Energy metrics (GWh) - supports illustrative ranges
    const setEnergy = (id, metricObj) => {
        if (!metricObj) return updateElement(id, '--');
        if (metricObj.delivered_gwh_illustrative && metricObj.delivered_range) {
            return updateElement(id, metricObj.delivered_range);
        }
        if (metricObj.delivered_gwh !== undefined && metricObj.delivered_gwh !== null) {
            return updateElement(id, formatNumber(metricObj.delivered_gwh));
        }
        return updateElement(id, '--');
    };

    if (data.energy_metrics) {
        setEnergy('total-available-gwh', data.energy_metrics.total); // optional element
        setEnergy('total-delivered-gwh', data.energy_metrics.total);
        setEnergy('explicit-gwh', data.energy_metrics.explicit);
        setEnergy('implicit-gwh', data.energy_metrics.implicit);
    } else {
        ['total-available-gwh', 'total-delivered-gwh', 'explicit-gwh', 'implicit-gwh'].forEach(id => updateElement(id, '--'));
    }

    // Coverage cues (contributors supplying each metric)
    if (data.coverage) {
        const total = data.coverage.contributors_total ?? data.metrics?.contributor_count ?? 0;
        const fmt = (n) => (total ? `${n}/${total}` : String(n));
        updateElement('coverage-capacity-mw', fmt(data.coverage.capacity_mw_contributors ?? 0));
        updateElement('coverage-delivered-mw', fmt(data.coverage.delivered_mw_contributors ?? 0));
        updateElement('coverage-explicit-energy', fmt(data.coverage.explicit_energy_contributors ?? 0));
        updateElement('coverage-implicit-energy', fmt(data.coverage.implicit_energy_contributors ?? 0));
        updateElement('coverage-note', `Values are range-bucketed when contributors < ${data.coverage.k_threshold ?? 3}.`);
    } else {
        ['coverage-capacity-mw', 'coverage-delivered-mw', 'coverage-explicit-energy', 'coverage-implicit-energy'].forEach(id => updateElement(id, '--'));
    }

    // Utilisation rate
    if (data.utilisation) {
        updateElement('utilisation-rate', `~${data.utilisation.overall_rate_pct}%`);
        updateElement('utilisation-note', data.utilisation.overall_rate_note);
    } else {
        updateElement('utilisation-rate', '--');
        updateElement('utilisation-note', '');
    }

    // Directional breakdown
    if (data.directional_breakdown) {
        const up = data.directional_breakdown.turn_up;
        const down = data.directional_breakdown.turn_down;

        if (up?.capacity_mw_illustrative && up.capacity_range_min != null && up.capacity_range_max != null) {
            updateElement('turn-up-gw', formatRangeGW(up.capacity_range_min, up.capacity_range_max));
        } else if (up?.capacity_mw != null) {
            updateElement('turn-up-gw', (up.capacity_mw / 1000).toFixed(1));
        } else {
            updateElement('turn-up-gw', '--');
        }

        if (down?.capacity_mw_illustrative && down.capacity_range_min != null && down.capacity_range_max != null) {
            updateElement('turn-down-gw', formatRangeGW(down.capacity_range_min, down.capacity_range_max));
        } else if (down?.capacity_mw != null) {
            updateElement('turn-down-gw', (down.capacity_mw / 1000).toFixed(1));
        } else {
            updateElement('turn-down-gw', '--');
        }

        updateElement('asymmetry-note', data.directional_breakdown.asymmetry_explanation);
    } else {
        updateElement('turn-up-gw', '--');
        updateElement('turn-down-gw', '--');
        updateElement('asymmetry-note', '');
    }

    // Flexibility type breakdown
    if (data.flexibility_type_breakdown) {
        const explicit = data.flexibility_type_breakdown.explicit;
        const implicit = data.flexibility_type_breakdown.implicit;

        if (explicit?.capacity_mw_illustrative && explicit.capacity_range_min != null && explicit.capacity_range_max != null) {
            updateElement('explicit-gw', formatRangeGW(explicit.capacity_range_min, explicit.capacity_range_max));
        } else if (explicit?.capacity_mw != null) {
            updateElement('explicit-gw', (explicit.capacity_mw / 1000).toFixed(1));
        } else {
            updateElement('explicit-gw', '--');
        }

        if (implicit?.capacity_mw_illustrative && implicit.capacity_range_min != null && implicit.capacity_range_max != null) {
            updateElement('implicit-gw', formatRangeGW(implicit.capacity_range_min, implicit.capacity_range_max));
        } else if (implicit?.capacity_mw != null) {
            updateElement('implicit-gw', (implicit.capacity_mw / 1000).toFixed(1));
        } else {
            updateElement('implicit-gw', '--');
        }
    } else {
        updateElement('explicit-gw', '--');
        updateElement('implicit-gw', '--');
    }

    // Latent potential
    if (data.latent_potential) {
        updateElement('latent-total-gw', data.latent_potential.total_gw.toFixed(1));
    } else {
        updateElement('latent-total-gw', '--');
    }

    // Current observed (for projections page)
    const currentGW = (data.metrics?.total_available_mw || 0) / 1000;
    const contributorCount = data.metrics?.contributor_count || 0;
    updateElement('current-observed-gw', `${currentGW.toFixed(1)} GW`);
    updateElement('current-observed-contributors', `From ${contributorCount} contributors`);

    // Future projections
    if (data.future_potential) {
        updateElement('future-2030-gw', data.future_potential['2030'].central_gw);
        updateElement('future-2030-range', `${data.future_potential['2030'].range_min_gw}-${data.future_potential['2030'].range_max_gw}`);
        updateElement('future-2050-gw', data.future_potential['2050'].central_gw);
        updateElement('future-2050-range', `${data.future_potential['2050'].range_min_gw}-${data.future_potential['2050'].range_max_gw}`);

        // Update progress bar to 2030 target
        const currentGW = data.metrics.total_available_mw / 1000;
        const target2030 = data.future_potential['2030'].central_gw;
        const progressPct = Math.min((currentGW / target2030) * 100, 100).toFixed(0);
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progressPct}%`;
            const label = progressBar.querySelector('.progress-label');
            if (label) label.textContent = `${progressPct}%`;
        }
        const progressContext = document.querySelector('.progress-context');
        if (progressContext) {
            const spans = progressContext.querySelectorAll('span');
            if (spans[0]) spans[0].textContent = `${currentGW.toFixed(1)} GW observed`;
            if (spans[1]) spans[1].textContent = `${target2030} GW target (2030)`;
        }
    } else {
        ['future-2030-gw', 'future-2030-range', 'future-2050-gw', 'future-2050-range'].forEach(id => updateElement(id, '--'));
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = `0%`;
            const label = progressBar.querySelector('.progress-label');
            if (label) label.textContent = ``;
        }
        const progressContext = document.querySelector('.progress-context');
        if (progressContext) {
            const spans = progressContext.querySelectorAll('span');
            if (spans[0]) spans[0].textContent = ``;
            if (spans[1]) spans[1].textContent = ``;
        }
    }
}

/**
 * Update Benchmarks / Sense-checks tab
 */
function updateBenchmarks(data) {
    const b = data?.benchmarks;
    if (!b) return;

    updateElement('cm-dy', b.dy || '2024/25');

    const nonAddEl = document.getElementById('benchmarks-nonadditivity');
    if (nonAddEl && b.non_additivity_notice) {
        nonAddEl.innerHTML = `<strong>Benchmark only.</strong> ${b.non_additivity_notice}`;
    }

    const methodsEl = document.getElementById('benchmarks-methods');
    if (methodsEl && b.methods_summary) {
        methodsEl.textContent = String(b.methods_summary).trim();
    }

    // Sources list
    const sourcesEl = document.getElementById('benchmark-sources');
    if (sourcesEl) {
        sourcesEl.innerHTML = '';
        (b.sources || []).forEach(src => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = src.url || '#';
            a.textContent = src.name || src.url || 'Source';
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            li.appendChild(a);
            sourcesEl.appendChild(li);
        });
        if ((b.sources || []).length === 0) {
            const li = document.createElement('li');
            li.textContent = 'Sources not available in this build.';
            sourcesEl.appendChild(li);
        }
    }

    // Comparison table
    const tbody = document.getElementById('benchmark-table-body');
    if (!tbody) return;

    const rows = b.comparison || [];
    tbody.innerHTML = '';

    if (!rows.length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 5;
        td.textContent = 'No benchmark data available.';
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    const fmtMW = (kw) => {
        const mw = (Number(kw) || 0) / 1000;
        return new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 }).format(mw);
    };

    const fmtDeltaMW = (kw) => {
        const mw = (Number(kw) || 0) / 1000;
        const sign = mw > 0 ? '+' : '';
        return sign + new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 }).format(mw);
    };

    const fmtPct = (p) => {
        if (p === null || p === undefined || isNaN(p)) return '';
        return (Number(p) * 100).toFixed(1) + '%';
    };

    rows.forEach(r => {
        const tr = document.createElement('tr');

        const category = String(r.asset_class || '');

        const contribIllustrative = Boolean(r.contributors_illustrative);
        const contribRange = r.contributors_range ? String(r.contributors_range) : null;
        const contribDisplay = contribIllustrative && contribRange ? contribRange : fmtMW(r.contributors_kw);

        const cmDisplay = fmtMW(r.cm_benchmark_kw);
        const deltaDisplay = fmtDeltaMW(r.variance_kw);
        const pctDisplay = fmtPct(r.variance_pct);

        const tdCat = document.createElement('td');
        tdCat.textContent = category;
        tr.appendChild(tdCat);

        const tdContrib = document.createElement('td');
        tdContrib.textContent = contribDisplay;
        if (contribIllustrative) tdContrib.classList.add('illustrative-value');
        tdContrib.title = `k=${r.contributors_k ?? ''}${contribRange ? `; range=${contribRange}` : ''}`;
        tr.appendChild(tdContrib);

        const tdCm = document.createElement('td');
        tdCm.textContent = cmDisplay;
        tr.appendChild(tdCm);

        const tdDelta = document.createElement('td');
        tdDelta.textContent = deltaDisplay;
        tr.appendChild(tdDelta);

        const tdPct = document.createElement('td');
        tdPct.textContent = pctDisplay;
        tr.appendChild(tdPct);

        tbody.appendChild(tr);
    });
}

/**
 * Update element text content safely
 */
function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el && value !== undefined && value !== null) {
        el.textContent = value;
    }
}

/**
 * Format number with locale
 */
function formatNumber(value) {
    if (value === undefined || value === null || isNaN(value)) return '--';
    return new Intl.NumberFormat(CONFIG.formatOptions.locale, {
        maximumFractionDigits: CONFIG.formatOptions.maximumFractionDigits
    }).format(value);
}

/**
 * Format date
 */
function formatDate(dateString) {
    if (!dateString) return '--';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-GB', {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
    } catch {
        return dateString;
    }
}

/**
 * Calculate delivery factor
 */
function calculateDeliveryFactor(available, delivered) {
    if (!available || available === 0) return 0;
    return Math.min((delivered / available) * 100, 100);
}

/**
 * Format label for display
 */
function formatLabel(label) {
    if (!label) return 'Unknown';
    return String(label)
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initDashboard);

// Export for other modules
window.DashboardState = DashboardState;
window.formatNumber = formatNumber;
window.formatLabel = formatLabel;
window.updateV7Metrics = updateV7Metrics;
window.setupTheme = setupTheme;
window.updateChartColors = updateChartColors;
