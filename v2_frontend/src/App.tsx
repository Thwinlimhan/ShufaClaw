import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { 
  Activity, 
  BarChart3, 
  Settings2, 
  ShieldAlert, 
  Crosshair,
  TrendingUp,
  Terminal,
  ServerCrash
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from './api';

interface SystemMetrics {
  health_status: string;
  ingestion_lag_ms: number;
  execution_latency_ms: number;
  active_strategies: number;
  api_errors_1h: number;
  last_updated: string;
}

export default function App() {
  return (
    <BrowserRouter>
      <DashboardLayout />
    </BrowserRouter>
  );
}

function DashboardLayout() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await api.monitoring.summary();
        setMetrics(data);
        setError(false);
      } catch {
        setError(true);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen bg-darkBg text-slate overflow-hidden font-sans">
      
      {/* Sidebar */}
      <aside className="w-64 border-r border-muted bg-[#0e1118] flex flex-col justify-between">
        <div>
          <div className="p-6 border-b border-muted">
            <h1 className="text-xl font-bold flex items-center space-x-2 text-white">
              <Crosshair className="text-neonBlue" size={24}/>
              <span>ShufaClaw </span>
              <span className="text-xs text-neonPurple font-mono bg-neonPurple/10 px-2 py-0.5 rounded">V2</span>
            </h1>
          </div>
          <nav className="p-4 space-y-2">
            <NavItem to="/" icon={<BarChart3 />} label="Portfolio Overview" />
            <NavItem to="/market" icon={<Activity />} label="Market Intelligence" />
            <NavItem to="/strategy" icon={<TrendingUp />} label="Strategy Lab" />
            <NavItem to="/execution" icon={<Terminal />} label="Execution Analytics" />
            <NavItem to="/risk" icon={<ShieldAlert />} label="Risk Dashboard" />
            <NavItem to="/settings" icon={<Settings2 />} label="System Config" />
          </nav>
        </div>
        <div className="p-6 border-t border-muted text-xs">
          Institutional Quant Platform
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-8 overflow-y-auto">
        {/* Global HUD Header */}
        <header className="flex justify-end items-center mb-8">
          <div className="flex space-x-4">
            {error ? (
              <div className="flex items-center space-x-2 px-4 py-2 rounded-full border border-bearish text-bearish bg-bearish/10">
                <ServerCrash size={16} />
                <span className="font-mono text-sm">Backend Offline</span>
              </div>
            ) : (
              <div className="flex items-center space-x-2 px-4 py-2 rounded-full border border-bullish text-bullish bg-bullish/10">
                <div className="w-2 h-2 rounded-full bg-bullish animate-pulse"></div>
                <span className="font-mono text-sm">System Ops Normal</span>
              </div>
            )}
            
            {/* Live Global Metric Chips */}
            <div className="flex items-center space-x-2 px-3 py-1 rounded-md border border-muted bg-[#12151c] text-xs font-mono">
              <span className="opacity-50">Ingestion:</span> 
              <span className={metrics && metrics.ingestion_lag_ms > 2000 ? "text-[#FFB300]" : "text-bullish"}>
                {metrics ? `${metrics.ingestion_lag_ms.toFixed(0)}ms` : '--'}
              </span>
            </div>
            <div className="flex items-center space-x-2 px-3 py-1 rounded-md border border-muted bg-[#12151c] text-xs font-mono">
              <span className="opacity-50">Execution:</span> 
              <span className={metrics && metrics.execution_latency_ms > 1000 ? "text-[#FFB300]" : "text-bullish"}>
                {metrics ? `${metrics.execution_latency_ms.toFixed(0)}ms` : '--'}
              </span>
            </div>
          </div>
        </header>

        {/* Page Routing */}
        <Routes>
          <Route path="/" element={<PortfolioOverview metrics={metrics} />} />
          <Route path="/market" element={<MarketIntelligence />} />
          <Route path="/strategy" element={<StrategyLab />} />
          <Route path="/execution" element={<ExecutionAnalytics />} />
          <Route path="/risk" element={<RiskDashboard />} />
          <Route path="/settings" element={<PagePlaceholder title="System Hooks" desc="Exchange API Keys, Telegram integrations, and Model configs." icon={<Settings2 size={48} className="text-white" />} />} />
        </Routes>
      </main>
    </div>
  );
}

// ---------------------------------------------------------
// Subcomponents
// ---------------------------------------------------------

function NavItem({ to, icon, label }: { to: string, icon: React.ReactNode, label: string }) {
  const location = useLocation();
  const active = location.pathname === to;
  
  return (
    <Link to={to}>
      <div className={`flex items-center space-x-3 px-4 py-3 rounded-lg cursor-pointer transition-all duration-200 ${
        active 
        ? 'bg-neonBlue/10 text-neonBlue border border-neonBlue/20 shadow-[0_0_15px_rgba(0,240,255,0.1)]' 
        : 'hover:bg-muted text-slate hover:text-white'
      }`}>
        <span className={active ? '' : 'opacity-70'}>{icon}</span>
        <span className="font-medium text-sm">{label}</span>
      </div>
    </Link>
  );
}

function PagePlaceholder({ title, desc, icon }: { title: string, desc: string, icon: React.ReactNode }) {
  return (
    <div className="h-full flex flex-col items-center justify-center p-12 text-center opacity-80 mt-12">
      <div className="mb-6 p-6 rounded-full bg-muted/30 border border-muted">{icon}</div>
      <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">{title}</h2>
      <p className="text-slate max-w-md">{desc}</p>
      <div className="mt-8 px-4 py-2 border border-neonBlue text-neonBlue text-xs rounded animate-pulse font-mono">
        MODULE LOADING...
      </div>
    </div>
  );
}

// ---------------------------------------------------------
// Actual Pages
// ---------------------------------------------------------

function PortfolioOverview({ metrics }: { metrics: SystemMetrics | null }) {
  const performanceData = [
    { time: '10:00', nav: 100000, expected: 100000 },
    { time: '11:00', nav: 101200, expected: 100500 },
    { time: '12:00', nav: 100800, expected: 101000 },
    { time: '13:00', nav: 102500, expected: 101500 },
    { time: '14:00', nav: 104000, expected: 102000 },
  ];

  return (
    <div className="animate-in fade-in duration-500">
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-white">Portfolio Overview</h2>
        <p className="text-sm mt-1">Real-time delta-neutral execution telemetry</p>
      </div>

      <div className="grid grid-cols-4 gap-6 mb-8">
        <MetricCard 
          title="Active Capital (USD)" 
          value="$104,000" 
          sub="+4.0% Today"
          status="good"
        />
        <MetricCard 
          title="Max Drawdown" 
          value="1.2%" 
          sub="Limit: 15.0%"
          status="good"
        />
        <MetricCard 
          title="Active Strategies" 
          value={metrics ? metrics.active_strategies : '--'} 
          sub="Deployed on Mainnet"
          status="info"
        />
        <MetricCard 
          title="API Errors (1h)" 
          value={metrics ? metrics.api_errors_1h : '--'} 
          sub="Recovered by retries"
          status={metrics && metrics.api_errors_1h > 10 ? 'danger' : 'info'}
        />
      </div>

      <div className="glass-panel p-6 mb-8 h-[400px]">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-white">Live NAV vs Expected (Paper)</h3>
          <div className="flex items-center space-x-4 text-xs font-mono">
            <div className="flex items-center"><div className="w-3 h-3 bg-neonBlue mr-2 rounded-sm"></div> Actual NAV</div>
            <div className="flex items-center"><div className="w-3 h-3 bg-neonPurple mr-2 rounded-sm"></div> Strategy Expected</div>
          </div>
        </div>
        
        <ResponsiveContainer width="100%" height="80%">
          <LineChart data={performanceData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2A2E39" vertical={false}/>
            <XAxis dataKey="time" stroke="#8D99AE" tickLine={false} axisLine={false} />
            <YAxis stroke="#8D99AE" tickLine={false} axisLine={false} domain={['dataMin - 1000', 'dataMax + 1000']} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#151924', borderColor: '#2A2E39', borderRadius: '8px' }}
              itemStyle={{ color: '#fff' }}
            />
            <Line type="monotone" dataKey="nav" stroke="#00F0FF" strokeWidth={3} dot={{ r: 4, fill: "#00F0FF" }} activeDot={{ r: 6 }} />
            <Line type="monotone" dataKey="expected" stroke="#8A2BE2" strokeWidth={2} strokeDasharray="5 5" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function MetricCard({ title, value, sub, status }: { title: string, value: string | number, sub: string, status: 'good' | 'warn' | 'danger' | 'info' }) {
  const colors = {
    good: 'text-bullish',
    warn: 'text-[#FFB300]',
    danger: 'text-bearish',
    info: 'text-neonBlue'
  };

  return (
    <div className="glass-panel p-5 relative overflow-hidden group">
      <div className={`absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-transparent to-current opacity-5 pointer-events-none ${colors[status]}`}></div>
      <h4 className="text-sm font-medium mb-1">{title}</h4>
      <div className={`text-3xl font-bold font-mono ${colors[status]} tracking-tight`}>
        {value}
      </div>
      <div className="text-xs mt-2 opacity-60">
        {sub}
      </div>
    </div>
  );
}

// ---------------------------------------------------------
// V2 Data Pages (wired to real APIs)
// ---------------------------------------------------------

function MarketIntelligence() {
  const [data, setData] = useState<{ vector: Record<string, unknown>; regime: string } | null>(null);
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.features(symbol).then((res) => {
      if (!cancelled && res.status === 'success') setData(res.data);
    }).catch((e) => { if (!cancelled) setErr(String(e)); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [symbol]);

  return (
    <div className="animate-in fade-in duration-500">
      <div className="mb-8 flex justify-between items-center">
        <h2 className="text-2xl font-semibold text-white">Market Intelligence</h2>
        <select value={symbol} onChange={(e) => setSymbol(e.target.value)} className="bg-[#12151c] border border-muted rounded px-3 py-2 text-sm">
          <option value="BTCUSDT">BTC/USDT</option>
          <option value="ETHUSDT">ETH/USDT</option>
          <option value="SOLUSDT">SOL/USDT</option>
        </select>
      </div>
      {loading && <div className="text-slate">Loading features...</div>}
      {err && <div className="text-bearish">Error: {err}</div>}
      {data && (
        <div className="space-y-6">
          <div className="glass-panel p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Current Regime</h3>
            <div className="text-2xl font-mono text-neonBlue">{data.regime}</div>
          </div>
          <div className="glass-panel p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Feature Vector</h3>
            <pre className="text-xs text-slate overflow-auto max-h-96">{JSON.stringify(data.vector, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
}

function StrategyLab() {
  const [strategies, setStrategies] = useState<unknown[]>([]);
  const [backtests, setBacktests] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.v2.strategies(), api.v2.backtests(undefined, undefined, 20)])
      .then(([s, b]) => {
        if (!cancelled) {
          setStrategies((s as { data: unknown[] }).data || []);
          setBacktests((b as { data: unknown[] }).data || []);
        }
      })
      .catch((e) => { if (!cancelled) setErr(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="animate-in fade-in duration-500">
      <h2 className="text-2xl font-semibold text-white mb-8">Strategy Lab</h2>
      {loading && <div className="text-slate">Loading...</div>}
      {err && <div className="text-bearish">Error: {err}</div>}
      {!loading && !err && (
        <div className="grid grid-cols-2 gap-6">
          <div className="glass-panel p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Strategies ({strategies.length})</h3>
            <div className="space-y-2 max-h-80 overflow-auto">
              {strategies.length === 0 ? <p className="text-slate text-sm">No strategies yet. Run discovery to populate.</p> : strategies.map((s: unknown, i) => (
                <div key={i} className="border border-muted rounded p-3 text-sm">
                  <pre className="text-xs truncate">{JSON.stringify(s)}</pre>
                </div>
              ))}
            </div>
          </div>
          <div className="glass-panel p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Backtests ({backtests.length})</h3>
            <div className="space-y-2 max-h-80 overflow-auto">
              {backtests.length === 0 ? <p className="text-slate text-sm">No backtests yet.</p> : backtests.map((b: unknown, i) => (
                <div key={i} className="border border-muted rounded p-3 text-sm">
                  <pre className="text-xs truncate">{JSON.stringify(b)}</pre>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ExecutionAnalytics() {
  const [orders, setOrders] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.v2.orders(undefined, 50).then((res) => {
      if (!cancelled && res.status === 'success') setOrders(res.data || []);
    }).catch((e) => { if (!cancelled) setErr(String(e)); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="animate-in fade-in duration-500">
      <h2 className="text-2xl font-semibold text-white mb-8">Execution Analytics</h2>
      {loading && <div className="text-slate">Loading orders...</div>}
      {err && <div className="text-bearish">Error: {err}</div>}
      {!loading && !err && (
        <div className="glass-panel p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Order History ({orders.length})</h3>
          {orders.length === 0 ? <p className="text-slate text-sm">No orders yet. Paper/live executions will appear here.</p> : (
            <div className="space-y-2 max-h-96 overflow-auto">
              {orders.map((o: unknown, i) => (
                <div key={i} className="border border-muted rounded p-3 text-sm font-mono">
                  <pre className="text-xs">{JSON.stringify(o, null, 2)}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RiskDashboard() {
  const [events, setEvents] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.v2.riskEvents(50).then((res) => {
      if (!cancelled && res.status === 'success') setEvents(res.data || []);
    }).catch((e) => { if (!cancelled) setErr(String(e)); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="animate-in fade-in duration-500">
      <h2 className="text-2xl font-semibold text-white mb-8">Risk Dashboard</h2>
      {loading && <div className="text-slate">Loading risk events...</div>}
      {err && <div className="text-bearish">Error: {err}</div>}
      {!loading && !err && (
        <div className="glass-panel p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Risk Events ({events.length})</h3>
          {events.length === 0 ? <p className="text-slate text-sm">No risk events. System operating within limits.</p> : (
            <div className="space-y-2 max-h-96 overflow-auto">
              {events.map((e: unknown, i) => (
                <div key={i} className="border border-muted rounded p-3 text-sm">
                  <pre className="text-xs">{JSON.stringify(e, null, 2)}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
