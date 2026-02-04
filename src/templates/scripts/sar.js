// SAR (System Activity Reporter) Viewer
// Dynamic graph visualization with navigation

// Check if Chart.js is available
if (typeof Chart === 'undefined') {
    console.error('SAR viewer: Chart.js is required but not loaded');
}

class SarViewer {
    constructor(containerId, sarData) {
        this.container = document.getElementById(containerId);
        this.sarData = sarData;
        this.currentDayIndex = 0;
        this.charts = {};
        
        if (!this.container || !this.sarData || !this.sarData.available) {
            console.error('SAR viewer: Invalid container or data');
            return;
        }
        
        this.availableDays = this.sarData.available_days || [];
        if (this.availableDays.length === 0) {
            console.error('SAR viewer: No available days');
            return;
        }
        
        this.init();
    }
    
    init() {
        // Set up navigation
        this.setupNavigation();
        
        // Prevent resize issues by setting initial canvas dimensions
        this.setInitialCanvasDimensions();
        
        // Load initial day
        this.loadDay(this.availableDays[0]);
    }
    
    setInitialCanvasDimensions() {
        const canvases = ['sar-cpu-graph', 'sar-load-graph', 'sar-memory-graph'];
        canvases.forEach(id => {
            const canvas = document.getElementById(id);
            if (canvas) {
                // Wait for container to be laid out
                setTimeout(() => {
                    canvas.width = canvas.offsetWidth || 800;
                    canvas.height = 400;
                    canvas.style.height = '400px';
                    canvas.style.maxHeight = '400px';
                    canvas.style.width = '100%';
                }, 100);
            }
        });
    }
    
    setupNavigation() {
        const prevButton = document.getElementById('sar-prev-day');
        const nextButton = document.getElementById('sar-next-day');
        const daySelector = document.getElementById('sar-day-selector');
        
        if (!prevButton || !nextButton || !daySelector) {
            console.error('SAR viewer: Navigation elements not found');
            return;
        }
        
        // Previous button
        prevButton.addEventListener('click', () => {
            if (this.currentDayIndex > 0) {
                this.currentDayIndex--;
                const day = this.availableDays[this.currentDayIndex];
                daySelector.value = day;
                this.loadDay(day);
            }
        });
        
        // Next button
        nextButton.addEventListener('click', () => {
            if (this.currentDayIndex < this.availableDays.length - 1) {
                this.currentDayIndex++;
                const day = this.availableDays[this.currentDayIndex];
                daySelector.value = day;
                this.loadDay(day);
            }
        });
        
        // Day selector
        daySelector.addEventListener('change', (e) => {
            const day = parseInt(e.target.value);
            this.currentDayIndex = this.availableDays.indexOf(day);
            this.loadDay(day);
        });
        
        // Update button states
        this.updateNavigationButtons();
    }
    
    updateNavigationButtons() {
        const prevButton = document.getElementById('sar-prev-day');
        const nextButton = document.getElementById('sar-next-day');
        
        if (prevButton) {
            prevButton.disabled = this.currentDayIndex === 0;
        }
        if (nextButton) {
            nextButton.disabled = this.currentDayIndex >= this.availableDays.length - 1;
        }
    }
    
    loadDay(day) {
        const dayData = this.sarData.files[day];
        if (!dayData || !dayData.data) {
            console.error(`SAR viewer: No data for day ${day}`);
            return;
        }
        
        // Destroy existing charts
        this.destroyCharts();
        
        // Create new charts
        this.createCpuChart(dayData.data);
        this.createLoadChart(dayData.data);
        this.createMemoryChart(dayData.data);
        
        // Update navigation
        this.updateNavigationButtons();
    }
    
    destroyCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
        
        // Reset canvas dimensions to prevent growth
        const canvases = ['sar-cpu-graph', 'sar-load-graph', 'sar-memory-graph'];
        canvases.forEach(id => {
            const canvas = document.getElementById(id);
            if (canvas) {
                canvas.width = canvas.offsetWidth;
                canvas.height = 400; // Fixed height
                canvas.style.height = '400px';
                canvas.style.maxHeight = '400px';
            }
        });
    }
    
    createCpuChart(data) {
        const canvas = document.getElementById('sar-cpu-graph');
        if (!canvas || !data.cpu || data.cpu.length === 0) {
            if (canvas) {
                canvas.parentElement.innerHTML += '<p style="color: var(--text-secondary);">No CPU data available for this day.</p>';
            }
            return;
        }
        
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not available');
            return;
        }
        
        // Filter to 'all' CPU data only for cleaner visualization
        const cpuAllData = data.cpu.filter(d => d.cpu === 'all');
        
        if (cpuAllData.length === 0) {
            if (canvas) {
                canvas.parentElement.innerHTML += '<p style="color: var(--text-secondary);">No CPU data available for this day.</p>';
            }
            return;
        }
        
        const labels = cpuAllData.map(d => d.time);
        const utilization = cpuAllData.map(d => d.utilization || (100 - (d.idle || 0)));
        const user = cpuAllData.map(d => d.usr || 0);
        const system = cpuAllData.map(d => d.sys || 0);
        const iowait = cpuAllData.map(d => d.iowait || 0);
        
        // Set explicit canvas dimensions before creating chart
        const containerWidth = canvas.parentElement.offsetWidth || canvas.offsetWidth || 800;
        canvas.width = containerWidth;
        canvas.height = 400;
        canvas.style.height = '400px';
        canvas.style.maxHeight = '400px';
        canvas.style.width = '100%';
        canvas.style.display = 'block';
        
        const ctx = canvas.getContext('2d');
        this.charts.cpu = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Total Utilization',
                        data: utilization,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1,
                        fill: true
                    },
                    {
                        label: 'User',
                        data: user,
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        tension: 0.1
                    },
                    {
                        label: 'System',
                        data: system,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1
                    },
                    {
                        label: 'I/O Wait',
                        data: iowait,
                        borderColor: 'rgb(255, 159, 64)',
                        backgroundColor: 'rgba(255, 159, 64, 0.2)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                resizeDelay: 0,
                layout: {
                    padding: {
                        top: 10,
                        bottom: 10
                    }
                },
                onResize: null, // Disable resize handler
                plugins: {
                    title: {
                        display: true,
                        text: 'CPU Utilization Over Time'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Percentage (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                }
            }
        });
    }
    
    createLoadChart(data) {
        const canvas = document.getElementById('sar-load-graph');
        if (!canvas || !data.load || data.load.length === 0) {
            if (canvas) {
                canvas.parentElement.innerHTML += '<p style="color: var(--text-secondary);">No load average data available for this day.</p>';
            }
            return;
        }
        
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not available');
            return;
        }
        
        const labels = data.load.map(d => d.time);
        const ldavg1 = data.load.map(d => d.ldavg_1 || 0);
        const ldavg5 = data.load.map(d => d.ldavg_5 || 0);
        const ldavg15 = data.load.map(d => d.ldavg_15 || 0);
        
        // Set explicit canvas dimensions before creating chart
        const containerWidth = canvas.parentElement.offsetWidth || canvas.offsetWidth || 800;
        canvas.width = containerWidth;
        canvas.height = 400;
        canvas.style.height = '400px';
        canvas.style.maxHeight = '400px';
        canvas.style.width = '100%';
        canvas.style.display = 'block';
        
        const ctx = canvas.getContext('2d');
        this.charts.load = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Load Average (1 min)',
                        data: ldavg1,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1,
                        fill: true
                    },
                    {
                        label: 'Load Average (5 min)',
                        data: ldavg5,
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        tension: 0.1
                    },
                    {
                        label: 'Load Average (15 min)',
                        data: ldavg15,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                resizeDelay: 0,
                layout: {
                    padding: {
                        top: 10,
                        bottom: 10
                    }
                },
                onResize: null, // Disable resize handler
                plugins: {
                    title: {
                        display: true,
                        text: 'System Load Average'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Load Average'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                }
            }
        });
    }
    
    createMemoryChart(data) {
        const canvas = document.getElementById('sar-memory-graph');
        if (!canvas || !data.memory || data.memory.length === 0) {
            if (canvas) {
                canvas.parentElement.innerHTML += '<p style="color: var(--text-secondary);">No memory data available for this day.</p>';
            }
            return;
        }
        
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not available');
            return;
        }
        
        // Extract memory data - try to find meaningful metrics
        const labels = data.memory.map(d => d.time);
        
        // Try to extract memory metrics from raw data
        const memFree = data.memory.map(d => {
            if (d.kbmemfree !== undefined) return d.kbmemfree / 1024; // Convert to MB
            if (d.raw && d.raw.length > 0 && typeof d.raw[0] === 'number') return d.raw[0] / 1024;
            return 0;
        });
        
        const memUsed = data.memory.map(d => {
            if (d.kbmemused !== undefined) return d.kbmemused / 1024; // Convert to MB
            if (d.raw && d.raw.length > 2 && typeof d.raw[2] === 'number') return d.raw[2] / 1024;
            return 0;
        });
        
        // Set explicit canvas dimensions before creating chart
        const containerWidth = canvas.parentElement.offsetWidth || canvas.offsetWidth || 800;
        canvas.width = containerWidth;
        canvas.height = 400;
        canvas.style.height = '400px';
        canvas.style.maxHeight = '400px';
        canvas.style.width = '100%';
        canvas.style.display = 'block';
        
        const ctx = canvas.getContext('2d');
        this.charts.memory = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Memory Free (MB)',
                        data: memFree,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1,
                        fill: true
                    },
                    {
                        label: 'Memory Used (MB)',
                        data: memUsed,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                resizeDelay: 0,
                layout: {
                    padding: {
                        top: 10,
                        bottom: 10
                    }
                },
                onResize: null, // Disable resize handler
                plugins: {
                    title: {
                        display: true,
                        text: 'Memory Usage'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Memory (MB)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                }
            }
        });
    }
}
