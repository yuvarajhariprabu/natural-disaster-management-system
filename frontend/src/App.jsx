import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, ShieldAlert, Droplets, CloudRain, AlertOctagon, 
  CheckCircle2, TrendingUp, RefreshCw, Radio, MapPin, Wifi, WifiOff 
} from 'lucide-react';
import { 
  MapContainer, TileLayer, CircleMarker, Popup 
} from 'react-leaflet';
import { 
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid 
} from 'recharts';

export default function App() {
  const [data, setData] = useState({
    overall_risk: 0,
    landslide_risk: 0,
    flood_risk: 0,
    severity: 'SAFE',
    reasons: ['Initialising system data...'],
    nodes: [],
    latest_readings: [],
    active_alerts: []
  });

  const [history, setHistory] = useState([]);
  const [activeChartTab, setActiveChartTab] = useState('landslide');
  const [connectionStatus, setConnectionStatus] = useState('CONNECTING');
  const [activeScenario, setActiveScenario] = useState('normal');
  const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString());

  const wsRef = useRef(null);

  // Update clock every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Set up WebSocket connection with REST fallback
  useEffect(() => {
    let restPollingTimer = null;

    function connectWS() {
      console.log("Connecting WebSocket...");
      const ws = new WebSocket(`ws://${window.location.hostname}:8000/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected.");
        setConnectionStatus('CONNECTED');
        if (restPollingTimer) {
          clearInterval(restPollingTimer);
          restPollingTimer = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          setData(payload);
        } catch (e) {
          console.error("Error parsing WebSocket payload:", e);
        }
      };

      ws.onclose = () => {
        console.log("WebSocket connection closed. Switching to polling fallback...");
        setConnectionStatus('DISCONNECTED');
        // Start REST polling fallback
        if (!restPollingTimer) {
          fetchSummary(); // immediate fetch
          restPollingTimer = setInterval(fetchSummary, 3000);
        }
        // Try to reconnect in 5 seconds
        setTimeout(connectWS, 5000);
      };

      ws.onerror = (err) => {
        console.error("WebSocket error observed:", err);
      };
    }

    connectWS();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (restPollingTimer) clearInterval(restPollingTimer);
    };
  }, []);

  // Fetch chart history every 5 seconds
  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchSummary = async () => {
    try {
      const response = await fetch(`http://${window.location.hostname}:8000/api/summary`);
      if (response.ok) {
        const payload = await response.json();
        setData(payload);
      }
    } catch (e) {
      console.error("Failed to fetch summary:", e);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch(`http://${window.location.hostname}:8000/api/readings?limit=30`);
      if (response.ok) {
        const readings = await response.json();
        // format history: reverse readings to chronological order
        const formatted = readings.reverse().map(r => ({
          time: new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          soil_moisture: r.soil_moisture,
          vibration: r.vibration,
          water_level: r.water_level,
          rainfall: r.rainfall,
          node_id: r.node_id
        }));
        setHistory(formatted);
      }
    } catch (e) {
      console.error("Failed to fetch readings history:", e);
    }
  };

  const triggerScenario = async (scenario) => {
    try {
      setActiveScenario(scenario);
      const response = await fetch(`http://${window.location.hostname}:8000/api/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario })
      });
      if (response.ok) {
        fetchHistory(); // refresh charts immediately
      }
    } catch (e) {
      console.error("Failed to trigger simulation scenario:", e);
    }
  };

  const acknowledgeAlert = async (alertId) => {
    try {
      const response = await fetch(`http://${window.location.hostname}:8000/api/alerts/${alertId}/acknowledge`, {
        method: 'POST'
      });
      if (response.ok) {
        // WebSocket updates summary automatically, but trigger fallback just in case
        if (connectionStatus === 'DISCONNECTED') {
          fetchSummary();
        }
      }
    } catch (e) {
      console.error("Failed to acknowledge alert:", e);
    }
  };

  // Helper to color statuses
  const getSeverityClass = (sev) => {
    switch (sev) {
      case 'SAFE': return 'text-safe bg-safe glow-safe';
      case 'LOW': return 'text-low bg-low glow-low';
      case 'WARNING': return 'text-warning bg-warning glow-warning';
      case 'HIGH': return 'text-high bg-high glow-high';
      case 'CRITICAL': return 'text-critical bg-critical glow-critical';
      default: return '';
    }
  };

  const getCircleColor = (status) => {
    switch (status) {
      case 'SAFE': return '#10b981';
      case 'LOW': return '#3b82f6';
      case 'WARNING': return '#f59e0b';
      case 'HIGH': return '#f97316';
      case 'CRITICAL': return '#ef4444';
      default: return '#6b7280';
    }
  };

  // Extract node specific latest values
  const getNodeReading = (nodeId) => {
    return data.latest_readings.find(r => r.node_id === nodeId) || {};
  };

  const n1Reading = getNodeReading('NODE1');
  const n2Reading = getNodeReading('NODE2');
  const n3Reading = getNodeReading('NODE3');

  const n1Status = data.nodes.find(n => n.id === 'NODE1') || {};
  const n2Status = data.nodes.find(n => n.id === 'NODE2') || {};
  const n3Status = data.nodes.find(n => n.id === 'NODE3') || {};

  // Filter history data for specific chart segments
  const getChartData = (type) => {
    if (type === 'landslide') {
      return history.filter(h => h.node_id === 'NODE1');
    } else if (type === 'flood') {
      return history.filter(h => h.node_id === 'NODE2');
    } else if (type === 'rain') {
      return history.filter(h => h.node_id === 'NODE3');
    }
    return [];
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-logo">
          <div className="logo-icon">
            <ShieldAlert size={24} color="#fff" />
          </div>
          <div className="logo-text">
            <h1>D-SHIELD</h1>
            <p>Rural Disaster Early Warning Layer</p>
          </div>
        </div>
        
        <div className="header-status">
          <div className="status-badge">
            <span className="status-indicator" style={{ backgroundColor: connectionStatus === 'CONNECTED' ? '#10b981' : '#ef4444' }}></span>
            <span style={{ color: connectionStatus === 'CONNECTED' ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
              LOCAL GATEWAY: {connectionStatus}
            </span>
            {connectionStatus === 'CONNECTED' ? <Wifi size={14} className="text-safe" /> : <WifiOff size={14} className="text-critical" />}
          </div>
          <div className="status-badge">
            <Activity size={14} className="text-low" />
            <span>TIME: {currentTime}</span>
          </div>
        </div>
      </header>

      {/* Main Grid Content */}
      <main className="dashboard-content">
        {/* Left Column */}
        <div className="main-column">
          {/* Overall Risk Card */}
          <div className="card-glass overall-risk-card">
            <div className="risk-dial-container">
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                Overall Risk Index
              </span>
              <div className="risk-percentage" style={{
                color: getCircleColor(data.severity)
              }}>
                {Math.round(data.overall_risk)}%
              </div>
              <div className={`risk-level-tag ${getSeverityClass(data.severity)}`} style={{ color: '#fff' }}>
                {data.severity}
              </div>
            </div>
            <div className="risk-details">
              <h2>Early Warning Status & Data Fusion Reasons</h2>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                Explainable risk calculations fused from distributed remote field nodes:
              </p>
              <ul className="reasons-list">
                {data.reasons.map((reason, idx) => (
                  <li key={idx}>
                    <AlertOctagon size={16} className={getSeverityClass(data.severity).split(' ')[0]} style={{ marginTop: '3px' }} />
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Node Status Grid */}
          <div className="node-cards-grid">
            {/* Node 1 */}
            <div className={`card-glass node-card ${n1Status.status === 'OFFLINE' ? 'OFFLINE' : (data.landslide_risk > 70 ? 'CRITICAL' : data.landslide_risk > 50 ? 'WARNING' : 'SAFE')}`}>
              <div className="node-card-header">
                <div className="node-title">
                  <h3>🏔️ Mountain Node</h3>
                  <span className="node-subtitle">{n1Status.location || 'Landslide Monitoring'}</span>
                </div>
                <div className={`status-badge ${n1Status.status === 'ONLINE' ? 'text-safe' : 'text-critical'}`}>
                  {n1Status.status || 'OFFLINE'}
                </div>
              </div>
              
              <div className="sensor-stats">
                <div className="sensor-row">
                  <span className="sensor-label">Soil Moisture:</span>
                  <span className="sensor-val">{n1Reading.soil_moisture !== undefined ? `${n1Reading.soil_moisture.toFixed(1)}%` : 'N/A'}</span>
                </div>
                <div className="sensor-row">
                  <span className="sensor-label">Vibration Level:</span>
                  <span className="sensor-val">{n1Reading.vibration !== undefined ? `${n1Reading.vibration.toFixed(2)}g` : 'N/A'}</span>
                </div>
                <div className="sensor-row">
                  <span className="sensor-label">Calculated Risk:</span>
                  <span className="sensor-val" style={{ color: getCircleColor(data.landslide_risk > 70 ? 'CRITICAL' : data.landslide_risk > 50 ? 'WARNING' : 'SAFE') }}>
                    {Math.round(data.landslide_risk)}%
                  </span>
                </div>
              </div>

              <div className="node-card-footer">
                <span>LoRa RSSI: {n1Status.rssi || -75}dBm</span>
                <span>Pkts: {n1Status.packet_count || 0}</span>
              </div>
            </div>

            {/* Node 2 */}
            <div className={`card-glass node-card ${n2Status.status === 'OFFLINE' ? 'OFFLINE' : (data.flood_risk > 70 ? 'CRITICAL' : data.flood_risk > 50 ? 'WARNING' : 'SAFE')}`}>
              <div className="node-card-header">
                <div className="node-title">
                  <h3>🌊 River Node</h3>
                  <span className="node-subtitle">{n2Status.location || 'Flood Monitoring'}</span>
                </div>
                <div className={`status-badge ${n2Status.status === 'ONLINE' ? 'text-safe' : 'text-critical'}`}>
                  {n2Status.status || 'OFFLINE'}
                </div>
              </div>

              <div className="sensor-stats">
                <div className="sensor-row">
                  <span className="sensor-label">Water Level:</span>
                  <span className="sensor-val">{n2Reading.water_level !== undefined ? `${n2Reading.water_level.toFixed(2)}m` : 'N/A'}</span>
                </div>
                <div className="sensor-row">
                  <span className="sensor-label">Temperature / Press:</span>
                  <span className="sensor-val" style={{ fontSize: '0.8rem' }}>
                    {n2Reading.temperature !== undefined ? `${n2Reading.temperature.toFixed(1)}°C` : 'N/A'} / {n2Reading.pressure !== undefined ? `${Math.round(n2Reading.pressure)}hPa` : 'N/A'}
                  </span>
                </div>
                <div className="sensor-row">
                  <span className="sensor-label">Calculated Risk:</span>
                  <span className="sensor-val" style={{ color: getCircleColor(data.flood_risk > 70 ? 'CRITICAL' : data.flood_risk > 50 ? 'WARNING' : 'SAFE') }}>
                    {Math.round(data.flood_risk)}%
                  </span>
                </div>
              </div>

              <div className="node-card-footer">
                <span>LoRa RSSI: {n2Status.rssi || -80}dBm</span>
                <span>Pkts: {n2Status.packet_count || 0}</span>
              </div>
            </div>

            {/* Node 3 */}
            <div className={`card-glass node-card ${n3Status.status === 'OFFLINE' ? 'OFFLINE' : (n3Reading.rainfall > 40 ? 'CRITICAL' : n3Reading.rainfall > 20 ? 'WARNING' : 'SAFE')}`}>
              <div className="node-card-header">
                <div className="node-title">
                  <h3>🌧️ Aggregator Node</h3>
                  <span className="node-subtitle">{n3Status.location || 'Field Collector'}</span>
                </div>
                <div className={`status-badge ${n3Status.status === 'ONLINE' ? 'text-safe' : 'text-critical'}`}>
                  {n3Status.status || 'OFFLINE'}
                </div>
              </div>

              <div className="sensor-stats">
                <div className="sensor-row">
                  <span className="sensor-label">Rain Rate:</span>
                  <span className="sensor-val">{n3Reading.rainfall !== undefined ? `${n3Reading.rainfall.toFixed(1)} mm/h` : 'N/A'}</span>
                </div>
                <div className="sensor-row">
                  <span className="sensor-label">Gateway Bridge:</span>
                  <span className="sensor-val" style={{ color: 'var(--color-safe)' }}>USB Serial</span>
                </div>
                <div className="sensor-row">
                  <span className="sensor-label">Aggregator Health:</span>
                  <span className="sensor-val" style={{ color: 'var(--color-safe)' }}>NORMAL</span>
                </div>
              </div>

              <div className="node-card-footer">
                <span>LoRa RSSI: {n3Status.rssi || -65}dBm</span>
                <span>Pkts: {n3Status.packet_count || 0}</span>
              </div>
            </div>
          </div>

          {/* Realtime Telemetry Charts */}
          <div className="card-glass charts-card">
            <div className="chart-header">
              <h2>Real-Time Historical Telemetry Trends</h2>
              <div className="chart-tabs">
                <button 
                  className={`chart-tab-btn ${activeChartTab === 'landslide' ? 'active' : ''}`}
                  onClick={() => setActiveChartTab('landslide')}
                >
                  🏔️ Mountain Sensors
                </button>
                <button 
                  className={`chart-tab-btn ${activeChartTab === 'flood' ? 'active' : ''}`}
                  onClick={() => setActiveChartTab('flood')}
                >
                  🌊 River Level
                </button>
                <button 
                  className={`chart-tab-btn ${activeChartTab === 'rain' ? 'active' : ''}`}
                  onClick={() => setActiveChartTab('rain')}
                >
                  🌧️ Aggregator Rain
                </button>
              </div>
            </div>

            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <LineChart data={getChartData(activeChartTab)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="time" stroke="var(--text-secondary)" fontSize={11} />
                  <YAxis stroke="var(--text-secondary)" fontSize={11} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#111827', borderColor: 'var(--border-color)', color: '#fff' }} 
                  />
                  <Legend />
                  {activeChartTab === 'landslide' && (
                    <>
                      <Line type="monotone" dataKey="soil_moisture" name="Soil Moisture (%)" stroke="#10b981" strokeWidth={2} activeDot={{ r: 6 }} />
                      <Line type="monotone" dataKey="vibration" name="Ground Vibration (g)" stroke="#ef4444" strokeWidth={2} />
                    </>
                  )}
                  {activeChartTab === 'flood' && (
                    <Line type="monotone" dataKey="water_level" name="River Level (m)" stroke="#3b82f6" strokeWidth={2} activeDot={{ r: 6 }} />
                  )}
                  {activeChartTab === 'rain' && (
                    <Line type="monotone" dataKey="rainfall" name="Rain Rate (mm/h)" stroke="#f59e0b" strokeWidth={2} activeDot={{ r: 6 }} />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="side-column">
          {/* Simulation Center */}
          <div className="card-glass simulation-card">
            <h2>Demo & Simulation Controller</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              Simulate sensor spikes and disaster events to test early-warning logic:
            </p>
            <div className="simulation-grid">
              <button 
                className={`sim-btn ${activeScenario === 'normal' ? 'active' : ''}`}
                onClick={() => triggerScenario('normal')}
              >
                <CheckCircle2 size={14} /> Safe Baseline
              </button>
              <button 
                className={`sim-btn ${activeScenario === 'rain' ? 'active' : ''}`}
                onClick={() => triggerScenario('rain')}
              >
                <CloudRain size={14} /> Heavy Rain
              </button>
              <button 
                className={`sim-btn ${activeScenario === 'river' ? 'active' : ''}`}
                onClick={() => triggerScenario('river')}
              >
                <TrendingUp size={14} /> Rising River
              </button>
              <button 
                className={`sim-btn ${activeScenario === 'landslide' ? 'active' : ''}`}
                onClick={() => triggerScenario('landslide')}
              >
                <Activity size={14} /> Landslide Risk
              </button>
              <button 
                className={`sim-btn ${activeScenario === 'critical' ? 'active' : ''}`}
                onClick={() => triggerScenario('critical')}
              >
                <ShieldAlert size={14} /> Critical Event
              </button>
              <button 
                className="sim-btn sim-btn-reset"
                onClick={() => triggerScenario('reset')}
              >
                <RefreshCw size={14} /> Reset Database
              </button>
            </div>
          </div>

          {/* Interactive Map */}
          <div className="card-glass" style={{ padding: '1rem' }}>
            <h2 style={{ marginBottom: '0.75rem', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <MapPin size={18} className="text-low" /> Predefined Node Deployments
            </h2>
            <div className="map-container">
              <MapContainer 
                center={[45.888, 6.845]} 
                zoom={14} 
                scrollWheelZoom={false}
                zoomControl={false}
              >
                <TileLayer
                  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                />
                {/* Node 1 marker */}
                {n1Status.latitude && (
                  <CircleMarker 
                    center={[n1Status.latitude, n1Status.longitude]}
                    radius={10}
                    fillColor={getCircleColor(data.landslide_risk > 70 ? 'CRITICAL' : data.landslide_risk > 50 ? 'WARNING' : 'SAFE')}
                    color="#fff"
                    weight={1.5}
                    fillOpacity={0.8}
                  >
                    <Popup>
                      <strong>Mountain Node (NODE1)</strong><br />
                      Landslide Risk: {Math.round(data.landslide_risk)}%<br />
                      Soil: {n1Reading.soil_moisture?.toFixed(1)}% | Vib: {n1Reading.vibration?.toFixed(2)}g
                    </Popup>
                  </CircleMarker>
                )}
                {/* Node 2 marker */}
                {n2Status.latitude && (
                  <CircleMarker 
                    center={[n2Status.latitude, n2Status.longitude]}
                    radius={10}
                    fillColor={getCircleColor(data.flood_risk > 70 ? 'CRITICAL' : data.flood_risk > 50 ? 'WARNING' : 'SAFE')}
                    color="#fff"
                    weight={1.5}
                    fillOpacity={0.8}
                  >
                    <Popup>
                      <strong>River Node (NODE2)</strong><br />
                      Flood Risk: {Math.round(data.flood_risk)}%<br />
                      Water Level: {n2Reading.water_level?.toFixed(2)}m
                    </Popup>
                  </CircleMarker>
                )}
                {/* Node 3 marker */}
                {n3Status.latitude && (
                  <CircleMarker 
                    center={[n3Status.latitude, n3Status.longitude]}
                    radius={12}
                    fillColor="#3b82f6"
                    color="#fff"
                    weight={2}
                    fillOpacity={0.8}
                  >
                    <Popup>
                      <strong>Aggregator Gateway (NODE3)</strong><br />
                      Precipitation: {n3Reading.rainfall?.toFixed(1)} mm/h<br />
                      Status: {n3Status.status}
                    </Popup>
                  </CircleMarker>
                )}
              </MapContainer>
            </div>
          </div>

          {/* Active Alerts Panel */}
          <div className="card-glass alerts-card">
            <div className="alerts-header">
              <h2 style={{ fontSize: '1.1rem' }}>Active Early-Warning Alerts</h2>
              <span className="status-badge bg-critical" style={{ color: '#fff', fontSize: '0.7rem' }}>
                {data.active_alerts.length} Active
              </span>
            </div>
            
            <div className="alerts-list">
              {data.active_alerts.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  No active threat alerts generated.
                </div>
              ) : (
                data.active_alerts.map((alert) => (
                  <div key={alert.id} className={`alert-item ${alert.severity}`}>
                    <div className="alert-body">
                      <span className="alert-title">{alert.message}</span>
                      <span className="alert-meta">
                        Source: {alert.node_id} | {new Date(alert.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <button 
                      className="ack-btn"
                      onClick={() => acknowledgeAlert(alert.id)}
                    >
                      Acknowledge
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Warning Disclaimer Banner */}
      <footer className="disclaimer-banner">
        <strong>⚠️ HACKATHON PROTOTYPE WARNING DISCLAIMER:</strong> All warning thresholds, risk evaluations, and telemetry metrics displayed are simulation values calibrated for demonstration. They are not official safety levels and require field-calibration and compliance certification prior to real-world deployment.
      </footer>
    </div>
  );
}
