# DataVerse AI 2.0 - Quick Start Guide

## 🚀 New Features - Get Started in 5 Minutes

### 1. **Command Palette** (Cmd+K)

**How to Use:**
- Press `⌘K` on Mac or `Ctrl+K` on Windows/Linux
- Type to search for commands
- Press ↑↓ arrows to navigate
- Press Enter to execute

**Available Commands:**
```
Upload Dataset       → Load CSV file
Analyze Data         → Start analysis
Export Results       → Download report
Share Session        → Share with team
Settings             → Configure app
```

### 2. **Quick Actions**

**Access:** Visible on main chat screen after uploading data

**4 Actions:**
1. **📊 Exploratory Analysis** - Generate EDA report
2. **🤖 AI Insights** - Ask for key findings
3. **📈 Predictions** - Build predictive model
4. **📁 Data Profile** - View data summary

### 3. **Settings** 

**Access:** Click Settings in Sidebar or use Command Palette

**Configure:**
- Auto-save sessions
- Data retention period
- Export format preference
- Upload size limits
- Theme (dark/light)
- API version

### 4. **Session History**

**Access:** `/history` or via Sidebar

**Features:**
- View all previous analyses
- Filter by status (Active/Completed)
- Sort by date, name, or size
- Quickly open old sessions
- Delete or export sessions

### 5. **Analytics Dashboard**

**Access:** `/analytics` or via Sidebar

**See:**
- Trained models & accuracy
- Available analysis features
- Anomaly detection results
- Model performance metrics

---

## 🤖 New Analytics Tools

### **Anomaly Detection**

**What it does:** Finds unusual data points that deviate from patterns

**How to use via UI:**
```
1. Upload dataset
2. Go to Analytics page
3. Click "Run Anomaly Detection"
4. Select detection method
```

**Available Methods:**
- **Ensemble** ⭐ Recommended (combines 3+ methods)
- **Isolation Forest** (tree-based)
- **Local Outlier Factor** (density-based)
- **Z-Score** (statistical)
- **IQR** (quartile-based)

**API Call:**
```bash
curl -X POST http://localhost:8001/analytics/anomalies \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "method": "ensemble",
    "contamination": 0.05
  }'
```

### **Customer Segmentation**

**What it does:** Groups similar customers/records together

**How to use via UI:**
```
1. Upload customer data
2. Go to Analytics page
3. Click model or "Run Segmentation"
4. System auto-detects best number of groups
```

**Features:**
- Automatic K detection
- Segment characteristics
- Feature importance
- Quality metrics (Silhouette score)

**API Call:**
```bash
curl -X POST http://localhost:8001/analytics/segmentation \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "n_clusters": null,
    "scale": true
  }'
```

### **Time Series Forecasting**

**What it does:** Predicts future values based on historical patterns

**How to use:**
```
Specify:
- Time column (dates)
- Value column (to forecast)
- Frequency (Daily/Weekly/Monthly)
- Periods ahead (how many to predict)
```

---

## 📖 Using Each Page

### **Home Page** (`/`)
- Upload datasets
- See feature highlights
- Start new analysis
- Quick access to tools

### **Settings** (`/settings`)
**Tabs:**
- **General** - Auto-save, limits, formats
- **Privacy** - Data retention, deleteion
- **Appearance** - Theme selection
- **Notifications** - Alert preferences
- **API** - Version selection

### **History** (`/history`)
**Features:**
- Search all sessions
- Filter by status
- Sort by date/name/size
- Quick open/download/delete
- Storage usage chart

### **Analytics** (`/analytics`)
**Tabs:**
- **Models** - View trained ML models
- **Analytics** - Available analysis tools
- **Anomalies** - Outlier detection results

---

## 💡 Pro Tips

### Keyboard Shortcuts
```
Cmd+K (Mac)   / Ctrl+K (Windows) → Open Command Palette
Shift+Enter   → New line in chat
Enter         → Send message
Esc           → Close palette/modals
```

### Best Practices

1. **Before Analysis:**
   - Clean data format (CSV works best)
   - Remove sensitive columns
   - Ensure consistent data types

2. **During Analysis:**
   - Use Command Palette for quick access
   - Save session for later
   - Take notes on insights

3. **After Analysis:**
   - Export results (HTML/PDF recommended)
   - Share sessions with team
   - Refer back to history

### Common Workflows

**Workflow 1: Quick Data Exploration**
```
1. Upload CSV (Command Palette → Upload)
2. Click "Data Profile" quick action
3. View results in right panel
4. Export as needed
```

**Workflow 2: Find Outliers**
```
1. Upload data
2. Go to Analytics → Run Anomaly Detection
3. Choose "ensemble" method
4. Review flagged rows
5. Decide on cleanup
```

**Workflow 3: Segment Customers**
```
1. Upload customer data
2. Analytics → Run Segmentation
3. System auto-finds best groups
4. Review segment characteristics
5. Use for targeted marketing
```

---

## ⚙️ Configuration Guide

### Recommended Settings

**For Development:**
```
General:
  - Auto-save: ON
  - Upload limit: 50MB
  - Default format: JSON
  
Theme: Auto (matches system)
Data Retention: 90 days
API Version: v1
```

**For Production:**
```
General:
  - Auto-save: ON
  - Upload limit: 50MB
  - Default format: HTML
  
Theme: Light (professional)
Data Retention: 365 days
API Version: v1
```

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Command Palette not opening | Refresh browser, check console errors |
| Settings not saving | Verify backend is running |
| Anomaly detection slow | Reduce contamination parameter |
| Segmentation convergence | Check for missing values, ensure numeric data |
| Export not working | Verify file permissions in storage folder |

---

## 📚 Further Resources

- **Full Technical Docs:** `INTEGRATION_GUIDE_PHASE5.md`
- **Feature Overview:** `PHASE_5_IMPROVEMENTS.md`
- **Complete Summary:** `PHASE_5_COMPLETION_SUMMARY.md`
- **API Reference:** `QUICK_REFERENCE.md`
- **Setup Guide:** `SETUP.md`

---

## 🎓 Learning Path

**Beginner:**
1. Upload a CSV file
2. Explore Settings page
3. Check Session History
4. Try Quick Actions

**Intermediate:**
1. Run Anomaly Detection
2. Create Customer Segments
3. Build predictive model
4. Export results

**Advanced:**
1. Use API endpoints directly
2. Batch predictions
3. Custom analysis chains
4. Integration with external systems

---

## 🔗 API Quick Reference

```bash
# Anomaly Detection
POST /analytics/anomalies
  ?session_id=UUID&method=ensemble&contamination=0.05

# Segmentation
POST /analytics/segmentation
  ?session_id=UUID&n_clusters=null&scale=true

# Time Series
POST /analytics/forecast
  ?session_id=UUID&time_column=date&value_column=sales

# Export
POST /export/results
  ?session_id=UUID&format=html&include_visualizations=true

# List Models
GET /models/list?session_id=UUID

# Check Health
GET /health
```

---

## ✅ Pre-Launch Checklist

- [ ] Updated `.env` with API keys
- [ ] Docker containers running
- [ ] Frontend loads at http://localhost:3000
- [ ] Backend responds at http://localhost:8001/health
- [ ] Test Command Palette (Cmd+K)
- [ ] Upload test CSV file
- [ ] Try Quick Actions
- [ ] Check Settings page
- [ ] View Session History
- [ ] Test Anomaly Detection

---

**Current Version**: 2.0.0  
**Last Updated**: April 4, 2026  
**Status**: ✅ Production Ready

**Need Help?** Check the command palette suggestions or visit documentation files.
