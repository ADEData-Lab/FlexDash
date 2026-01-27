/**
 * FlexDash Chart Management
 *
 * Handles Chart.js visualization creation and updates
 */

// Chart color palette - uses ADE:Demand brand colors
// These can be updated dynamically when theme changes
const CHART_COLORS = {
    primary: '#45c3d3',      // Teal
    secondary: '#6eb43f',    // Green
    tertiary: '#eb8800',     // Orange
    success: '#6eb43f',      // Green
    warning: '#eb8800',      // Orange
    danger: '#c41230',       // Crimson
    domestic: '#45c3d3',     // Teal
    ic: '#6eb43f',           // Green
    illustrative: '#eb8800', // Orange
    palette: [
        '#45c3d3', '#6eb43f', '#eb8800', '#c41230',
        '#58585a', '#7dd3e0', '#8dc761', '#f5a623'
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

    // Methodology v7 charts
    createDirectionalChart(data);
    createFlexTypeChart(data);
    createEnergyBreakdownChart(data);
    createLatentPotentialChart(data);
    createFutureTimelineChart(data);
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

    // Get theme colors
    const domesticColor = getComputedStyle(document.documentElement).getPropertyValue('--chart-domestic').trim() || CHART_COLORS.domestic;
    const icColor = getComputedStyle(document.documentElement).getPropertyValue('--chart-ic').trim() || CHART_COLORS.ic;

    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [domesticColor, icColor],
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

/**
 * Methodology v7: Turn-up vs Turn-down Chart
 * Shows capacity (actual values, k>=3) only - energy values omitted due to k<3
 */
function createDirectionalChart(data) {
    const ctx = document.getElementById('directional-chart');
    if (!ctx) return;

    const dirData = data.directional_breakdown;
    if (!dirData) return;

    // Get theme colors
    const styles = getComputedStyle(document.documentElement);
    const successColor = styles.getPropertyValue('--color-success').trim() || '#6eb43f';
    const primaryColor = styles.getPropertyValue('--chart-domestic').trim() || '#45c3d3';

    // Only show capacity (k>=3), energy is k<3 so not charted
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Turn-Up', 'Turn-Down'],
            datasets: [
                {
                    label: 'Capacity (GW)',
                    data: [
                        dirData.turn_up.capacity_mw / 1000,
                        dirData.turn_down.capacity_mw / 1000
                    ],
                    backgroundColor: [successColor, primaryColor],
                    borderRadius: 4
                }
            ]
        },
        options: {
            ...CHART_DEFAULTS,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                legend: { display: false },
                title: {
                    display: true,
                    text: 'Flexibility by Direction (Capacity GW)'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label;
                            const value = context.parsed.y;
                            return `${label}: ${value.toFixed(1)} GW`;
                        },
                        afterLabel: function(context) {
                            const idx = context.dataIndex;
                            if (idx === 0) return `Energy: ${dirData.turn_up.energy_gwh_range} (range)`;
                            return `Energy: ${dirData.turn_down.energy_gwh_range} (range)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Capacity (GW)' }
                }
            }
        }
    });

    if (!window.DashboardState.charts.overview) {
        window.DashboardState.charts.overview = [];
    }
    window.DashboardState.charts.overview.push(chart);
}

/**
 * Methodology v7: Explicit vs Implicit Doughnut Chart
 */
function createFlexTypeChart(data) {
    const ctx = document.getElementById('flex-type-chart');
    if (!ctx) return;

    const flexData = data.flexibility_type_breakdown;
    if (!flexData) return;

    // Get theme colors
    const styles = getComputedStyle(document.documentElement);
    const domesticColor = styles.getPropertyValue('--chart-domestic').trim() || CHART_COLORS.domestic;
    const icColor = styles.getPropertyValue('--chart-ic').trim() || CHART_COLORS.ic;

    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Explicit (Managed)', 'Implicit (ToU Response)'],
            datasets: [{
                data: [flexData.explicit.capacity_mw, flexData.implicit.capacity_mw],
                backgroundColor: [domesticColor, icColor],
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
                    display: true,
                    text: 'Explicit vs Implicit Flexibility'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((value / total) * 100).toFixed(1);
                            return `${context.label}: ${(value / 1000).toFixed(1)} GW (${pct}%)`;
                        }
                    }
                }
            }
        }
    });

    if (!window.DashboardState.charts.overview) {
        window.DashboardState.charts.overview = [];
    }
    window.DashboardState.charts.overview.push(chart);
}

/**
 * Methodology v7: Energy Breakdown Chart
 * Note: Explicit/Implicit use range midpoints due to k<3 disclosure control
 */
function createEnergyBreakdownChart(data) {
    const ctx = document.getElementById('energy-breakdown-chart');
    if (!ctx) return;

    const energyData = data.energy_metrics;
    if (!energyData) return;

    // Use midpoints for illustrative/range values
    const explicitMidpoint = energyData.explicit.illustrative ?
        (energyData.explicit.delivered_gwh_min + energyData.explicit.delivered_gwh_max) / 2 : 0;
    const implicitMidpoint = energyData.implicit.illustrative ?
        (energyData.implicit.delivered_gwh_min + energyData.implicit.delivered_gwh_max) / 2 : 0;

    // Get theme colors
    const styles = getComputedStyle(document.documentElement);
    const illustrativeColor = styles.getPropertyValue('--chart-illustrative').trim() || '#eb8800';
    const successColor = styles.getPropertyValue('--color-success').trim() || '#6eb43f';

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Explicit [Range]', 'Implicit [Range]', 'Total'],
            datasets: [
                {
                    label: 'Delivered (GWh)',
                    data: [
                        explicitMidpoint,
                        implicitMidpoint,
                        energyData.total.delivered_gwh
                    ],
                    backgroundColor: [
                        illustrativeColor + 'b3',  // Orange with transparency for illustrative
                        illustrativeColor + 'b3',  // Orange with transparency for illustrative
                        successColor + 'cc'        // Green for actual
                    ],
                    borderColor: [illustrativeColor, illustrativeColor, successColor],
                    borderWidth: 2
                }
            ]
        },
        options: {
            ...CHART_DEFAULTS,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                title: {
                    display: true,
                    text: 'Energy Flexibility (GWh) - Orange = Range Estimates (k<3)'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            if (idx === 0) return `Explicit: ${energyData.explicit.delivered_gwh_range} (range)`;
                            if (idx === 1) return `Implicit: ${energyData.implicit.delivered_gwh_range} (range)`;
                            return `Total: ${context.parsed.y.toLocaleString()} GWh`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Energy (GWh)' }
                }
            }
        }
    });

    if (!window.DashboardState.charts.overview) {
        window.DashboardState.charts.overview = [];
    }
    window.DashboardState.charts.overview.push(chart);
}

/**
 * Methodology v7: Latent Potential Bar Chart
 */
function createLatentPotentialChart(data) {
    const ctx = document.getElementById('latent-potential-chart');
    if (!ctx) return;

    const latentData = data.latent_potential;
    if (!latentData || !latentData.by_asset_class) return;

    const assets = latentData.by_asset_class.filter(a => a.latent_gw);
    const labels = assets.map(a => a.display_name);
    const values = assets.map(a => a.latent_gw);

    // Get theme colors
    const styles = getComputedStyle(document.documentElement);
    const teal = styles.getPropertyValue('--chart-domestic').trim() || '#45c3d3';
    const green = styles.getPropertyValue('--chart-ic').trim() || '#6eb43f';
    const orange = styles.getPropertyValue('--chart-illustrative').trim() || '#eb8800';
    const crimson = styles.getPropertyValue('--color-danger').trim() || '#c41230';

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Latent Potential (GW)',
                data: values,
                backgroundColor: [
                    teal, green, orange, crimson
                ],
                borderRadius: 4
            }]
        },
        options: {
            ...CHART_DEFAULTS,
            indexAxis: 'y',
            plugins: {
                ...CHART_DEFAULTS.plugins,
                legend: { display: false },
                title: {
                    display: true,
                    text: 'Latent Flexibility Potential by Asset Class'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const asset = assets[context.dataIndex];
                            return [
                                `Potential: ${context.parsed.x.toFixed(1)} GW`,
                                `GB Deployed: ${(asset.gb_deployed / 1000000).toFixed(2)}M units`,
                                `Source: ${asset.source}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: { display: true, text: 'Potential Capacity (GW)' }
                }
            }
        }
    });

    if (!window.DashboardState.charts.projections) {
        window.DashboardState.charts.projections = [];
    }
    window.DashboardState.charts.projections.push(chart);
}

/**
 * Methodology v7: Future Potential Timeline Chart
 */
function createFutureTimelineChart(data) {
    const ctx = document.getElementById('future-timeline-chart');
    if (!ctx) return;

    const futureData = data.future_potential;
    if (!futureData) return;

    const currentGW = data.metrics.total_available_mw / 1000;

    // Get theme colors
    const styles = getComputedStyle(document.documentElement);
    const primaryColor = styles.getPropertyValue('--chart-domestic').trim() || '#45c3d3';
    const successColor = styles.getPropertyValue('--color-success').trim() || '#6eb43f';
    const warningColor = styles.getPropertyValue('--color-warning').trim() || '#eb8800';

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['2025 (Current)', '2030', '2050'],
            datasets: [
                {
                    label: 'Central Scenario',
                    data: [currentGW, futureData['2030'].central_gw, futureData['2050'].central_gw],
                    borderColor: primaryColor,
                    backgroundColor: primaryColor + '33', // Add transparency
                    fill: true,
                    tension: 0.3,
                    pointRadius: 8,
                    pointHoverRadius: 12
                },
                {
                    label: 'High Scenario',
                    data: [currentGW, futureData['2030'].range_max_gw, futureData['2050'].range_max_gw],
                    borderColor: successColor,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.3,
                    pointRadius: 6
                },
                {
                    label: 'Low Scenario',
                    data: [currentGW, futureData['2030'].range_min_gw, futureData['2050'].range_min_gw],
                    borderColor: warningColor,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.3,
                    pointRadius: 6
                }
            ]
        },
        options: {
            ...CHART_DEFAULTS,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                title: {
                    display: true,
                    text: 'Flexibility Potential Trajectory (GW)'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toFixed(0)} GW`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 250,
                    title: { display: true, text: 'Flexibility Capacity (GW)' }
                }
            }
        }
    });

    if (!window.DashboardState.charts.projections) {
        window.DashboardState.charts.projections = [];
    }
    window.DashboardState.charts.projections.push(chart);
}

/**
 * Create 2030 Technology Breakdown Chart
 */
function create2030TechChart(data) {
    const ctx = document.getElementById('tech-2030-chart');
    if (!ctx) return;

    const futureData = data.future_potential?.['2030'];
    if (!futureData || !futureData.by_technology) return;

    const techs = futureData.by_technology;
    const labels = techs.map(t => t.technology);
    const values = techs.map(t => t.gw);

    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: ['#2E86AB', '#A23B72', '#F18F01', '#4CAF50'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            ...CHART_DEFAULTS,
            cutout: '50%',
            plugins: {
                ...CHART_DEFAULTS.plugins,
                title: {
                    display: true,
                    text: '2030 Flexibility by Technology'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const tech = techs[context.dataIndex];
                            return [`${context.label}: ${context.parsed} GW`, tech.note];
                        }
                    }
                }
            }
        }
    });

    if (!window.DashboardState.charts.projections) {
        window.DashboardState.charts.projections = [];
    }
    window.DashboardState.charts.projections.push(chart);
}

// Export for use
window.initializeCharts = initializeCharts;
window.CHART_COLORS = CHART_COLORS;
window.createDirectionalChart = createDirectionalChart;
window.createFlexTypeChart = createFlexTypeChart;
window.createEnergyBreakdownChart = createEnergyBreakdownChart;
window.createLatentPotentialChart = createLatentPotentialChart;
window.createFutureTimelineChart = createFutureTimelineChart;
window.create2030TechChart = create2030TechChart;
