// Q1 Chart - Development Time Over Decades
function initQ1Chart() {
    const canvas = document.getElementById('devTimeChart');
    if (!canvas) {
        console.log('Q1 canvas not found');
        return;
    }

    fetch('/api/chart/q1')
        .then(r => r.json())
        .then(data => {
            console.log('Q1 data:', data);

            const ctx = canvas.getContext('2d');

            new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [
                        ...data.datasets,
                        {
                            label: 'Trend',
                            data: data.trend,
                            type: 'line',
                            borderColor: '#000',
                            borderDash: [5, 5],
                            pointRadius: 0,
                            fill: false,
                            tension: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'linear',
                            position: 'bottom',
                            title: { display: true, text: 'Release Year' },
                            min: data.x_min,
                            max: data.x_max
                        },
                        y: {
                            title: { display: true, text: 'Development Time' }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: 'Game Development Time Over the Decades'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const point = context.raw;
                                    if (point.name) {
                                        return `${point.name}: ${formatMonthsShort(point.y)} (${point.x})`;
                                    }
                                    return `Trend: ${formatMonthsShort(point.y)}`;
                                }
                            }
                        },
                        zoom: {
                            zoom: {
                                wheel: { enabled: true },
                                pinch: { enabled: true },
                                mode: 'xy'
                            },
                            pan: {
                                enabled: true,
                                mode: 'xy'
                            }
                        }
                    }
                }
            });
        })
        .catch(err => {
            console.error('Q1 chart error:', err);
        });
}

function initQ3Chart() {
    const canvas = document.getElementById('eraChart');
    if (!canvas) return;

    fetch('/api/chart/q3')
        .then(r => r.json())
        .then(data => {
            const ctx = canvas.getContext('2d');

            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: 'Avg Dev Time',
                            data: data.dev_time,
                            backgroundColor: '#e74c3c',
                            yAxisID: 'y'
                        },
                        {
                            label: 'Avg Team Size',
                            data: data.team_size,
                            backgroundColor: '#3498db',
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: { display: true, text: 'Development Time' },
                            ticks: {
                                callback: function(value) {
                                    return formatMonthsShort(value);
                                }
                            }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: { display: true, text: 'Team Size' },
                            grid: { drawOnChartArea: false }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: 'How Game Development Scaled Over the Decades'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.dataset.label || '';
                                    const value = context.parsed.y;
                                    if (label.includes('Dev Time')) {
                                        return `${label}: ${formatMonths(value)}`;
                                    }
                                    return `${label}: ${formatTeamSize(value)} people`;
                                }
                            }
                        },
                        zoom: {
                            zoom: {
                                wheel: { enabled: true },
                                pinch: { enabled: true },
                                mode: 'xy'
                            },
                            pan: {
                                enabled: true,
                                mode: 'xy'
                            }
                        }
                    }
                }
            });
            
            console.log('Q3 chart created with zoom');
        })
        .catch(err => console.error('Q3 chart error:', err));
}

function initQ7Chart() {
    const canvas = document.getElementById('engineChart');
    if (!canvas) return;

    fetch('/api/chart/q7')
        .then(r => r.json())
        .then(data => {
            const ctx = canvas.getContext('2d');

            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Average Development Time',
                        data: data.values,
                        backgroundColor: '#3498db',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Development Time' },
                            ticks: {
                                callback: function(value) {
                                    return formatMonthsShort(value);
                                }
                            }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: 'Did Engine Choice Affect Development'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.parsed.y;
                                    return `Avg Time: ${formatMonths(value)}`;
                                }
                            }
                        },
                        zoom: {
                            zoom: {
                                wheel: { enabled: true },
                                pinch: { enabled: true },
                                mode: 'xy'
                            },
                            pan: {
                                enabled: true,
                                mode: 'xy'
                            }
                        }
                    }
                }
            });
        })
        .catch(err => console.error('Q7 chart error:', err));
}

function initQ8Chart() {
    const metrics = [
        { id: 'divergenceDevTime', key: 'development_time', label: 'Development Time', formatter: formatMonthsShort, axisFormatter: formatMonthsShort },
        { id: 'divergenceBudget', key: 'budget', label: 'Budget', formatter: formatBudget, axisFormatter: null },
        { id: 'divergenceTeamSize', key: 'peak_team_size', label: 'Team Size', formatter: formatTeamSize, axisFormatter: null },
        { id: 'divergenceFileSize', key: 'file_size', label: 'File Size', formatter: formatFileSize, axisFormatter: formatFileSize }
    ];

    fetch('/api/chart/q8')
        .then(r => r.json())
        .then(data => {
            metrics.forEach(metric => {
                const canvas = document.getElementById(metric.id);
                if (!canvas) return;

                const ctx = canvas.getContext('2d');

                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.labels,
                        datasets: [
                            {
                                label: 'AAA',
                                data: data.metrics[metric.key].AAA,
                                borderColor: '#e74c3c',
                                backgroundColor: 'rgba(231, 76, 60, 0.1)',
                                tension: 0.3,
                                fill: false
                            },
                            {
                                label: 'Indie',
                                data: data.metrics[metric.key].Indie,
                                borderColor: '#2ecc71',
                                backgroundColor: 'rgba(46, 204, 113, 0.1)',
                                tension: 0.3,
                                fill: false
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: metric.axisFormatter ? {
                                ticks: {
                                    callback: function(value) {
                                        return metric.axisFormatter(value);
                                    }
                                }
                            } : {}
                        },
                        plugins: {
                            title: {
                                display: true,
                                text: metric.label
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.dataset.label;
                                        const value = context.parsed.y;
                                        const formatted = metric.formatter(value);
                                        return `${label}: ${formatted}`;
                                    }
                                }
                            },
                            zoom: {
                                zoom: {
                                    wheel: { enabled: true },
                                    pinch: { enabled: true },
                                    mode: 'xy'
                                },
                                pan: {
                                    enabled: true,
                                    mode: 'xy'
                                }
                            }
                        }
                    }
                });
            });
        })
        .catch(err => console.error('Q8 chart error:', err));
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM ready, initializing charts');
    initQ1Chart();
    initQ3Chart();
    initQ7Chart();
    initQ8Chart();
});