"""
DataVerse Analytics - Streamlit Web UI

A user-friendly web interface to interact with the DataVerse backend API.
Upload datasets, ask questions in natural language, and get AI-powered analytics.

Run with: streamlit run scripts/ui_app.py
"""

import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="DataVerse Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5em;
        color: #1f77b4;
        margin-bottom: 10px;
    }
    .status-ok {
        color: #2ecc71;
        font-weight: bold;
    }
    .status-error {
        color: #e74c3c;
        font-weight: bold;
    }
    .info-box {
        background-color: #ecf0f1;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "backend_url" not in st.session_state:
    st.session_state.backend_url = "http://localhost:8001/api"
if "query_history" not in st.session_state:
    st.session_state.query_history = []

# Sidebar configuration
st.sidebar.title("⚙️ Configuration")

backend_port = st.sidebar.number_input("Backend Port", value=8001, min_value=8000, max_value=9000)
st.session_state.backend_url = f"http://localhost:{backend_port}/api"

st.sidebar.markdown("---")

# Connection status
st.sidebar.title("🔗 Connection Status")
try:
    resp = requests.get(f"{st.session_state.backend_url}/health", timeout=2)
    if resp.status_code == 200:
        st.sidebar.markdown('<p class="status-ok">✓ Connected</p>', unsafe_allow_html=True)
        backend_ok = True
    else:
        st.sidebar.markdown('<p class="status-error">✗ Backend Error</p>', unsafe_allow_html=True)
        backend_ok = False
except:
    st.sidebar.markdown('<p class="status-error">✗ Disconnected</p>', unsafe_allow_html=True)
    backend_ok = False

if st.session_state.session_id:
    st.sidebar.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")

st.sidebar.markdown("---")

# Main content
st.markdown('<div class="main-header">📊 DataVerse Analytics</div>', unsafe_allow_html=True)
st.markdown("AI-powered analytics for retail and product datasets")

if not backend_ok:
    st.error("⚠️ Backend is not connected. Please ensure the server is running on port " + str(backend_port))
    st.info(
        f"Start the backend with:\n```bash\npython -m uvicorn app.main:app --app-dir dataverse_backend --host 127.0.0.1 --port {backend_port}\n```"
    )
else:
    # Tab layout
    tab1, tab2, tab3 = st.tabs(["📤 Upload", "🔍 Query", "📝 History"])
    
    # ===== TAB 1: UPLOAD =====
    with tab1:
        st.header("Upload Dataset")
        st.markdown("Upload a CSV dataset for analysis. The system will validate it and extract insights.")
        
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv", key="file_uploader")
        
        if uploaded_file:
            st.success(f"✓ File selected: {uploaded_file.name}")
            
            # Show dataset preview
            df = pd.read_csv(uploaded_file)
            st.markdown("**Dataset Preview:**")
            st.dataframe(df.head(5), use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                st.metric("Size", f"{df.memory_usage().sum() / 1024:.1f} KB")
            
            if st.button("📤 Upload to Backend", key="upload_btn", use_container_width=True):
                with st.spinner("Uploading dataset..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                        resp = requests.post(
                            f"{st.session_state.backend_url}/upload",
                            files=files,
                            timeout=30
                        )
                        
                        if resp.status_code == 200:
                            data = resp.json()
                            st.session_state.session_id = data.get("session_id")
                            
                            st.success("✓ Dataset uploaded successfully!")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                is_retail = data.get("is_retail", False)
                                status_icon = "✓" if is_retail else "⚠️"
                                st.info(f"{status_icon} Retail dataset: {is_retail}")
                            
                            with col2:
                                st.info(f"Session: `{st.session_state.session_id[:12]}...`")
                            
                            st.markdown(f"**Message:** {data.get('message', 'N/A')}")
                            
                            if data.get("matched_keywords"):
                                st.markdown(f"**Matched Keywords:** {', '.join(data.get('matched_keywords', []))}")
                        else:
                            st.error(f"Upload failed: {resp.status_code}")
                            st.text(resp.text)
                    except Exception as e:
                        st.error(f"Error uploading file: {e}")
    
    # ===== TAB 2: QUERY =====
    with tab2:
        st.header("Query Dataset")
        st.markdown("Ask questions about your dataset in natural language")
        
        if not st.session_state.session_id:
            st.warning("⚠️ Please upload a dataset first (see Upload tab)")
        else:
            # Quick query templates
            st.markdown("**Quick Query Templates:**")
            col1, col2, col3 = st.columns(3)
            
            template_queries = {
                "Analyze sales": "Analyze total sales by region",
                "Top products": "What are the top 10 products by revenue?",
                "Distribution": "Show me the distribution of profit margins"
            }
            
            for template, query in template_queries.items():
                if col1.button(template, use_container_width=True):
                    st.session_state.query_text = query
                col1, col2, col3 = st.columns(3)
            
            # Custom query input
            st.markdown("**Or type your own query:**")
            query_text = st.text_area(
                "Enter your question",
                value=st.session_state.get("query_text", ""),
                placeholder="E.g., What are my best-selling products?",
                height=100,
                key="query_input"
            )
            
            if st.button("🔍 Analyze", use_container_width=True, key="query_btn"):
                if not query_text.strip():
                    st.warning("Please enter a query")
                else:
                    with st.spinner("Analyzing your query..."):
                        try:
                            payload = {
                                "session_id": st.session_state.session_id,
                                "query": query_text
                            }
                            resp = requests.post(
                                f"{st.session_state.backend_url}/query",
                                json=payload,
                                timeout=120
                            )
                            
                            if resp.status_code == 200:
                                data = resp.json()
                                
                                # Add to history
                                st.session_state.query_history.append({
                                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                                    "query": query_text,
                                    "is_retail": data.get("is_retail")
                                })
                                
                                # Display results
                                st.success("✓ Analysis complete!")
                                
                                # Intent
                                intent_data = data.get("intent", {})
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown("**Detected Intent:**")
                                    st.json(intent_data)
                                
                                with col2:
                                    st.markdown("**Response Metadata:**")
                                    metadata = {
                                        "Is Retail": data.get("is_retail"),
                                        "Action Required": data.get("action_required", "None"),
                                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    st.json(metadata)
                                
                                # Report
                                st.markdown("---")
                                st.markdown("**Analysis Report:**")
                                report = data.get("report", "")
                                
                                if isinstance(report, str):
                                    try:
                                        report_json = json.loads(report)
                                        if "narrative" in report_json:
                                            st.info(report_json["narrative"])
                                        else:
                                            st.json(report_json)
                                    except:
                                        st.markdown(report)
                                else:
                                    st.json(report)
                                
                                # Computed facts
                                facts = data.get("computed_facts", {})
                                if facts:
                                    st.markdown("**Computed Facts:**")
                                    st.json(facts)
                            else:
                                st.error(f"Query failed: {resp.status_code}")
                                st.text(resp.text[:500])
                        except Exception as e:
                            st.error(f"Error processing query: {e}")
    
    # ===== TAB 3: HISTORY =====
    with tab3:
        st.header("Query History")
        
        if not st.session_state.query_history:
            st.info("No queries yet. Try asking a question in the Query tab!")
        else:
            st.markdown(f"**Total Queries:** {len(st.session_state.query_history)}")
            
            # Display history as table
            history_df = pd.DataFrame(st.session_state.query_history)
            st.dataframe(
                history_df,
                use_container_width=True,
                column_config={
                    "timestamp": st.column_config.TextColumn("Time"),
                    "query": st.column_config.TextColumn("Query", width=400),
                    "is_retail": st.column_config.CheckboxColumn("Retail Dataset")
                }
            )
            
            if st.button("🗑️ Clear History", use_container_width=True):
                st.session_state.query_history = []
                st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #95a5a6; font-size: 0.9em;">
    <p>DataVerse Analytics • Backend on {host}:{port} • Built with Streamlit</p>
</div>
""".format(host="localhost", port=backend_port), unsafe_allow_html=True)
