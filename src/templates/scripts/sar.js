// SAR (System Activity Reporter) Viewer
// Dynamic graph visualization with navigation and plot selector

// Check if Chart.js is available
if (typeof Chart === 'undefined') {
    console.error('SAR viewer: Chart.js is required but not loaded');
}

class SarViewer {
    constructor(containerId, sarData) {
        this.container = document.getElementById(containerId);
        this.sarData = sarData;
        this.currentDayIndex = 0;
        this.currentPlot = 'cpu';
        this.chart = null;
        
        if (!this.container || !this.sarData || !this.sarData.available) {
            console.error('SAR viewer: Invalid container or data');
            return;
        }
        
        this.availableDays = this.sarData.available_days || [];
        if (this.availableDays.length === 0) {
            console.error('SAR viewer: No available days');
            return;
        }
        
        // Define all available plot types with their metadata
        this.plotTypes = {
            cpu: { name: 'CPU Utilization', dataKey: 'cpu', group: 'CPU & Process' },
            process: { name: 'Process Creation & Context Switches', dataKey: 'process', group: 'CPU & Process' },
            softnet: { name: 'Softnet Statistics', dataKey: 'softnet', group: 'CPU & Process' },
            load: { name: 'Load Average', dataKey: 'load', group: 'System' },
            memory: { name: 'Memory Utilization', dataKey: 'memory', group: 'Memory' },
            swap: { name: 'Swap Utilization', dataKey: 'swap', group: 'Memory' },
            swap_paging: { name: 'Swap Paging (In/Out)', dataKey: 'swap_paging', group: 'Memory' },
            hugepages: { name: 'Hugepages Utilization', dataKey: 'hugepages', group: 'Memory' },
            paging: { name: 'Paging Statistics', dataKey: 'paging', group: 'Memory' },
            io_transfer: { name: 'I/O Transfer Rates', dataKey: 'io_transfer', group: 'Storage' },
            block_device: { name: 'Block Device Statistics', dataKey: 'block_device', group: 'Storage' },
            filesystem: { name: 'Filesystem Utilization', dataKey: 'filesystem', group: 'Storage' },
            network: { name: 'Network Interface Stats', dataKey: 'network', group: 'Network' },
            network_errors: { name: 'Network Error Stats', dataKey: 'network_errors', group: 'Network' },
            sockets: { name: 'Socket Usage', dataKey: 'sockets', group: 'Network' },
            nfs_client: { name: 'NFS Client RPC Stats', dataKey: 'nfs_client', group: 'NFS' },
            nfs_server: { name: 'NFS Server RPC Stats', dataKey: 'nfs_server', group: 'NFS' },
            tty: { name: 'Serial/TTY Statistics', dataKey: 'tty', group: 'System' }
        };
        
        this.init();
    }
    
    init() {
        // Set up navigation
        this.setupNavigation();
        
        // Set up plot selector
        this.setupPlotSelector();
        
        // Prevent resize issues by setting initial canvas dimensions
        this.setInitialCanvasDimensions();
        
        // Load initial day and plot
        this.loadDay(this.availableDays[0]);
    }
    
    setInitialCanvasDimensions() {
        const canvas = document.getElementById('sar-graph');
        if (canvas) {
            setTimeout(() => {
                canvas.width = canvas.offsetWidth || 800;
                canvas.height = 450;
                canvas.style.height = '450px';
                canvas.style.maxHeight = '450px';
                canvas.style.width = '100%';
            }, 100);
        }
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
    
    setupPlotSelector() {
        const plotSelector = document.getElementById('sar-plot-selector');
        if (!plotSelector) {
            console.error('SAR viewer: Plot selector not found');
            return;
        }
        
        // Clear existing options
        plotSelector.innerHTML = '';
        
        // Group plot types by category
        const groups = {};
        for (const [key, config] of Object.entries(this.plotTypes)) {
            if (!groups[config.group]) {
                groups[config.group] = [];
            }
            groups[config.group].push({ key, ...config });
        }
        
        // Create optgroups
        for (const [groupName, plots] of Object.entries(groups)) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = groupName;
            
            for (const plot of plots) {
                const option = document.createElement('option');
                option.value = plot.key;
                option.textContent = plot.name;
                if (plot.key === this.currentPlot) {
                    option.selected = true;
                }
                optgroup.appendChild(option);
            }
            
            plotSelector.appendChild(optgroup);
        }
        
        // Handle plot selection change
        plotSelector.addEventListener('change', (e) => {
            this.currentPlot = e.target.value;
            this.updateChart();
        });
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
        this.currentDay = day;
        const dayData = this.sarData.files[day];
        if (!dayData || !dayData.data) {
            console.error(`SAR viewer: No data for day ${day}`);
            return;
        }
        
        this.dayData = dayData.data;
        this.currentDateDisplay = dayData.date_display || `Day ${day}`;
        
        // Update available plots indicator
        this.updateAvailablePlots();
        
        // Create chart for current plot type
        this.updateChart();
        
        // Update navigation
        this.updateNavigationButtons();
    }
    
    updateAvailablePlots() {
        const plotSelector = document.getElementById('sar-plot-selector');
        if (!plotSelector) return;
        
        // Disable options that don't have data
        const options = plotSelector.querySelectorAll('option');
        options.forEach(option => {
            const plotKey = option.value;
            const plotConfig = this.plotTypes[plotKey];
            const hasData = this.dayData[plotConfig.dataKey] && this.dayData[plotConfig.dataKey].length > 0;
            option.disabled = !hasData;
            option.textContent = this.plotTypes[plotKey].name + (hasData ? '' : ' (no data)');
        });
    }
    
    updateChart() {
        // Destroy existing chart
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
        
        const canvas = document.getElementById('sar-graph');
        if (!canvas) {
            console.error('SAR viewer: Canvas not found');
            return;
        }
        
        // Reset canvas
        const containerWidth = canvas.parentElement.offsetWidth || canvas.offsetWidth || 800;
        canvas.width = containerWidth;
        canvas.height = 450;
        canvas.style.height = '450px';
        canvas.style.maxHeight = '450px';
        canvas.style.width = '100%';
        canvas.style.display = 'block';
        
        // Clear any error message
        const errorMsg = canvas.parentElement.querySelector('.sar-no-data-msg');
        if (errorMsg) {
            errorMsg.remove();
        }
        
        // Create appropriate chart based on plot type
        const chartCreator = this.getChartCreator(this.currentPlot);
        if (chartCreator) {
            chartCreator.call(this, this.dayData);
        }
    }
    
    getChartCreator(plotType) {
        const creators = {
            cpu: this.createCpuChart,
            process: this.createProcessChart,
            paging: this.createPagingChart,
            swap_paging: this.createSwapPagingChart,
            io_transfer: this.createIoTransferChart,
            memory: this.createMemoryChart,
            swap: this.createSwapChart,
            hugepages: this.createHugepagesChart,
            filesystem: this.createFilesystemChart,
            load: this.createLoadChart,
            tty: this.createTtyChart,
            block_device: this.createBlockDeviceChart,
            network: this.createNetworkChart,
            network_errors: this.createNetworkErrorsChart,
            nfs_client: this.createNfsClientChart,
            nfs_server: this.createNfsServerChart,
            sockets: this.createSocketsChart,
            softnet: this.createSoftnetChart
        };
        return creators[plotType];
    }
    
    showNoDataMessage(canvas, message) {
        const msg = document.createElement('p');
        msg.className = 'sar-no-data-msg';
        msg.style.color = 'var(--text-secondary)';
        msg.style.textAlign = 'center';
        msg.style.padding = '2rem';
        msg.textContent = message || 'No data available for this metric.';
        canvas.parentElement.appendChild(msg);
    }
    
    getChartConfig(title, yAxisLabel, datasets, labels, options = {}) {
        // Include date in title if available
        const fullTitle = this.currentDateDisplay ? 
            `${title} - ${this.currentDateDisplay}` : title;
        
        return {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                resizeDelay: 0,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                layout: {
                    padding: { top: 10, bottom: 10 }
                },
                plugins: {
                    title: {
                        display: true,
                        text: fullTitle,
                        font: { size: 16 }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        enabled: true
                    }
                },
                scales: {
                    y: {
                        beginAtZero: options.beginAtZero !== false,
                        max: options.max,
                        title: {
                            display: true,
                            text: yAxisLabel
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                },
                ...options.chartOptions
            }
        };
    }
    
    // Color palette for charts
    colors = {
        primary: { border: 'rgb(75, 192, 192)', bg: 'rgba(75, 192, 192, 0.2)' },
        secondary: { border: 'rgb(54, 162, 235)', bg: 'rgba(54, 162, 235, 0.2)' },
        danger: { border: 'rgb(255, 99, 132)', bg: 'rgba(255, 99, 132, 0.2)' },
        warning: { border: 'rgb(255, 159, 64)', bg: 'rgba(255, 159, 64, 0.2)' },
        success: { border: 'rgb(75, 192, 75)', bg: 'rgba(75, 192, 75, 0.2)' },
        purple: { border: 'rgb(153, 102, 255)', bg: 'rgba(153, 102, 255, 0.2)' },
        pink: { border: 'rgb(255, 99, 255)', bg: 'rgba(255, 99, 255, 0.2)' },
        yellow: { border: 'rgb(255, 205, 86)', bg: 'rgba(255, 205, 86, 0.2)' },
        gray: { border: 'rgb(128, 128, 128)', bg: 'rgba(128, 128, 128, 0.2)' },
        teal: { border: 'rgb(0, 150, 136)', bg: 'rgba(0, 150, 136, 0.2)' }
    };
    
    getColorPalette() {
        return [
            this.colors.primary, this.colors.secondary, this.colors.danger,
            this.colors.warning, this.colors.success, this.colors.purple,
            this.colors.pink, this.colors.yellow, this.colors.gray, this.colors.teal
        ];
    }
    
    // ============ Chart Creation Methods ============
    
    createCpuChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.cpu || data.cpu.length === 0) {
            this.showNoDataMessage(canvas, 'No CPU data available for this day.');
            return;
        }
        
        // Filter to 'all' CPU data only for cleaner visualization
        const cpuAllData = data.cpu.filter(d => d.cpu === 'all');
        if (cpuAllData.length === 0) {
            this.showNoDataMessage(canvas, 'No aggregated CPU data available.');
            return;
        }
        
        const labels = cpuAllData.map(d => d.time);
        const datasets = [
            {
                label: 'Total Utilization',
                data: cpuAllData.map(d => d.utilization || (100 - (d.idle || 0))),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1, fill: true
            },
            {
                label: 'User (%usr)',
                data: cpuAllData.map(d => d.usr || 0),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1
            },
            {
                label: 'System (%sys)',
                data: cpuAllData.map(d => d.sys || 0),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1
            },
            {
                label: 'I/O Wait (%iowait)',
                data: cpuAllData.map(d => d.iowait || 0),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1
            },
            {
                label: 'Steal (%steal)',
                data: cpuAllData.map(d => d.steal || 0),
                borderColor: this.colors.purple.border,
                backgroundColor: this.colors.purple.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('CPU Utilization Over Time', 'Percentage (%)', datasets, labels, { max: 100 });
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createProcessChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.process || data.process.length === 0) {
            this.showNoDataMessage(canvas, 'No process creation data available.');
            return;
        }
        
        const labels = data.process.map(d => d.time);
        const datasets = [
            {
                label: 'Processes Created/s (proc/s)',
                data: data.process.map(d => d.proc_s || 0),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1, fill: true,
                yAxisID: 'y'
            },
            {
                label: 'Context Switches/s (cswch/s)',
                data: data.process.map(d => d.cswch_s || 0),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1,
                yAxisID: 'y1'
            }
        ];
        
        const config = this.getChartConfig('Process Creation & Context Switches', 'Processes/s', datasets, labels);
        config.options.scales.y1 = {
            type: 'linear',
            display: true,
            position: 'right',
            title: { display: true, text: 'Context Switches/s' },
            grid: { drawOnChartArea: false }
        };
        
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createPagingChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.paging || data.paging.length === 0) {
            this.showNoDataMessage(canvas, 'No paging statistics available.');
            return;
        }
        
        const labels = data.paging.map(d => d.time);
        const datasets = [
            {
                label: 'Page In/s (pgpgin/s)',
                data: data.paging.map(d => d.pgpgin_s || 0),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1
            },
            {
                label: 'Page Out/s (pgpgout/s)',
                data: data.paging.map(d => d.pgpgout_s || 0),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1
            },
            {
                label: 'Page Faults/s (fault/s)',
                data: data.paging.map(d => d.fault_s || 0),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1
            },
            {
                label: 'Major Faults/s (majflt/s)',
                data: data.paging.map(d => d.majflt_s || 0),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1
            },
            {
                label: 'Page Free/s (pgfree/s)',
                data: data.paging.map(d => d.pgfree_s || 0),
                borderColor: this.colors.success.border,
                backgroundColor: this.colors.success.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('Paging Statistics', 'Pages/s', datasets, labels);
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createIoTransferChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.io_transfer || data.io_transfer.length === 0) {
            this.showNoDataMessage(canvas, 'No I/O transfer data available.');
            return;
        }
        
        const labels = data.io_transfer.map(d => d.time);
        const datasets = [
            {
                label: 'Total Transfers/s (tps)',
                data: data.io_transfer.map(d => d.tps || 0),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1, fill: true,
                yAxisID: 'y'
            },
            {
                label: 'Read Transfers/s (rtps)',
                data: data.io_transfer.map(d => d.rtps || 0),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1,
                yAxisID: 'y'
            },
            {
                label: 'Write Transfers/s (wtps)',
                data: data.io_transfer.map(d => d.wtps || 0),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1,
                yAxisID: 'y'
            },
            {
                label: 'Blocks Read/s (bread/s)',
                data: data.io_transfer.map(d => d.bread_s || 0),
                borderColor: this.colors.success.border,
                backgroundColor: this.colors.success.bg,
                tension: 0.1,
                yAxisID: 'y1'
            },
            {
                label: 'Blocks Written/s (bwrtn/s)',
                data: data.io_transfer.map(d => d.bwrtn_s || 0),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1,
                yAxisID: 'y1'
            }
        ];
        
        const config = this.getChartConfig('I/O Transfer Rates', 'Transfers/s', datasets, labels);
        config.options.scales.y1 = {
            type: 'linear',
            display: true,
            position: 'right',
            title: { display: true, text: 'Blocks/s' },
            grid: { drawOnChartArea: false }
        };
        
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createMemoryChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.memory || data.memory.length === 0) {
            this.showNoDataMessage(canvas, 'No memory data available.');
            return;
        }
        
        const labels = data.memory.map(d => d.time);
        const datasets = [
            {
                label: 'Memory Used (%)',
                data: data.memory.map(d => d.memused_pct || 0),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1, fill: true
            },
            {
                label: 'Commit (%)',
                data: data.memory.map(d => d.commit_pct || 0),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('Memory Utilization', 'Percentage (%)', datasets, labels, { max: 100 });
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createSwapChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.swap || data.swap.length === 0) {
            this.showNoDataMessage(canvas, 'No swap data available.');
            return;
        }
        
        const labels = data.swap.map(d => d.time);
        const datasets = [
            {
                label: 'Swap Used (%)',
                data: data.swap.map(d => d.swpused_pct || 0),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1, fill: true
            },
            {
                label: 'Swap Cached (%)',
                data: data.swap.map(d => d.swpcad_pct || 0),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('Swap Utilization', 'Percentage (%)', datasets, labels, { max: 100 });
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createSwapPagingChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.swap_paging || data.swap_paging.length === 0) {
            this.showNoDataMessage(canvas, 'No swap paging data available.');
            return;
        }
        
        const labels = data.swap_paging.map(d => d.time);
        const datasets = [
            {
                label: 'Pages Swapped In/s (pswpin/s)',
                data: data.swap_paging.map(d => d.pswpin_s || 0),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1, fill: true
            },
            {
                label: 'Pages Swapped Out/s (pswpout/s)',
                data: data.swap_paging.map(d => d.pswpout_s || 0),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('Swap Paging Activity', 'Pages/s', datasets, labels);
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createHugepagesChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.hugepages || data.hugepages.length === 0) {
            this.showNoDataMessage(canvas, 'No hugepages data available.');
            return;
        }
        
        const labels = data.hugepages.map(d => d.time);
        const datasets = [
            {
                label: 'Hugepages Used (%)',
                data: data.hugepages.map(d => d.hugused_pct || 0),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1, fill: true
            }
        ];
        
        const config = this.getChartConfig('Hugepages Utilization', 'Percentage (%)', datasets, labels, { max: 100 });
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createFilesystemChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.filesystem || data.filesystem.length === 0) {
            this.showNoDataMessage(canvas, 'No filesystem data available.');
            return;
        }
        
        const labels = data.filesystem.map(d => d.time);
        const datasets = [
            {
                label: 'File Handles (file-nr)',
                data: data.filesystem.map(d => d.file_nr || 0),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1, fill: true
            },
            {
                label: 'Inodes (inode-nr)',
                data: data.filesystem.map(d => d.inode_nr || 0),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1
            },
            {
                label: 'PTY Count (pty-nr)',
                data: data.filesystem.map(d => d.pty_nr || 0),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('Filesystem Utilization', 'Count', datasets, labels);
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createLoadChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.load || data.load.length === 0) {
            this.showNoDataMessage(canvas, 'No load average data available.');
            return;
        }
        
        const labels = data.load.map(d => d.time);
        const datasets = [
            {
                label: 'Load Average (1 min)',
                data: data.load.map(d => d.ldavg_1 || 0),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1, fill: true
            },
            {
                label: 'Load Average (5 min)',
                data: data.load.map(d => d.ldavg_5 || 0),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1
            },
            {
                label: 'Load Average (15 min)',
                data: data.load.map(d => d.ldavg_15 || 0),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1
            },
            {
                label: 'Run Queue Size',
                data: data.load.map(d => d.runq_sz || 0),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1
            },
            {
                label: 'Blocked Processes',
                data: data.load.map(d => d.blocked || 0),
                borderColor: this.colors.purple.border,
                backgroundColor: this.colors.purple.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('System Load Average', 'Load / Count', datasets, labels);
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createTtyChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.tty || data.tty.length === 0) {
            this.showNoDataMessage(canvas, 'No TTY/Serial data available.');
            return;
        }
        
        // Aggregate all TTYs for overview
        const timeGroups = {};
        data.tty.forEach(d => {
            if (!timeGroups[d.time]) {
                timeGroups[d.time] = { rcvin_s: 0, txmtin_s: 0, framerr_s: 0, ovrun_s: 0 };
            }
            timeGroups[d.time].rcvin_s += d.rcvin_s || 0;
            timeGroups[d.time].txmtin_s += d.txmtin_s || 0;
            timeGroups[d.time].framerr_s += d.framerr_s || 0;
            timeGroups[d.time].ovrun_s += d.ovrun_s || 0;
        });
        
        const labels = Object.keys(timeGroups).sort();
        const datasets = [
            {
                label: 'Receive/s (rcvin/s)',
                data: labels.map(t => timeGroups[t].rcvin_s),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1
            },
            {
                label: 'Transmit/s (txmtin/s)',
                data: labels.map(t => timeGroups[t].txmtin_s),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1
            },
            {
                label: 'Frame Errors/s',
                data: labels.map(t => timeGroups[t].framerr_s),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1
            },
            {
                label: 'Overruns/s',
                data: labels.map(t => timeGroups[t].ovrun_s),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('Serial/TTY Statistics', 'Operations/s', datasets, labels);
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createBlockDeviceChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.block_device || data.block_device.length === 0) {
            this.showNoDataMessage(canvas, 'No block device data available.');
            return;
        }
        
        // Get unique devices
        const devices = [...new Set(data.block_device.map(d => d.device))];
        
        // Get unique timestamps
        const allTimes = [...new Set(data.block_device.map(d => d.time))].sort();
        
        // Create datasets for each device's utilization
        const palette = this.getColorPalette();
        const datasets = devices.slice(0, 8).map((device, idx) => {
            const deviceData = data.block_device.filter(d => d.device === device);
            const dataMap = {};
            deviceData.forEach(d => { dataMap[d.time] = d.util || 0; });
            
            return {
                label: `${device} (% util)`,
                data: allTimes.map(t => dataMap[t] || 0),
                borderColor: palette[idx % palette.length].border,
                backgroundColor: palette[idx % palette.length].bg,
                tension: 0.1
            };
        });
        
        const config = this.getChartConfig('Block Device Utilization', 'Utilization (%)', datasets, allTimes, { max: 100 });
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createNetworkChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.network || data.network.length === 0) {
            this.showNoDataMessage(canvas, 'No network interface data available.');
            return;
        }
        
        // Get unique interfaces (exclude 'lo' for cleaner view)
        const interfaces = [...new Set(data.network.map(d => d.iface))].filter(i => i !== 'lo');
        if (interfaces.length === 0) {
            interfaces.push('lo'); // Fallback to loopback if nothing else
        }
        
        // Get unique timestamps
        const allTimes = [...new Set(data.network.map(d => d.time))].sort();
        
        // Create datasets for RX and TX kB/s per interface
        const palette = this.getColorPalette();
        const datasets = [];
        
        interfaces.slice(0, 4).forEach((iface, idx) => {
            const ifaceData = data.network.filter(d => d.iface === iface);
            const dataMap = {};
            ifaceData.forEach(d => { 
                dataMap[d.time] = { rx: d.rxkB_s || 0, tx: d.txkB_s || 0 }; 
            });
            
            datasets.push({
                label: `${iface} RX (kB/s)`,
                data: allTimes.map(t => dataMap[t]?.rx || 0),
                borderColor: palette[idx * 2 % palette.length].border,
                backgroundColor: palette[idx * 2 % palette.length].bg,
                tension: 0.1
            });
            
            datasets.push({
                label: `${iface} TX (kB/s)`,
                data: allTimes.map(t => dataMap[t]?.tx || 0),
                borderColor: palette[(idx * 2 + 1) % palette.length].border,
                backgroundColor: palette[(idx * 2 + 1) % palette.length].bg,
                tension: 0.1,
                borderDash: [5, 5]
            });
        });
        
        const config = this.getChartConfig('Network Interface Traffic', 'kB/s', datasets, allTimes);
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createNetworkErrorsChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.network_errors || data.network_errors.length === 0) {
            this.showNoDataMessage(canvas, 'No network error data available.');
            return;
        }
        
        // Aggregate errors across all interfaces
        const timeGroups = {};
        data.network_errors.forEach(d => {
            if (!timeGroups[d.time]) {
                timeGroups[d.time] = { 
                    rxerr: 0, txerr: 0, coll: 0, 
                    rxdrop: 0, txdrop: 0 
                };
            }
            timeGroups[d.time].rxerr += d.rxerr_s || 0;
            timeGroups[d.time].txerr += d.txerr_s || 0;
            timeGroups[d.time].coll += d.coll_s || 0;
            timeGroups[d.time].rxdrop += d.rxdrop_s || 0;
            timeGroups[d.time].txdrop += d.txdrop_s || 0;
        });
        
        const labels = Object.keys(timeGroups).sort();
        const datasets = [
            {
                label: 'RX Errors/s',
                data: labels.map(t => timeGroups[t].rxerr),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1
            },
            {
                label: 'TX Errors/s',
                data: labels.map(t => timeGroups[t].txerr),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1
            },
            {
                label: 'Collisions/s',
                data: labels.map(t => timeGroups[t].coll),
                borderColor: this.colors.purple.border,
                backgroundColor: this.colors.purple.bg,
                tension: 0.1
            },
            {
                label: 'RX Drops/s',
                data: labels.map(t => timeGroups[t].rxdrop),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1
            },
            {
                label: 'TX Drops/s',
                data: labels.map(t => timeGroups[t].txdrop),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('Network Errors & Drops', 'Errors/s', datasets, labels);
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createNfsClientChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.nfs_client || data.nfs_client.length === 0) {
            this.showNoDataMessage(canvas, 'No NFS client data available.');
            return;
        }
        
        const labels = data.nfs_client.map(d => d.time);
        const datasets = [
            {
                label: 'Calls/s',
                data: data.nfs_client.map(d => d.call_s || 0),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1, fill: true
            },
            {
                label: 'Retransmissions/s',
                data: data.nfs_client.map(d => d.retrans_s || 0),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1
            },
            {
                label: 'Read/s',
                data: data.nfs_client.map(d => d.read_s || 0),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1
            },
            {
                label: 'Write/s',
                data: data.nfs_client.map(d => d.write_s || 0),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1
            },
            {
                label: 'Access/s',
                data: data.nfs_client.map(d => d.access_s || 0),
                borderColor: this.colors.success.border,
                backgroundColor: this.colors.success.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('NFS Client RPC Statistics', 'Operations/s', datasets, labels);
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createNfsServerChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.nfs_server || data.nfs_server.length === 0) {
            this.showNoDataMessage(canvas, 'No NFS server data available.');
            return;
        }
        
        const labels = data.nfs_server.map(d => d.time);
        const datasets = [
            {
                label: 'Server Calls/s (scall/s)',
                data: data.nfs_server.map(d => d.scall_s || 0),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1, fill: true
            },
            {
                label: 'Bad Calls/s',
                data: data.nfs_server.map(d => d.badcall_s || 0),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1
            },
            {
                label: 'Cache Hits/s',
                data: data.nfs_server.map(d => d.hit_s || 0),
                borderColor: this.colors.success.border,
                backgroundColor: this.colors.success.bg,
                tension: 0.1
            },
            {
                label: 'Cache Misses/s',
                data: data.nfs_server.map(d => d.miss_s || 0),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1
            },
            {
                label: 'Server Read/s',
                data: data.nfs_server.map(d => d.sread_s || 0),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1
            },
            {
                label: 'Server Write/s',
                data: data.nfs_server.map(d => d.swrite_s || 0),
                borderColor: this.colors.purple.border,
                backgroundColor: this.colors.purple.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('NFS Server RPC Statistics', 'Operations/s', datasets, labels);
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createSocketsChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.sockets || data.sockets.length === 0) {
            this.showNoDataMessage(canvas, 'No socket usage data available.');
            return;
        }
        
        const labels = data.sockets.map(d => d.time);
        const datasets = [
            {
                label: 'Total Sockets',
                data: data.sockets.map(d => d.totsck || 0),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1, fill: true
            },
            {
                label: 'TCP Sockets',
                data: data.sockets.map(d => d.tcpsck || 0),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1
            },
            {
                label: 'UDP Sockets',
                data: data.sockets.map(d => d.udpsck || 0),
                borderColor: this.colors.success.border,
                backgroundColor: this.colors.success.bg,
                tension: 0.1
            },
            {
                label: 'RAW Sockets',
                data: data.sockets.map(d => d.rawsck || 0),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1
            },
            {
                label: 'TCP Time Wait',
                data: data.sockets.map(d => d.tcp_tw || 0),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('Socket Usage', 'Socket Count', datasets, labels);
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
    
    createSoftnetChart(data) {
        const canvas = document.getElementById('sar-graph');
        if (!data.softnet || data.softnet.length === 0) {
            this.showNoDataMessage(canvas, 'No softnet statistics available.');
            return;
        }
        
        // Filter to 'all' CPU data only for overview
        const softnetAllData = data.softnet.filter(d => d.cpu === 'all');
        if (softnetAllData.length === 0) {
            this.showNoDataMessage(canvas, 'No aggregated softnet data available.');
            return;
        }
        
        const labels = softnetAllData.map(d => d.time);
        const datasets = [
            {
                label: 'Total Packets/s',
                data: softnetAllData.map(d => d.total_s || 0),
                borderColor: this.colors.primary.border,
                backgroundColor: this.colors.primary.bg,
                tension: 0.1, fill: true
            },
            {
                label: 'Dropped/s',
                data: softnetAllData.map(d => d.dropd_s || 0),
                borderColor: this.colors.danger.border,
                backgroundColor: this.colors.danger.bg,
                tension: 0.1
            },
            {
                label: 'Time Squeezed/s',
                data: softnetAllData.map(d => d.squeezd_s || 0),
                borderColor: this.colors.warning.border,
                backgroundColor: this.colors.warning.bg,
                tension: 0.1
            },
            {
                label: 'RX RPS/s',
                data: softnetAllData.map(d => d.rx_rps_s || 0),
                borderColor: this.colors.secondary.border,
                backgroundColor: this.colors.secondary.bg,
                tension: 0.1
            },
            {
                label: 'Flow Limit/s',
                data: softnetAllData.map(d => d.flw_lim_s || 0),
                borderColor: this.colors.purple.border,
                backgroundColor: this.colors.purple.bg,
                tension: 0.1
            }
        ];
        
        const config = this.getChartConfig('Softnet Statistics', 'Packets/s', datasets, labels);
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, config);
    }
}
