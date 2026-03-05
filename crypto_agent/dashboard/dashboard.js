document.addEventListener('alpine:init', () => {
    Alpine.data('dashboardData', () => ({
        currentPage: 'command_center',
        streamActive: false,
        currentTime: '',
        searchOpen: false,
        notifOpen: false,
        searchQuery: '',
        searchResults: [],
        logFilter: 'all',
        logEntries: [],
        logPollInterval: null,
        dashStats: {},

        navItems: [
            { id: 'command_center', name: 'Command Center', icon: '⎈' },
            { id: 'portfolio', name: 'Portfolio Map', icon: '⟡' },
            { id: 'scanner', name: 'Arbitrage Scanner', icon: '⌖' },
            { id: 'alerts', name: 'Active Triggers', icon: '⚡' },
            { id: 'journal', name: 'Cognitive Journal', icon: '✧' },
            { id: 'analytics', name: 'Deep Analytics', icon: '∿' },
            { id: 'chat', name: 'Neural Chat', icon: '⍜' },
            { id: 'onchain', name: 'On-Chain Grid', icon: '⎉' },
            { id: 'airdrops', name: 'Airdrop Hub', icon: '⚲' },
            { id: 'scheduler', name: 'Scheduler', icon: '⏱' },
            { id: 'logs', name: 'Live Logs', icon: '📋' },
            { id: 'settings', name: 'System Core', icon: '⚙' }
        ],

        scheduledTasks: [
            { name: 'Morning Briefing', schedule: 'Daily 8:00 AM', icon: '☀️', status: 'active' },
            { name: 'Evening Summary', schedule: 'Daily 9:00 PM', icon: '🌙', status: 'active' },
            { name: 'Price Alert Scan', schedule: 'Every 30s', icon: '🔔', status: 'active' },
            { name: 'Market Scanner', schedule: 'Every 5 min', icon: '📡', status: 'active' },
            { name: 'Regime Detection', schedule: 'Every 1 hr', icon: '🌡️', status: 'active' },
            { name: 'Smart Money Watch', schedule: 'Every 15 min', icon: '🐋', status: 'active' },
            { name: 'News Sentiment', schedule: 'Every 30 min', icon: '📰', status: 'active' },
            { name: 'Weekly Review', schedule: 'Sun 6:00 PM', icon: '📊', status: 'active' },
            { name: 'Weekly Research', schedule: 'Fri 10:00 AM', icon: '🔬', status: 'active' },
            { name: 'Risk Review', schedule: 'Daily 3:00 PM', icon: '⚠️', status: 'active' },
            { name: 'Auto Backup', schedule: 'Mon 8:00 AM', icon: '💾', status: 'active' },
            { name: 'Prediction Verify', schedule: 'Every 6 hrs', icon: '🎯', status: 'active' },
        ],

        notifications: [
            { icon: '⚡', message: 'BTC crossed $97,000 resistance level', time: '2 mins ago', type: 'alert' },
            { icon: '📡', message: 'Market Scanner found 3 new opportunities', time: '15 mins ago', type: 'scan' },
            { icon: '🐋', message: 'Whale alert: 1,245 BTC moved from Coinbase', time: '1 hr ago', type: 'whale' },
        ],

        // Searchable items with descriptions
        searchableItems: [],

        state: {
            portfolio_value: 58350.50,
            portfolio_change_24h: 1.8,
            btc_price: 97500,
            eth_price: 3100,
            fear_greed: 67,
            active_alerts: 12,
            activity_log: [
                { type: 'alert', message: 'BTC/USDT structural resistance at $97,000 crossed. Shift to momentum tracking.', time: '2 mins ago', severity: 'HIGH' },
                { type: 'scan', message: 'ETH establishing oversold divergence on H4 interval.', time: '15 mins ago', severity: 'MEDIUM' },
                { type: 'journal', message: 'Execution logged: SOL long scaling entry.', time: '1 hr ago' },
                { type: 'system', message: 'Cognitive loop finalized daily tactical synthesis.', time: '3 hrs ago', severity: 'LOW' }
            ],
            system: { cpu: 0, memory: 0, disk: 0, uptime: '0h 0m 0s', memory_used_gb: 0, memory_total_gb: 0, disk_used_gb: 0, disk_total_gb: 0 }
        },

        init() {
            Chart.defaults.color = '#94A3B8';
            Chart.defaults.font.family = 'Outfit';

            // Build searchable items from nav
            this.searchableItems = this.navItems.map(n => ({
                ...n,
                desc: this.getPageDesc(n.id)
            }));
            this.searchResults = [...this.searchableItems];

            this.initCharts();
            this.connectSSE();
            this.updateTime();
            setInterval(() => this.updateTime(), 1000);
            this.pollLogs();
            this.fetchStats();
            setInterval(() => this.fetchStats(), 30000);
        },

        getPageDesc(id) {
            const descs = {
                'command_center': 'Overview dashboard with charts and health',
                'portfolio': 'Asset allocation and holdings',
                'scanner': 'Arbitrage opportunity detection',
                'alerts': 'Price triggers and thresholds',
                'journal': 'Trade journal and cognitive memory',
                'analytics': 'Win rate, profit factor, drawdown',
                'chat': 'AI assistant neural link',
                'onchain': 'Whale tracking and blockchain data',
                'airdrops': 'Protocol airdrop tracker',
                'scheduler': 'Cron jobs and scheduled tasks',
                'logs': 'Real-time system log viewer',
                'settings': 'System configuration and toggles'
            };
            return descs[id] || '';
        },

        handleKeydown(e) {
            // Ctrl+K or Cmd+K to open search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.searchOpen = !this.searchOpen;
                if (this.searchOpen) {
                    this.$nextTick(() => this.$refs.searchInput?.focus());
                }
            }
            // Escape to close modals
            if (e.key === 'Escape') {
                this.searchOpen = false;
                this.notifOpen = false;
            }
            // Number shortcuts 1-9 for nav (when not typing)
            if (!this.searchOpen && !e.ctrlKey && !e.metaKey && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
                const num = parseInt(e.key);
                if (num >= 1 && num <= this.navItems.length) {
                    this.currentPage = this.navItems[num - 1].id;
                }
            }
        },

        filterSearch() {
            const q = this.searchQuery.toLowerCase().trim();
            if (!q) {
                this.searchResults = [...this.searchableItems];
                return;
            }
            this.searchResults = this.searchableItems.filter(item =>
                item.name.toLowerCase().includes(q) ||
                item.desc.toLowerCase().includes(q)
            );
        },

        async fetchStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                if (data.status === 'success') {
                    this.dashStats = data.data;
                }
            } catch (e) {
                // Stats fetch failed silently
            }
        },

        async pollLogs() {
            const fetchLogs = async () => {
                try {
                    const res = await fetch('/api/logs');
                    const data = await res.json();
                    if (data.status === 'success') {
                        this.logEntries = data.data;
                    }
                } catch (e) { /* silent */ }
            };
            await fetchLogs();
            this.logPollInterval = setInterval(fetchLogs, 3000);
        },

        filteredLogs() {
            if (this.logFilter === 'all') return this.logEntries;
            return this.logEntries.filter(l => l.level === this.logFilter);
        },

        updateTime() {
            const now = new Date();
            this.currentTime = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' TST';
        },

        connectSSE() {
            const evtSource = new EventSource("/api/stream");
            this.streamActive = true;

            evtSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.btc_price !== undefined) {
                        this.state = { ...this.state, ...data };
                        this.streamActive = true;
                    }
                } catch (e) {
                    console.error("Stream disrupted", e);
                }
            };
            evtSource.onerror = () => {
                this.streamActive = false;
            };
        },

        formatNumber(num) {
            return parseFloat(num).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        },

        formatPercent(num) {
            const prefix = num > 0 ? '+' : '';
            return prefix + parseFloat(num).toFixed(2) + '%';
        },

        getIconForType(type) {
            const icons = { 'alert': '⚡', 'scan': '⌖', 'journal': '✧', 'system': '⚙', 'trade': '⟡' };
            return icons[type] || '⎈';
        },

        initCharts() {
            // Donut Chart
            const donutEl = document.getElementById('portfolioDonut');
            if (!donutEl) return;
            const ctxDonut = donutEl.getContext('2d');

            const gradientBTC = ctxDonut.createLinearGradient(0, 0, 0, 400);
            gradientBTC.addColorStop(0, '#F59E0B'); gradientBTC.addColorStop(1, '#B45309');
            const gradientETH = ctxDonut.createLinearGradient(0, 0, 0, 400);
            gradientETH.addColorStop(0, '#7C3AED'); gradientETH.addColorStop(1, '#4C1D95');
            const gradientSOL = ctxDonut.createLinearGradient(0, 0, 0, 400);
            gradientSOL.addColorStop(0, '#10B981'); gradientSOL.addColorStop(1, '#047857');
            const gradientUSDC = ctxDonut.createLinearGradient(0, 0, 0, 400);
            gradientUSDC.addColorStop(0, '#3B82F6'); gradientUSDC.addColorStop(1, '#1D4ED8');

            new Chart(ctxDonut, {
                type: 'doughnut',
                data: {
                    labels: ['BTC', 'ETH', 'SOL', 'USDC'],
                    datasets: [{
                        data: [45, 30, 15, 10],
                        backgroundColor: [gradientBTC, gradientETH, gradientSOL, gradientUSDC],
                        borderWidth: 2, borderColor: '#141419', hoverOffset: 8
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true, pointStyle: 'circle' } } },
                    cutout: '80%', layout: { padding: 10 }
                }
            });

            // Line Chart
            const lineEl = document.getElementById('equityCurve');
            if (!lineEl) return;
            const ctxLine = lineEl.getContext('2d');
            const gradientLine = ctxLine.createLinearGradient(0, 0, 0, 400);
            gradientLine.addColorStop(0, 'rgba(124, 58, 237, 0.5)');
            gradientLine.addColorStop(1, 'rgba(124, 58, 237, 0.01)');

            const labels = Array.from({ length: 30 }, (_, i) => `D${i + 1}`);
            const dataPoints = [];
            let val = 50000;
            for (let i = 0; i < 30; i++) {
                val = val + (Math.random() - 0.4) * 1200;
                dataPoints.push(val);
            }

            new Chart(ctxLine, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'Net Equity', data: dataPoints,
                        borderColor: '#A78BFA', backgroundColor: gradientLine,
                        borderWidth: 3, fill: true, tension: 0.4,
                        pointRadius: 0, pointHoverRadius: 6,
                        pointHoverBackgroundColor: '#FFF',
                        pointHoverBorderColor: '#A78BFA', pointHoverBorderWidth: 3
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(20, 20, 25, 0.9)',
                            titleFont: { family: 'Outfit', size: 13 },
                            bodyFont: { family: 'Outfit', size: 14, weight: 'bold' },
                            padding: 12, displayColors: false,
                            callbacks: { label: ctx => '$' + ctx.parsed.y.toLocaleString() }
                        }
                    },
                    scales: {
                        x: { display: false },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                            ticks: { callback: v => '$' + v / 1000 + 'k', padding: 10 }
                        }
                    },
                    interaction: { mode: 'index', intersect: false }
                }
            });
        }
    }));
});
