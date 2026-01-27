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
    if (hash && ['overview', 'domestic', 'ic', 'methodology'].includes(hash)) {
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
 * Load dashboard data from JSON
 */
async function loadDashboardData() {
    DashboardState.isLoading = true;
    document.body.classList.add('loading');

    try {
        const response = await fetch(CONFIG.dataPath);
        if (!response.ok) {
            throw new Error(`Failed to load data: ${response.status}`);
        }
        DashboardState.data = await response.json();
        console.log('Data loaded:', DashboardState.data);
    } catch (error) {
        console.warn('Could not load data file, using demo data:', error.message);
        DashboardState.data = getDemoData();
    } finally {
        DashboardState.isLoading = false;
        document.body.classList.remove('loading');
    }
}

/**
 * Get demo data for development/preview
 */
function getDemoData() {
    return {
        generated_at: new Date().toISOString(),
        study_period: '2024-2025',
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
            headline: 'This dashboard presents flexibility data from 7 contributing organisations for the study period 2024-2025. Total available flexibility capacity is 2,450 MW.',
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
    updateElement('study-period', data.study_period || '2024-2025');

    // Update headline metrics
    updateElement('total-available', formatNumber(data.metrics.total_available_mw));
    updateElement('total-delivered', formatNumber(data.metrics.total_delivered_mw));
    updateElement('delivery-factor', `${formatNumber(data.metrics.delivery_factor_pct)}%`);
    updateElement('contributor-count', data.metrics.contributor_count);

    // Update sector metrics
    updateElement('domestic-available', formatNumber(data.metrics.domestic?.available_mw));
    updateElement('domestic-delivered', formatNumber(data.metrics.domestic?.delivered_mw));
    updateElement('ic-available', formatNumber(data.metrics.ic?.available_mw));
    updateElement('ic-delivered', formatNumber(data.metrics.ic?.delivered_mw));

    // Update domestic page
    updateElement('domestic-total-mw', formatNumber(data.metrics.domestic?.available_mw));
    updateElement('domestic-delivery-pct',
        `${formatNumber(calculateDeliveryFactor(data.metrics.domestic?.available_mw, data.metrics.domestic?.delivered_mw))}%`);

    // Update I&C page
    updateElement('ic-total-mw', formatNumber(data.metrics.ic?.available_mw));
    updateElement('ic-delivery-pct',
        `${formatNumber(calculateDeliveryFactor(data.metrics.ic?.available_mw, data.metrics.ic?.delivered_mw))}%`);

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
