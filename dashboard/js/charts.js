/**
 * FlexDash Chart Management
 *
 * Handles Chart.js visualization creation and updates
 */

// Chart color palette
const CHART_COLORS = {
    primary: '#2E86AB',
    secondary: '#A23B72',
    tertiary: '#F18F01',
    success: '#4CAF50',
    domestic: '#2E86AB',
    ic: '#A23B72',
    illustrative: '#FF9800',
    palette: [
        '#2E86AB', '#A23B72', '#F18F01', '#4CAF50',
        '#9C27B0', '#00BCD4', '#FF5722', '#607D8B'
    ]
};

// Chart default options
const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'bottom',
            labels: {
                padding: 20,
                usePointStyle: true
            }
        },
        tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: 12,
            titleFont: { size: 14, weight: 'bold' },
            bodyFont: { size: 13 },
            callbacks: {
                label: function(context) {
                    let label = context.dataset.label || context.label || '';
                    if (label) label += ': ';
                    if (context.parsed !== undefined) {
                        const value = context.parsed.y !== undefined ? context.parsed.y : context.parsed;
                        label += new Intl.NumberFormat('en-GB').format(value) + ' MW';
                    }
                    return label;
                }
            }
        }
    }
};

/**
 * Initialize all charts
 */
function initializeCharts() {
    const data = window.DashboardState?.data;
    if (!data) {
        console.warn('No data available for charts');
        return;
    }

    // Destroy existing charts
    Object.values(window.DashboardState.charts).flat().forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    window.DashboardState.charts = {};

    // Create charts
    createSectorChart(data);
    createAssetChart(data);
    createDomesticAssetChart(data);
    createICAssetChart(data);
}

/**
 * Create sector breakdown doughnut chart
 */
function createSectorChart(data) {
    const ctx = document.getElementById('sector-chart');
    if (!ctx) return;

    const sectorData = data.sector_breakdown || [];
    const labels = sectorData.map(d => formatLabelLocal(d.sector));
    const values = sectorData.map(d => d.capacity_mw);
    const illustrativeFlags = sectorData.map(d => d.capacity_mw_illustrative);

    // Check if any values are illustrative
    const hasIllustrative = illustrativeFlags.some(f => f);

    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [CHART_COLORS.domestic, CHART_COLORS.ic],
                borderColor: '#ffffff',
                borderWidth: 3,
                hoverOffset: 10
            }]
        },
        options: {
            ...CHART_DEFAULTS,
            cutout: '60%',
            plugins: {
                ...CHART_DEFAULTS.plugins,
                title: {
                    display: false
                },
                tooltip: {
                    ...CHART_DEFAULTS.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            const isIllustrative = illustrativeFlags[context.dataIndex];
                            let label = `${context.label}: ${new Intl.NumberFormat('en-GB').format(value)} MW (${percentage}%)`;
                            if (isIllustrative) label += ' [Illustrative]';
                            return label;
                        }
                    }
                }
            }
        }
    });

    // Update note
    const noteEl = document.getElementById('sector-note');
    if (noteEl && hasIllustrative) {
        noteEl.textContent = 'Some values are illustrative due to disclosure control.';
    }

    // Store chart reference
    if (!window.DashboardState.charts.overview) {
        window.DashboardState.charts.overview = [];
    }
    window.DashboardState.charts.overview.push(chart);
}

/**
 * Create asset class horizontal bar chart
 */
function createAssetChart(data) {
    const ctx = document.getElementById('asset-chart');
    if (!ctx) return;

    const assetData = data.asset_breakdown || [];

    // Sort by capacity descending
    const sorted = [...assetData].sort((a, b) => b.capacity_mw - a.capacity_mw);

    const labels = sorted.map(d => formatLabelLocal(d.asset_class));
    const values = sorted.map(d => d.capacity_mw);
    const illustrativeFlags = sorted.map(d => d.capacity_mw_illustrative);

    // Color bars based on illustrative status
    const colors = sorted.map((d, i) =>
        d.capacity_mw_illustrative ? CHART_COLORS.illustrative : CHART_COLORS.palette[i % CHART_COLORS.palette.length]
    );

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Capacity (MW)',
                data: values,
                backgroundColor: colors,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            ...CHART_DEFAULTS,
            indexAxis: 'y',
            plugins: {
                ...CHART_DEFAULTS.plugins,
                legend: { display: false },
                tooltip: {
                    ...CHART_DEFAULTS.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const isIllustrative = illustrativeFlags[context.dataIndex];
                            let label = `${new Intl.NumberFormat('en-GB').format(context.parsed.x)} MW`;
                            if (isIllustrative) label += ' [Illustrative]';
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: {
                        callback: value => new Intl.NumberFormat('en-GB').format(value)
                    }
                },
                y: {
                    grid: { display: false }
                }
            }
        }
    });

    // Update note
    const hasIllustrative = illustrativeFlags.some(f => f);
    const noteEl = document.getElementById('asset-note');
    if (noteEl && hasIllustrative) {
        noteEl.textContent = 'Orange bars indicate illustrative values.';
    }

    if (!window.DashboardState.charts.overview) {
        window.DashboardState.charts.overview = [];
    }
    window.DashboardState.charts.overview.push(chart);
}

/**
 * Create domestic asset breakdown chart
 */
function createDomesticAssetChart(data) {
    const ctx = document.getElementById('domestic-asset-chart');
    if (!ctx) return;

    const assetData = data.asset_breakdown || [];

    // Filter to domestic assets
    const domesticAssets = ['ev_charger', 'heat_pump', 'battery_storage', 'smart_hot_water', 'wet_appliances'];
    const filtered = assetData.filter(d =>
        domesticAssets.includes(d.asset_class?.toLowerCase())
    );

    if (filtered.length === 0) {
        // Use placeholder data
        filtered.push(
            { asset_class: 'ev_charger', capacity_mw: 650, capacity_mw_illustrative: false },
            { asset_class: 'heat_pump', capacity_mw: 350, capacity_mw_illustrative: true },
            { asset_class: 'battery_storage', capacity_mw: 200, capacity_mw_illustrative: false }
        );
    }

    const sorted = [...filtered].sort((a, b) => b.capacity_mw - a.capacity_mw);
    const labels = sorted.map(d => formatLabelLocal(d.asset_class));
    const values = sorted.map(d => d.capacity_mw);
    const colors = sorted.map((d, i) =>
        d.capacity_mw_illustrative ? CHART_COLORS.illustrative : CHART_COLORS.palette[i % CHART_COLORS.palette.length]
    );

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Capacity (MW)',
                data: values,
                backgroundColor: colors,
                borderRadius: 4
            }]
        },
        options: {
            ...CHART_DEFAULTS,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: {
                        callback: value => new Intl.NumberFormat('en-GB').format(value)
                    }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });

    if (!window.DashboardState.charts.domestic) {
        window.DashboardState.charts.domestic = [];
    }
    window.DashboardState.charts.domestic.push(chart);
}

/**
 * Create I&C asset breakdown chart
 */
function createICAssetChart(data) {
    const ctx = document.getElementById('ic-asset-chart');
    if (!ctx) return;

    const assetData = data.asset_breakdown || [];

    // Filter to I&C assets
    const icAssets = ['cold_storage', 'water_treatment', 'manufacturing', 'commercial_hvac', 'commercial_battery', 'backup_generation', 'ev_fleet'];
    const filtered = assetData.filter(d =>
        icAssets.includes(d.asset_class?.toLowerCase())
    );

    if (filtered.length === 0) {
        // Use placeholder data
        filtered.push(
            { asset_class: 'cold_storage', capacity_mw: 480, capacity_mw_illustrative: false },
            { asset_class: 'water_treatment', capacity_mw: 420, capacity_mw_illustrative: true },
            { asset_class: 'manufacturing', capacity_mw: 350, capacity_mw_illustrative: false }
        );
    }

    const sorted = [...filtered].sort((a, b) => b.capacity_mw - a.capacity_mw);
    const labels = sorted.map(d => formatLabelLocal(d.asset_class));
    const values = sorted.map(d => d.capacity_mw);
    const colors = sorted.map((d, i) =>
        d.capacity_mw_illustrative ? CHART_COLORS.illustrative : CHART_COLORS.palette[i % CHART_COLORS.palette.length]
    );

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Capacity (MW)',
                data: values,
                backgroundColor: colors,
                borderRadius: 4
            }]
        },
        options: {
            ...CHART_DEFAULTS,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: {
                        callback: value => new Intl.NumberFormat('en-GB').format(value)
                    }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });

    if (!window.DashboardState.charts.ic) {
        window.DashboardState.charts.ic = [];
    }
    window.DashboardState.charts.ic.push(chart);
}

/**
 * Format label helper
 */
function formatLabelLocal(label) {
    if (!label) return 'Unknown';
    return String(label)
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

// Export for use
window.initializeCharts = initializeCharts;
window.CHART_COLORS = CHART_COLORS;
