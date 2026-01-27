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
 * Create asset class horizontal bar chart with range support and log scale
 */
function createAssetChart(data) {
    const ctx = document.getElementById('asset-chart');
    if (!ctx) return;

    const assetData = data.asset_breakdown || [];

    // Sort by capacity descending (use midpoint for illustrative)
    const sorted = [...assetData].sort((a, b) => {
        const aVal = a.capacity_mw_illustrative && a.capacity_range_max ?
            (a.capacity_range_min + a.capacity_range_max) / 2 : a.capacity_mw;
        const bVal = b.capacity_mw_illustrative && b.capacity_range_max ?
            (b.capacity_range_min + b.capacity_range_max) / 2 : b.capacity_mw;
        return bVal - aVal;
    });

    // Use display_name if available, otherwise format asset_class
    const labels = sorted.map(d => {
        let label = d.display_name || formatLabelLocal(d.asset_class);
        if (d.capacity_mw_illustrative && d.capacity_range) {
            label += ` [${d.capacity_range}]`;
        }
        return label;
    });

    // For chart display, use actual value or midpoint of range
    // Add small offset for log scale (can't have 0)
    const values = sorted.map(d => {
        let val;
        if (d.capacity_mw_illustrative && d.capacity_range_max) {
            val = (d.capacity_range_min + d.capacity_range_max) / 2;
        } else {
            val = d.capacity_mw;
        }
        return Math.max(val, 1); // Minimum 1 for log scale
    });

    const illustrativeFlags = sorted.map(d => d.capacity_mw_illustrative);
    const ranges = sorted.map(d => d.capacity_range);
    const includes = sorted.map(d => d.includes || []);
    const kValues = sorted.map(d => d.k);

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
                        title: function(context) {
                            const idx = context[0].dataIndex;
                            const name = sorted[idx].display_name || formatLabelLocal(sorted[idx].asset_class);
                            return name;
                        },
                        label: function(context) {
                            const idx = context.dataIndex;
                            const isIllustrative = illustrativeFlags[idx];
                            const range = ranges[idx];
                            const k = kValues[idx];

                            if (isIllustrative && range) {
                                return `Range: ${range} (k=${k})`;
                            }
                            return `${new Intl.NumberFormat('en-GB').format(sorted[idx].capacity_mw)} MW (k=${k})`;
                        },
                        afterLabel: function(context) {
                            const idx = context.dataIndex;
                            const inc = includes[idx];
                            if (inc && inc.length > 0) {
                                return 'Includes: ' + inc.join(', ');
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'logarithmic',
                    min: 1,
                    max: 20000,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: {
                        callback: function(value) {
                            if (value === 1) return '1';
                            if (value === 10) return '10';
                            if (value === 100) return '100';
                            if (value === 1000) return '1,000';
                            if (value === 10000) return '10,000';
                            return '';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Capacity (MW) - Log Scale'
                    }
                },
                y: {
                    grid: { display: false }
                }
            }
        }
    });

    // Update note with legend
    const noteEl = document.getElementById('asset-note');
    if (noteEl) {
        noteEl.innerHTML = '<strong>Blue/green bars:</strong> Real data (k\u22653) &nbsp; <strong style="color:#FF9800">Orange bars:</strong> Range estimates (k<3)';
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

    // Filter to domestic assets (by sector or asset class)
    const filtered = assetData.filter(d =>
        d.sector === 'domestic' || d.sector === 'mixed' ||
        ['ev_charging', 'heat_pumps', 'battery_storage', 'other_domestic'].includes(d.asset_class)
    );

    if (filtered.length === 0) return;

    // Sort by capacity, using midpoint for ranges
    const sorted = [...filtered].sort((a, b) => {
        const aVal = a.capacity_mw_illustrative && a.capacity_range_max ?
            (a.capacity_range_min + a.capacity_range_max) / 2 : a.capacity_mw;
        const bVal = b.capacity_mw_illustrative && b.capacity_range_max ?
            (b.capacity_range_min + b.capacity_range_max) / 2 : b.capacity_mw;
        return bVal - aVal;
    });

    const labels = sorted.map(d => {
        let label = d.display_name || formatLabelLocal(d.asset_class);
        if (d.capacity_mw_illustrative && d.capacity_range) {
            label += ` [${d.capacity_range}]`;
        }
        return label;
    });

    const values = sorted.map(d => {
        if (d.capacity_mw_illustrative && d.capacity_range_max) {
            return Math.max((d.capacity_range_min + d.capacity_range_max) / 2, 1);
        }
        return Math.max(d.capacity_mw, 1);
    });

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
                legend: { display: false },
                tooltip: {
                    ...CHART_DEFAULTS.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const d = sorted[context.dataIndex];
                            if (d.capacity_mw_illustrative && d.capacity_range) {
                                return `Range: ${d.capacity_range} (k=${d.k})`;
                            }
                            return `${new Intl.NumberFormat('en-GB').format(d.capacity_mw)} MW (k=${d.k})`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'logarithmic',
                    min: 1,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: {
                        callback: function(value) {
                            if ([1, 10, 100, 1000, 10000].includes(value)) {
                                return new Intl.NumberFormat('en-GB').format(value);
                            }
                            return '';
                        }
                    },
                    title: { display: true, text: 'MW (log scale)' }
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

    // Filter to I&C assets (by sector or asset class)
    const filtered = assetData.filter(d =>
        d.sector === 'ic' ||
        ['ic_process_loads', 'ic_aggregated'].includes(d.asset_class)
    );

    if (filtered.length === 0) return;

    // Sort by capacity, using midpoint for ranges
    const sorted = [...filtered].sort((a, b) => {
        const aVal = a.capacity_mw_illustrative && a.capacity_range_max ?
            (a.capacity_range_min + a.capacity_range_max) / 2 : a.capacity_mw;
        const bVal = b.capacity_mw_illustrative && b.capacity_range_max ?
            (b.capacity_range_min + b.capacity_range_max) / 2 : b.capacity_mw;
        return bVal - aVal;
    });

    const labels = sorted.map(d => {
        let label = d.display_name || formatLabelLocal(d.asset_class);
        if (d.capacity_mw_illustrative && d.capacity_range) {
            label += ` [${d.capacity_range}]`;
        }
        return label;
    });

    const values = sorted.map(d => {
        if (d.capacity_mw_illustrative && d.capacity_range_max) {
            return Math.max((d.capacity_range_min + d.capacity_range_max) / 2, 1);
        }
        return Math.max(d.capacity_mw, 1);
    });

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
                legend: { display: false },
                tooltip: {
                    ...CHART_DEFAULTS.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const d = sorted[context.dataIndex];
                            if (d.capacity_mw_illustrative && d.capacity_range) {
                                return `Range: ${d.capacity_range} (k=${d.k})`;
                            }
                            return `${new Intl.NumberFormat('en-GB').format(d.capacity_mw)} MW (k=${d.k})`;
                        },
                        afterLabel: function(context) {
                            const d = sorted[context.dataIndex];
                            if (d.includes && d.includes.length > 0) {
                                return 'Includes: ' + d.includes.join(', ');
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'logarithmic',
                    min: 1,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: {
                        callback: function(value) {
                            if ([1, 10, 100, 1000, 10000].includes(value)) {
                                return new Intl.NumberFormat('en-GB').format(value);
                            }
                            return '';
                        }
                    },
                    title: { display: true, text: 'MW (log scale)' }
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
