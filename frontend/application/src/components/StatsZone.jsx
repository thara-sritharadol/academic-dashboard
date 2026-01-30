import React, { useState, useEffect } from 'react';

const StatsZone = () => {
  // 1. สร้าง State สำหรับเก็บข้อมูล, สถานะ Loading, และ Error
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 2. ดึงข้อมูลจาก Django API เมื่อ Component โหลดเสร็จ
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/stats/');
        
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        
        const jsonData = await response.json();
        setStats(jsonData);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching stats:", err);
        setError('Failed to load statistics.');
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  // 3. แสดงผลตามสถานะ
  if (loading) return <div style={styles.loading}>Loading Statistics...</div>;
  if (error) return <div style={styles.error}>{error}</div>;
  if (!stats) return null;

  // คำนวณ % Coverage (งานที่มี Abstract / งานทั้งหมด)
  const coveragePercent = ((stats.analyzed_papers / stats.total_papers) * 100).toFixed(1);

  // 4. UI
  return (
    <div style={styles.container}>
      <h2 style={styles.header}>Thammasat Research Overview</h2>
      
      {/* Card */}
      <div style={styles.cardContainer}>
        {/* Card 1: Authors */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Researchers</h3>
          <p style={styles.cardNumber}>{stats.total_authors.toLocaleString()}</p>
          <span style={styles.cardSub}>Total Authors Found</span>
        </div>

        {/* Card 2: Papers */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Total Papers</h3>
          <p style={styles.cardNumber}>{stats.total_papers.toLocaleString()}</p>
          <span style={styles.cardSub}>Records in Database</span>
        </div>

        {/* Card 3: Analyzed Coverage */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Analyzed Data</h3>
          <p style={styles.cardNumber}>{stats.analyzed_papers.toLocaleString()}</p>
          <span style={styles.cardSub}>
             Coverage: <strong>{coveragePercent}%</strong> (Has Abstract)
          </span>
        </div>
      </div>

      {/* Cluster */}
      <div style={styles.clusterSection}>
        <h3>Found Research Clusters</h3>
        <ul style={styles.list}>
          {stats.cluster_stats.map((cluster, index) => (
            <li key={index} style={styles.listItem}>
              <strong>{cluster.cluster_label}</strong>
              <span style={styles.badge}>{cluster.count} papers</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

const styles = {
  container: {
    width: '90vw',
    padding: '20px',
    backgroundColor: '#f4f6f8',
    borderRadius: '8px',
    fontFamily: 'Arial, sans-serif',
    marginBottom: '20px'
  },
  header: {
    marginTop: 0,
    color: '#333'
  },
  loading: { padding: '20px', textAlign: 'center', fontSize: '18px' },
  error: { padding: '20px', color: 'red', textAlign: 'center' },
  cardContainer: {
    display: 'flex',
    gap: '20px',
    marginBottom: '20px',
    flexWrap: 'wrap'
  },
  card: {
    flex: 1,
    minWidth: '200px',
    backgroundColor: 'white',
    padding: '20px',
    borderRadius: '10px',
    boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
    textAlign: 'center'
  },
  cardTitle: { margin: 0, color: '#666', fontSize: '14px', textTransform: 'uppercase' },
  cardNumber: { margin: '10px 0', fontSize: '32px', fontWeight: 'bold', color: '#2c3e50' },
  cardSub: { fontSize: '12px', color: '#888' },
  clusterSection: {
    backgroundColor: 'white',
    padding: '20px',
    borderRadius: '10px',
    boxShadow: '0 2px 5px rgba(0,0,0,0.1)'
  },
  list: { listStyleType: 'none', padding: 0 },
  listItem: {
    padding: '10px',
    borderBottom: '1px solid #eee',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  badge: {
    backgroundColor: '#e3f2fd',
    color: '#1976d2',
    padding: '4px 8px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: 'bold'
  }
};

export default StatsZone;