import streamlit as st
import pandas as pd
import numpy as np
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# === CONFIGURATION ===
try:
    BASE_DIR = Path(__file__).parent
except:
    BASE_DIR = Path.cwd()

DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"

DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

DATA_FILE = DATA_DIR / "inventory_transactions.csv"
ITEMS_FILE = DATA_DIR / "master_items.csv"
PARTIES_FILE = DATA_DIR / "master_parties.csv"

PAGE_SIZE = 20
LOW_STOCK_THRESHOLD = 10
MAX_BACKUPS = 10

TRANSACTION_TYPES = {
    "Purchase": {"affects_stock": 1, "affects_balance": 1, "icon": "📥"},
    "Sale": {"affects_stock": -1, "affects_balance": -1, "icon": "📤"},
    "Receipt": {"affects_stock": 0, "affects_balance": -1, "icon": "💵"},
    "Payment": {"affects_stock": 0, "affects_balance": 1, "icon": "💸"},
    "Return In": {"affects_stock": 1, "affects_balance": -1, "icon": "↩️"},
    "Return Out": {"affects_stock": -1, "affects_balance": 1, "icon": "↪️"},
}

# === PAGE CONFIG ===
st.set_page_config(
    page_title="Business Inventory Tracker",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === CUSTOM CSS - WORKS IN BOTH LIGHT AND DARK MODE ===
st.markdown("""
<style>
    /* Metric cards */
    .metric-box {
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        margin: 5px;
    }
    
    .metric-box h3 {
        color: white !important;
        margin: 0;
        font-size: 1rem;
        opacity: 0.9;
    }
    
    .metric-box h1 {
        color: white !important;
        margin: 10px 0 0 0;
        font-size: 1.8rem;
    }
    
    .metric-green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .metric-red { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }
    .metric-blue { background: linear-gradient(135deg, #2196F3 0%, #21CBF3 100%); }
    .metric-purple { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .metric-orange { background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%); }
    
    /* Balance cards */
    .balance-card {
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        border-left: 5px solid;
    }
    
    .balance-owe {
        background-color: rgba(244, 67, 54, 0.15);
        border-left-color: #f44336;
    }
    
    .balance-receive {
        background-color: rgba(76, 175, 80, 0.15);
        border-left-color: #4caf50;
    }
    
    .balance-settled {
        background-color: rgba(158, 158, 158, 0.15);
        border-left-color: #9e9e9e;
    }
    
    /* Sidebar stats */
    .sidebar-stat {
        padding: 15px;
        border-radius: 10px;
        margin: 8px 0;
        border-left: 4px solid;
    }
    
    .stat-blue {
        background-color: rgba(33, 150, 243, 0.15);
        border-left-color: #2196F3;
    }
    
    .stat-green {
        background-color: rgba(76, 175, 80, 0.15);
        border-left-color: #4caf50;
    }
    
    .stat-orange {
        background-color: rgba(255, 152, 0, 0.15);
        border-left-color: #ff9800;
    }
    
    /* Transaction cards */
    .trans-card {
        padding: 12px 15px;
        border-radius: 8px;
        margin: 5px 0;
        border-left: 4px solid #673ab7;
        background-color: rgba(103, 58, 183, 0.1);
    }
    
    /* Alert boxes */
    .alert-box {
        padding: 12px 15px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 4px solid;
    }
    
    .alert-warning {
        background-color: rgba(255, 152, 0, 0.15);
        border-left-color: #ff9800;
    }
    
    .alert-success {
        background-color: rgba(76, 175, 80, 0.15);
        border-left-color: #4caf50;
    }
    
    .alert-info {
        background-color: rgba(33, 150, 243, 0.15);
        border-left-color: #2196F3;
    }
    
    /* Item and Party cards */
    .item-card {
        padding: 10px 15px;
        border-radius: 6px;
        margin: 4px 0;
        background-color: rgba(76, 175, 80, 0.1);
        border-left: 3px solid #4caf50;
    }
    
    .party-card {
        padding: 10px 15px;
        border-radius: 6px;
        margin: 4px 0;
        background-color: rgba(33, 150, 243, 0.1);
        border-left: 3px solid #2196F3;
    }
    
    /* Format instruction boxes */
    .format-box {
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border: 2px dashed;
    }
    
    .format-items {
        background-color: rgba(76, 175, 80, 0.1);
        border-color: #4caf50;
    }
    
    .format-parties {
        background-color: rgba(33, 150, 243, 0.1);
        border-color: #2196F3;
    }
    
    .format-trans {
        background-color: rgba(233, 30, 99, 0.1);
        border-color: #e91e63;
    }
    
    /* Report cards */
    .report-card {
        padding: 12px 15px;
        border-radius: 8px;
        margin: 5px 0;
        background-color: rgba(103, 58, 183, 0.1);
        border-left: 4px solid #673ab7;
    }
    
    /* Delete confirmation */
    .delete-confirm {
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        background-color: rgba(255, 152, 0, 0.2);
        border: 2px solid #ff9800;
    }
    
    /* Preview box */
    .preview-box {
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        background-color: rgba(33, 150, 243, 0.1);
        border: 1px solid #2196F3;
    }
</style>
""", unsafe_allow_html=True)


# === UTILITY FUNCTIONS ===
def create_backup(filepath):
    try:
        filepath = Path(filepath)
        if filepath.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{filepath.stem}_backup_{timestamp}{filepath.suffix}"
            backup_path = BACKUP_DIR / backup_name
            shutil.copy(filepath, backup_path)
            backups = sorted(BACKUP_DIR.glob(f"{filepath.stem}_backup_*"), reverse=True)
            for old_backup in backups[MAX_BACKUPS:]:
                old_backup.unlink()
    except:
        pass


def sanitize_input(text):
    if text is None:
        return ""
    text = str(text).strip()[:500]
    for char in ['<', '>', '{', '}', '|', '\\', '^', '`']:
        text = text.replace(char, '')
    return text


def safe_format_date(date_val, format_str='%d/%m/%Y'):
    if pd.isna(date_val):
        return "Invalid Date"
    try:
        if isinstance(date_val, str):
            date_val = pd.to_datetime(date_val)
        return date_val.strftime(format_str)
    except:
        return "Invalid Date"


def safe_desc_preview(desc, max_length=50):
    desc = str(desc) if not pd.isna(desc) else ""
    return desc[:max_length] + "..." if len(desc) > max_length else desc


def calculate_quantity(qty_raw, trans_type):
    qty_raw = abs(float(qty_raw))
    multiplier = TRANSACTION_TYPES.get(trans_type, {}).get("affects_stock", 1)
    return qty_raw * multiplier


def calculate_balance_effect(amount, trans_type):
    multiplier = TRANSACTION_TYPES.get(trans_type, {}).get("affects_balance", 1)
    return abs(float(amount)) * multiplier


def safe_float(val, default=0.0):
    try:
        if pd.isna(val):
            return default
        return float(val)
    except:
        return default


def get_balance_status(x):
    try:
        val = safe_float(x)
        if val < 0:
            return "🟢 They Owe You"
        elif val > 0:
            return "🔴 You Owe Them"
        else:
            return "⚪ Settled"
    except:
        return "⚪ Settled"


def display_metric_card(title, value, color="blue"):
    st.markdown(f'''
        <div class="metric-box metric-{color}">
            <h3>{title}</h3>
            <h1>{value}</h1>
        </div>
    ''', unsafe_allow_html=True)


def display_balance_card(party_name, amount, balance_type):
    amount = safe_float(amount)
    if balance_type == "owe":
        st.markdown(f'''
            <div class="balance-card balance-owe">
                <strong>🔴 {party_name}</strong><br>
                You Owe: <strong>₹{amount:,.2f}</strong>
            </div>
        ''', unsafe_allow_html=True)
    elif balance_type == "receive":
        st.markdown(f'''
            <div class="balance-card balance-receive">
                <strong>🟢 {party_name}</strong><br>
                They Owe You: <strong>₹{amount:,.2f}</strong>
            </div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown(f'''
            <div class="balance-card balance-settled">
                <strong>⚪ {party_name}</strong><br>
                Settled: <strong>₹0.00</strong>
            </div>
        ''', unsafe_allow_html=True)


# === DATA MANAGEMENT ===
def clean_dataframe(df):
    if df.empty:
        return df
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    for col in ['Quantity', 'Price per Unit', 'Total Amount', 'Balance Effect']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    for col in ['Party Name', 'Type', 'Item Name', 'Description']:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str)
    if 'Description' not in df.columns:
        df['Description'] = ''
    if 'Balance Effect' not in df.columns:
        df['Balance Effect'] = df.apply(
            lambda row: calculate_balance_effect(row['Total Amount'], row['Type']), axis=1
        )
    return df.reset_index(drop=True)


def load_transactions():
    if DATA_FILE.exists():
        try:
            df = pd.read_csv(DATA_FILE)
            return clean_dataframe(df)
        except Exception as e:
            st.error(f"Error loading: {e}")
            return create_empty_dataframe()
    return create_empty_dataframe()


def create_empty_dataframe():
    return pd.DataFrame(columns=[
        'Date', 'Party Name', 'Type', 'Item Name',
        'Quantity', 'Price per Unit', 'Total Amount',
        'Balance Effect', 'Description'
    ])


def save_transactions(df):
    try:
        create_backup(DATA_FILE)
        df = clean_dataframe(df)
        df.to_csv(DATA_FILE, index=False)
        st.session_state.df = df.copy()
        return True
    except Exception as e:
        st.error(f"Error saving: {e}")
        return False


def load_master(file_path, column_name):
    file_path = Path(file_path)
    if file_path.exists():
        try:
            data = pd.read_csv(file_path)[column_name].dropna().unique().tolist()
            return sorted([str(item).strip() for item in data if str(item).strip()])
        except:
            return []
    return []


def save_master(file_path, data, column_name):
    try:
        file_path = Path(file_path)
        create_backup(file_path)
        unique_data = sorted(list(set([str(item).strip() for item in data if str(item).strip()])))
        pd.DataFrame({column_name: unique_data}).to_csv(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"Error saving: {e}")
        return False


# === SESSION STATE ===
def init_session_state():
    if 'df' not in st.session_state:
        st.session_state.df = load_transactions()
    if 'master_items' not in st.session_state:
        st.session_state.master_items = load_master(ITEMS_FILE, "Item Name")
    if 'master_parties' not in st.session_state:
        st.session_state.master_parties = load_master(PARTIES_FILE, "Party Name")
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'edit_idx' not in st.session_state:
        st.session_state.edit_idx = None
    if 'show_delete_confirm' not in st.session_state:
        st.session_state.show_delete_confirm = None


def refresh_data():
    st.session_state.df = load_transactions()
    st.session_state.master_items = load_master(ITEMS_FILE, "Item Name")
    st.session_state.master_parties = load_master(PARTIES_FILE, "Party Name")


init_session_state()
df = st.session_state.df
master_items = st.session_state.master_items
master_parties = st.session_state.master_parties


# === SIDEBAR ===
with st.sidebar:
    st.title("🏪 Inventory Tracker")
    st.markdown("---")
    st.caption(f"📁 Data: {DATA_DIR}")
    
    if not df.empty:
        st.subheader("📊 Quick Stats")
        
        st.markdown(f'''
            <div class="sidebar-stat stat-blue">
                <strong>📝 Total Transactions</strong><br>
                <span style="font-size: 1.5rem; font-weight: bold;">{len(df)}</span>
            </div>
        ''', unsafe_allow_html=True)
        
        st.markdown(f'''
            <div class="sidebar-stat stat-green">
                <strong>📦 Unique Items</strong><br>
                <span style="font-size: 1.5rem; font-weight: bold;">{df['Item Name'].nunique()}</span>
            </div>
        ''', unsafe_allow_html=True)
        
        st.markdown(f'''
            <div class="sidebar-stat stat-orange">
                <strong>👥 Unique Parties</strong><br>
                <span style="font-size: 1.5rem; font-weight: bold;">{df['Party Name'].nunique()}</span>
            </div>
        ''', unsafe_allow_html=True)
        
        valid_dates = df['Date'].dropna()
        if not valid_dates.empty:
            st.caption(f"📅 {safe_format_date(valid_dates.min())} to {safe_format_date(valid_dates.max())}")
    
    st.markdown("---")
    st.subheader("🔧 Data Management")
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        refresh_data()
        st.success("Data refreshed!")
        st.rerun()
    
    if not df.empty:
        st.download_button(
            label="📥 Export All Data",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f"inventory_backup_{datetime.today().strftime('%Y%m%d')}.csv",
            mime='text/csv',
            use_container_width=True
        )
    
    st.markdown("---")
    st.subheader("📤 Import/Restore")
    st.caption("⚠️ Cloud data resets on reboot!")
    
    uploaded_file = st.file_uploader("Upload CSV", type=['csv'], key="main_upload")
    if uploaded_file is not None:
        try:
            imported_df = pd.read_csv(uploaded_file)
            required_cols = ['Date', 'Party Name', 'Type', 'Item Name', 'Quantity', 'Price per Unit', 'Total Amount']
            if all(col in imported_df.columns for col in required_cols):
                st.success(f"Found {len(imported_df)} transactions")
                if st.button("✅ Confirm Import", use_container_width=True):
                    imported_df = clean_dataframe(imported_df)
                    if save_transactions(imported_df):
                        st.success("Imported!")
                        refresh_data()
                        st.rerun()
            else:
                missing = [c for c in required_cols if c not in imported_df.columns]
                st.error(f"Missing: {missing}")
        except Exception as e:
            st.error(f"Error: {e}")
    
    st.markdown("---")
    st.caption("v2.1 - Dark Mode Fixed")


# === MAIN APP ===
st.title("🏪 Business Inventory Tracker")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏠 Dashboard",
    "📋 Transactions",
    "➕ Add Transaction",
    "⚙️ Masters",
    "💰 Party Balances",
    "📈 Reports"
])


# ==================== TAB 1: DASHBOARD ====================
with tab1:
    st.header("Dashboard Overview")
    
    if df.empty:
        st.info("👋 Welcome! No transactions yet. Add some to see the dashboard!")
        st.markdown("""
        ### Getting Started:
        1. Go to **Masters** tab to add items and parties
        2. Go to **Add Transaction** to record purchases/sales
        3. Come back here to see your overview!
        """)
    else:
        col1, col2, col3, col4 = st.columns(4)
        
        total_items = df['Item Name'].nunique()
        stock_qty = df.groupby('Item Name')['Quantity'].sum()
        total_stock = stock_qty.sum()
        last_prices = df[df['Price per Unit'] > 0].groupby('Item Name')['Price per Unit'].last()
        positive_stock = stock_qty[stock_qty > 0]
        stock_value = (positive_stock * last_prices.reindex(positive_stock.index, fill_value=0)).sum()
        
        with col1:
            display_metric_card("📦 Unique Items", total_items, "blue")
        with col2:
            display_metric_card("📊 Current Stock", f"{int(total_stock):,}", "green")
        with col3:
            display_metric_card("💰 Stock Value", f"₹{stock_value:,.0f}", "purple")
        with col4:
            display_metric_card("📝 Transactions", len(df), "orange")
        
        st.markdown("---")
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("📦 Stock by Item")
            stock_summary = stock_qty.reset_index(name='Current Stock')
            stock_summary = stock_summary[stock_summary['Current Stock'] != 0].sort_values('Current Stock', ascending=False).head(15)
            if not stock_summary.empty:
                st.bar_chart(stock_summary.set_index('Item Name')['Current Stock'])
            else:
                st.info("No stock data")
        
        with chart_col2:
            st.subheader("📈 Transaction Trend")
            valid_dates = df.dropna(subset=['Date'])
            if not valid_dates.empty:
                monthly = valid_dates.copy()
                monthly['Month'] = monthly['Date'].dt.to_period('M').astype(str)
                stock_types = [t for t, c in TRANSACTION_TYPES.items() if c['affects_stock'] != 0]
                stock_monthly = monthly[monthly['Type'].isin(stock_types)]
                if not stock_monthly.empty:
                    flow = stock_monthly.groupby(['Month', 'Type'])['Quantity'].sum().abs().unstack(fill_value=0)
                    st.line_chart(flow)
                else:
                    st.info("No movement data")
            else:
                st.info("No dated transactions")
        
        st.markdown("---")
        st.subheader("⚠️ Low Stock Alerts")
        
        low_stock = stock_summary[(stock_summary['Current Stock'] > 0) & (stock_summary['Current Stock'] < LOW_STOCK_THRESHOLD)]
        
        if not low_stock.empty:
            for _, row in low_stock.iterrows():
                st.markdown(f'''
                    <div class="alert-box alert-warning">
                        <strong>🔔 {row['Item Name']}</strong> - Only {int(row['Current Stock'])} units left!
                    </div>
                ''', unsafe_allow_html=True)
        else:
            st.markdown('''
                <div class="alert-box alert-success">
                    <strong>✅ All items are adequately stocked</strong>
                </div>
            ''', unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("🕐 Recent Transactions")
        
        recent = df.sort_values('Date', ascending=False).head(5)
        for _, row in recent.iterrows():
            icon = TRANSACTION_TYPES.get(row['Type'], {}).get('icon', '📝')
            date_str = safe_format_date(row['Date'])
            qty = int(abs(safe_float(row['Quantity'])))
            price = safe_float(row['Price per Unit'])
            st.markdown(f'''
                <div class="trans-card">
                    {icon} <strong>{date_str}</strong> | {row['Party Name']} | 
                    <strong>{row['Type']}</strong> | {row['Item Name']} | 
                    Qty: {qty} @ ₹{price:,.2f}
                </div>
            ''', unsafe_allow_html=True)


# ==================== TAB 2: TRANSACTIONS ====================
with tab2:
    st.header("All Transactions")
    
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([3, 2, 2, 2])
    
    with filter_col1:
        search = st.text_input("🔍 Search", "", key="trans_search")
    with filter_col2:
        type_filter = st.multiselect("Type", list(TRANSACTION_TYPES.keys()), key="trans_type_filter")
    with filter_col3:
        date_range = st.date_input("Date Range", value=[], key="trans_date_range")
    with filter_col4:
        sort_order = st.selectbox("Sort", ["Date (Newest)", "Date (Oldest)", "Amount (High)", "Amount (Low)"], key="trans_sort")
    
    view_df = df.copy()
    
    if search:
        mask = (
            view_df['Item Name'].str.contains(search, case=False, na=False) |
            view_df['Party Name'].str.contains(search, case=False, na=False) |
            view_df['Description'].str.contains(search, case=False, na=False)
        )
        view_df = view_df[mask]
    
    if type_filter:
        view_df = view_df[view_df['Type'].isin(type_filter)]
    
    if len(date_range) == 2:
        view_df = view_df[(view_df['Date'] >= pd.Timestamp(date_range[0])) & (view_df['Date'] <= pd.Timestamp(date_range[1]))]
    
    if sort_order == "Date (Newest)":
        view_df = view_df.sort_values('Date', ascending=False)
    elif sort_order == "Date (Oldest)":
        view_df = view_df.sort_values('Date', ascending=True)
    elif sort_order == "Amount (High)":
        view_df = view_df.sort_values('Total Amount', ascending=False, key=abs)
    else:
        view_df = view_df.sort_values('Total Amount', ascending=True, key=abs)
    
    view_df = view_df.reset_index(drop=False).rename(columns={'index': 'original_idx'})
    
    st.markdown(f"**Showing {len(view_df)} transactions**")
    
    if not view_df.empty:
        total_pages = max(1, (len(view_df) - 1) // PAGE_SIZE + 1)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            page = st.number_input(f"Page (1-{total_pages})", 1, total_pages, min(st.session_state.current_page, total_pages), key="page_sel")
            st.session_state.current_page = page
        
        start_idx = (page - 1) * PAGE_SIZE
        page_df = view_df.iloc[start_idx:start_idx + PAGE_SIZE]
        
        for _, row in page_df.iterrows():
            original_idx = row['original_idx']
            icon = TRANSACTION_TYPES.get(row['Type'], {}).get('icon', '📝')
            date_str = safe_format_date(row['Date'])
            desc = safe_desc_preview(row['Description'])
            qty = int(abs(safe_float(row['Quantity'])))
            price = safe_float(row['Price per Unit'])
            amount = abs(safe_float(row['Total Amount']))
            
            col1, col2, col3 = st.columns([8, 1, 1])
            with col1:
                st.markdown(f'''
                    <div class="trans-card">
                        {icon} <strong>{date_str}</strong> | {row['Party Name']} | 
                        <strong>{row['Type']}</strong> | {row['Item Name']} | 
                        Qty: {qty} @ ₹{price:,.2f} → <strong>₹{amount:,.2f}</strong>
                        {f' | <em>{desc}</em>' if desc else ''}
                    </div>
                ''', unsafe_allow_html=True)
            with col2:
                if st.button("✏️", key=f"edit_{original_idx}"):
                    st.session_state.edit_idx = original_idx
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_{original_idx}"):
                    st.session_state.show_delete_confirm = original_idx
        
        # Delete confirmation
        if st.session_state.show_delete_confirm is not None:
            del_idx = st.session_state.show_delete_confirm
            st.markdown('''
                <div class="delete-confirm">
                    <strong>⚠️ Delete this transaction?</strong>
                </div>
            ''', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("✅ Yes, Delete", type="primary"):
                    df_updated = st.session_state.df.drop(del_idx).reset_index(drop=True)
                    if save_transactions(df_updated):
                        st.session_state.show_delete_confirm = None
                        st.success("Deleted!")
                        st.rerun()
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.show_delete_confirm = None
                    st.rerun()
        
        # Edit form
        if st.session_state.edit_idx is not None:
            edit_idx = st.session_state.edit_idx
            if edit_idx in st.session_state.df.index:
                row = st.session_state.df.loc[edit_idx].copy()
                st.markdown("---")
                st.subheader("✏️ Edit Transaction")
                
                with st.form("edit_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        default_date = row['Date'] if pd.notna(row['Date']) else datetime.today()
                        if isinstance(default_date, pd.Timestamp):
                            default_date = default_date.date()
                        new_date = st.date_input("Date", value=default_date)
                        new_party = st.text_input("Party Name", value=str(row['Party Name']))
                        type_opts = list(TRANSACTION_TYPES.keys())
                        type_idx = type_opts.index(row['Type']) if row['Type'] in type_opts else 0
                        new_type = st.selectbox("Type", type_opts, index=type_idx)
                    with col2:
                        new_item = st.text_input("Item Name", value=str(row['Item Name']))
                        new_qty = st.number_input("Quantity", value=int(abs(safe_float(row['Quantity']))), min_value=1)
                        new_price = st.number_input("Price per Unit", value=float(safe_float(row['Price per Unit'])), min_value=0.0, step=0.5)
                    new_desc = st.text_area("Description", value=str(row['Description']) if pd.notna(row['Description']) else "")
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        save_btn = st.form_submit_button("💾 Save", type="primary")
                    with col2:
                        cancel_btn = st.form_submit_button("❌ Cancel")
                    
                    if save_btn:
                        if not sanitize_input(new_party) or not sanitize_input(new_item):
                            st.error("Party and Item required!")
                        else:
                            qty_calc = calculate_quantity(new_qty, new_type)
                            total = abs(qty_calc) * new_price
                            bal = calculate_balance_effect(total, new_type)
                            
                            st.session_state.df.at[edit_idx, 'Date'] = pd.Timestamp(new_date)
                            st.session_state.df.at[edit_idx, 'Party Name'] = sanitize_input(new_party)
                            st.session_state.df.at[edit_idx, 'Type'] = new_type
                            st.session_state.df.at[edit_idx, 'Item Name'] = sanitize_input(new_item)
                            st.session_state.df.at[edit_idx, 'Quantity'] = float(qty_calc)
                            st.session_state.df.at[edit_idx, 'Price per Unit'] = float(new_price)
                            st.session_state.df.at[edit_idx, 'Total Amount'] = float(total)
                            st.session_state.df.at[edit_idx, 'Balance Effect'] = float(bal)
                            st.session_state.df.at[edit_idx, 'Description'] = sanitize_input(new_desc)
                            
                            if save_transactions(st.session_state.df):
                                st.session_state.edit_idx = None
                                st.success("Updated!")
                                st.rerun()
                    if cancel_btn:
                        st.session_state.edit_idx = None
                        st.rerun()
            else:
                st.session_state.edit_idx = None
                st.rerun()
        
        st.markdown("---")
        if not view_df.empty:
            export_df = view_df.drop(columns=['original_idx'])
            st.download_button("📥 Export Filtered", export_df.to_csv(index=False).encode('utf-8'), f"transactions_{datetime.today().strftime('%Y%m%d')}.csv", "text/csv")
    else:
        st.info("No transactions found.")


# ==================== TAB 3: ADD TRANSACTION ====================
with tab3:
    st.header("Add New Transaction")
    
    st.subheader("Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📥 Purchase", use_container_width=True):
            st.session_state.quick_type = "Purchase"
    with col2:
        if st.button("📤 Sale", use_container_width=True):
            st.session_state.quick_type = "Sale"
    with col3:
        if st.button("💵 Receipt", use_container_width=True):
            st.session_state.quick_type = "Receipt"
    with col4:
        if st.button("💸 Payment", use_container_width=True):
            st.session_state.quick_type = "Payment"
    
    st.markdown("---")
    
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            date = st.date_input("📅 Date", value=datetime.today())
            party_search = st.text_input("🔍 Party Name")
            filtered_parties = [p for p in master_parties if party_search.lower() in p.lower()] if party_search else master_parties
            selected_party = st.selectbox("👤 Select Party", ["-- Type new --"] + filtered_parties)
            party = party_search.strip() if selected_party == "-- Type new --" else selected_party
            
            default_type_idx = 0
            if 'quick_type' in st.session_state and st.session_state.quick_type in list(TRANSACTION_TYPES.keys()):
                default_type_idx = list(TRANSACTION_TYPES.keys()).index(st.session_state.quick_type)
            trans_type = st.selectbox("📋 Type", list(TRANSACTION_TYPES.keys()), index=default_type_idx)
        
        with col2:
            item_search = st.text_input("🔍 Item Name")
            filtered_items = [i for i in master_items if item_search.lower() in i.lower()] if item_search else master_items
            selected_item = st.selectbox("📦 Select Item", ["-- Type new --"] + filtered_items)
            item = item_search.strip() if selected_item == "-- Type new --" else selected_item
            
            quantity = st.number_input("🔢 Quantity", min_value=1, value=1)
            price = st.number_input("💲 Price per Unit (₹)", min_value=0.0, value=0.0, step=0.5)
        
        description = st.text_area("📝 Description (optional)")
        
        preview_qty = calculate_quantity(quantity, trans_type)
        preview_total = abs(preview_qty) * price
        preview_bal = calculate_balance_effect(preview_total, trans_type)
        
        st.markdown(f'''
            <div class="preview-box">
                <strong>📋 Preview:</strong> {trans_type} | 
                Stock: <strong>{'+' if preview_qty > 0 else ''}{int(preview_qty)}</strong> | 
                Amount: <strong>₹{preview_total:,.2f}</strong> | 
                Balance: <strong>{'+ You Owe' if preview_bal > 0 else '- They Owe'} ₹{abs(preview_bal):,.2f}</strong>
            </div>
        ''', unsafe_allow_html=True)
        
        submitted = st.form_submit_button("✅ Add Transaction", type="primary", use_container_width=True)
        
        if submitted:
            party = sanitize_input(party)
            item = sanitize_input(item)
            
            if not party:
                st.error("❌ Party Name required!")
            elif not item and trans_type not in ["Receipt", "Payment"]:
                st.error("❌ Item Name required!")
            else:
                if not item and trans_type in ["Receipt", "Payment"]:
                    item = "N/A - Payment"
                
                qty = calculate_quantity(quantity, trans_type)
                total = abs(qty) * price
                bal = calculate_balance_effect(total, trans_type)
                
                new_row = pd.DataFrame([{
                    'Date': pd.Timestamp(date),
                    'Party Name': party,
                    'Type': trans_type,
                    'Item Name': item,
                    'Quantity': float(qty),
                    'Price per Unit': float(price),
                    'Total Amount': float(total),
                    'Balance Effect': float(bal),
                    'Description': sanitize_input(description)
                }])
                
                updated_df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                
                if save_transactions(updated_df):
                    if party and party not in master_parties:
                        st.session_state.master_parties.append(party)
                        save_master(PARTIES_FILE, st.session_state.master_parties, "Party Name")
                    if item and item not in master_items and item != "N/A - Payment":
                        st.session_state.master_items.append(item)
                        save_master(ITEMS_FILE, st.session_state.master_items, "Item Name")
                    if 'quick_type' in st.session_state:
                        del st.session_state.quick_type
                    st.success("✅ Added!")
                    st.balloons()
                    st.rerun()


# ==================== TAB 4: MASTERS ====================
with tab4:
    st.header("Manage Items & Parties")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 Items")
        with st.form("add_item_form"):
            new_item = st.text_input("Add New Item")
            if st.form_submit_button("➕ Add Item", use_container_width=True):
                if new_item.strip():
                    clean = sanitize_input(new_item)
                    if clean and clean not in st.session_state.master_items:
                        st.session_state.master_items.append(clean)
                        if save_master(ITEMS_FILE, st.session_state.master_items, "Item Name"):
                            st.success(f"✅ Added: {clean}")
                            st.rerun()
                    else:
                        st.warning("Already exists!")
        
        item_search = st.text_input("🔍 Search Items", key="search_items")
        display_items = [i for i in master_items if item_search.lower() in i.lower()] if item_search else master_items
        st.markdown(f"**Total: {len(display_items)}**")
        
        for i, name in enumerate(sorted(display_items)):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f'<div class="item-card">📦 {name}</div>', unsafe_allow_html=True)
            if c2.button("❌", key=f"del_item_{i}_{name}"):
                if name in st.session_state.master_items:
                    st.session_state.master_items.remove(name)
                    if save_master(ITEMS_FILE, st.session_state.master_items, "Item Name"):
                        st.rerun()
    
    with col2:
        st.subheader("👥 Parties")
        with st.form("add_party_form"):
            new_party = st.text_input("Add New Party")
            if st.form_submit_button("➕ Add Party", use_container_width=True):
                if new_party.strip():
                    clean = sanitize_input(new_party)
                    if clean and clean not in st.session_state.master_parties:
                        st.session_state.master_parties.append(clean)
                        if save_master(PARTIES_FILE, st.session_state.master_parties, "Party Name"):
                            st.success(f"✅ Added: {clean}")
                            st.rerun()
                    else:
                        st.warning("Already exists!")
        
        party_search = st.text_input("🔍 Search Parties", key="search_parties")
        display_parties = [p for p in master_parties if party_search.lower() in p.lower()] if party_search else master_parties
        st.markdown(f"**Total: {len(display_parties)}**")
        
        for i, name in enumerate(sorted(display_parties)):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f'<div class="party-card">👤 {name}</div>', unsafe_allow_html=True)
            if c2.button("❌", key=f"del_party_{i}_{name}"):
                if name in st.session_state.master_parties:
                    st.session_state.master_parties.remove(name)
                    if save_master(PARTIES_FILE, st.session_state.master_parties, "Party Name"):
                        st.rerun()
    
    st.markdown("---")
    st.subheader("📋 CSV Formats")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="format-box format-items"><strong>📦 Items CSV:</strong><pre>Item Name\nRice 25kg\nSugar 10kg</pre></div>', unsafe_allow_html=True)
        sample_items = pd.DataFrame({"Item Name": ["Rice 25kg", "Sugar 10kg", "Wheat 5kg"]})
        st.download_button("📥 Sample Items", sample_items.to_csv(index=False).encode('utf-8'), "sample_items.csv", use_container_width=True)
    with col2:
        st.markdown('<div class="format-box format-parties"><strong>👥 Parties CSV:</strong><pre>Party Name\nSharma Traders\nABC Dist</pre></div>', unsafe_allow_html=True)
        sample_parties = pd.DataFrame({"Party Name": ["Sharma Traders", "ABC Distributors"]})
        st.download_button("📥 Sample Parties", sample_parties.to_csv(index=False).encode('utf-8'), "sample_parties.csv", use_container_width=True)
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        items_file = st.file_uploader("📦 Import Items", type=['csv'], key="items_upload")
        if items_file:
            try:
                items_df = pd.read_csv(items_file)
                if 'Item Name' in items_df.columns:
                    new_items = items_df['Item Name'].dropna().unique().tolist()
                    st.success(f"Found {len(new_items)} items")
                    if st.button("✅ Import Items", use_container_width=True):
                        st.session_state.master_items = list(set(st.session_state.master_items + new_items))
                        save_master(ITEMS_FILE, st.session_state.master_items, "Item Name")
                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    with col2:
        parties_file = st.file_uploader("👥 Import Parties", type=['csv'], key="parties_upload")
        if parties_file:
            try:
                parties_df = pd.read_csv(parties_file)
                if 'Party Name' in parties_df.columns:
                    new_parties = parties_df['Party Name'].dropna().unique().tolist()
                    st.success(f"Found {len(new_parties)} parties")
                    if st.button("✅ Import Parties", use_container_width=True):
                        st.session_state.master_parties = list(set(st.session_state.master_parties + new_parties))
                        save_master(PARTIES_FILE, st.session_state.master_parties, "Party Name")
                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


# ==================== TAB 5: PARTY BALANCES ====================
with tab5:
    st.header("💰 Party Balances")
    
    if df.empty:
        st.info("No transactions yet.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            min_date = df['Date'].min()
            from_date = st.date_input("From", value=min_date.date() if pd.notna(min_date) else datetime.today().date(), key="bal_from")
        with col2:
            max_date = df['Date'].max()
            to_date = st.date_input("To", value=max_date.date() if pd.notna(max_date) else datetime.today().date(), key="bal_to")
        with col3:
            party_filter = st.multiselect("Parties", master_parties, key="bal_parties")
        
        filtered_df = df[(df['Date'] >= pd.Timestamp(from_date)) & (df['Date'] <= pd.Timestamp(to_date))]
        if party_filter:
            filtered_df = filtered_df[filtered_df['Party Name'].isin(party_filter)]
        
        if filtered_df.empty:
            st.warning("No transactions found.")
        else:
            filtered_df['Balance Effect'] = pd.to_numeric(filtered_df['Balance Effect'], errors='coerce').fillna(0)
            party_summary = filtered_df.groupby('Party Name')['Balance Effect'].sum().reset_index()
            party_summary.rename(columns={'Balance Effect': 'Net Balance'}, inplace=True)
            party_summary['Net Balance'] = pd.to_numeric(party_summary['Net Balance'], errors='coerce').fillna(0)
            party_summary['Status'] = party_summary['Net Balance'].apply(get_balance_status)
            party_summary['Amount'] = party_summary['Net Balance'].abs()
            party_summary = party_summary.sort_values('Net Balance', ascending=True)
            
            total_receivable = safe_float(party_summary[party_summary['Net Balance'] < 0]['Amount'].sum())
            total_payable = safe_float(party_summary[party_summary['Net Balance'] > 0]['Amount'].sum())
            net_position = total_receivable - total_payable
            
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                display_metric_card("💚 Receivable", f"₹{total_receivable:,.0f}", "green")
            with col2:
                display_metric_card("❤️ Payable", f"₹{total_payable:,.0f}", "red")
            with col3:
                display_metric_card("📊 Net", f"₹{net_position:,.0f}", "blue" if net_position >= 0 else "orange")
            
            st.markdown("---")
            st.subheader("📋 Party-wise Balances")
            
            for _, row in party_summary.iterrows():
                net_bal = safe_float(row['Net Balance'])
                amount = safe_float(row['Amount'])
                if net_bal > 0:
                    display_balance_card(row['Party Name'], amount, "owe")
                elif net_bal < 0:
                    display_balance_card(row['Party Name'], amount, "receive")
                else:
                    display_balance_card(row['Party Name'], 0, "settled")
            
            st.markdown("---")
            st.subheader("📊 Summary Table")
            display_summary = party_summary[['Party Name', 'Status', 'Amount']].copy()
            display_summary['Amount'] = display_summary['Amount'].apply(lambda x: f"₹{safe_float(x):,.2f}")
            st.dataframe(display_summary, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("🔎 Party Details")
            selected_party = st.selectbox("Select Party", ["-- Select --"] + party_summary['Party Name'].tolist())
            
            if selected_party != "-- Select --":
                party_trans = filtered_df[filtered_df['Party Name'] == selected_party].sort_values('Date', ascending=False)
                st.markdown(f"### {selected_party}")
                
                purchases = safe_float(party_trans[party_trans['Type'].isin(['Purchase', 'Return In'])]['Total Amount'].sum())
                sales = safe_float(party_trans[party_trans['Type'].isin(['Sale', 'Return Out'])]['Total Amount'].sum())
                receipts = safe_float(party_trans[party_trans['Type'] == 'Receipt']['Total Amount'].sum())
                payments = safe_float(party_trans[party_trans['Type'] == 'Payment']['Total Amount'].sum())
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    display_metric_card("📥 Purchases", f"₹{purchases:,.0f}", "blue")
                with c2:
                    display_metric_card("📤 Sales", f"₹{sales:,.0f}", "green")
                with c3:
                    display_metric_card("💵 Receipts", f"₹{receipts:,.0f}", "purple")
                with c4:
                    display_metric_card("💸 Payments", f"₹{payments:,.0f}", "orange")
                
                st.markdown("---")
                display_df = party_trans[['Date', 'Type', 'Item Name', 'Quantity', 'Price per Unit', 'Total Amount', 'Description']].copy()
                display_df['Date'] = display_df['Date'].apply(safe_format_date)
                display_df['Quantity'] = display_df['Quantity'].apply(lambda x: int(abs(safe_float(x))))
                display_df['Total Amount'] = display_df['Total Amount'].apply(lambda x: f"₹{safe_float(x):,.2f}")
                display_df['Price per Unit'] = display_df['Price per Unit'].apply(lambda x: f"₹{safe_float(x):,.2f}")
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                st.download_button(f"📥 Export {selected_party}", party_trans.to_csv(index=False).encode('utf-8'), f"{selected_party}_{datetime.today().strftime('%Y%m%d')}.csv")


# ==================== TAB 6: REPORTS ====================
with tab6:
    st.header("📈 Reports")
    
    if df.empty:
        st.info("No data for reports.")
    else:
        report_type = st.selectbox("Report Type", ["Stock Summary", "Transaction Summary", "Monthly Analysis", "Item Analysis", "Party Analysis"])
        st.markdown("---")
        
        if report_type == "Stock Summary":
            st.subheader("📦 Stock Summary")
            stock_qty = df.groupby('Item Name')['Quantity'].sum()
            last_prices = df[df['Price per Unit'] > 0].groupby('Item Name')['Price per Unit'].last()
            stock_report = pd.DataFrame({
                'Item Name': stock_qty.index,
                'Stock': stock_qty.values,
                'Last Price': last_prices.reindex(stock_qty.index, fill_value=0).values
            })
            stock_report['Value'] = stock_report['Stock'] * stock_report['Last Price']
            stock_report = stock_report.sort_values('Value', ascending=False)
            
            display_stock = stock_report.copy()
            display_stock['Stock'] = display_stock['Stock'].apply(lambda x: int(safe_float(x)))
            display_stock['Last Price'] = display_stock['Last Price'].apply(lambda x: f"₹{safe_float(x):,.2f}")
            display_stock['Value'] = display_stock['Value'].apply(lambda x: f"₹{safe_float(x):,.2f}")
            st.dataframe(display_stock, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                positive_stock = stock_report[stock_report['Stock'] > 0].head(10)
                if not positive_stock.empty:
                    st.bar_chart(positive_stock.set_index('Item Name')['Stock'])
            with col2:
                positive_value = stock_report[stock_report['Value'] > 0].head(10)
                if not positive_value.empty:
                    st.bar_chart(positive_value.set_index('Item Name')['Value'])
        
        elif report_type == "Transaction Summary":
            st.subheader("📊 Transaction Summary")
            col1, col2 = st.columns(2)
            with col1:
                from_d = st.date_input("From", df['Date'].min().date() if pd.notna(df['Date'].min()) else datetime.today().date(), key="rep_from")
            with col2:
                to_d = st.date_input("To", df['Date'].max().date() if pd.notna(df['Date'].max()) else datetime.today().date(), key="rep_to")
            
            report_df = df[(df['Date'] >= pd.Timestamp(from_d)) & (df['Date'] <= pd.Timestamp(to_d))]
            if not report_df.empty:
                type_summary = report_df.groupby('Type').agg({'Quantity': lambda x: abs(x).sum(), 'Total Amount': 'sum'}).reset_index()
                for _, row in type_summary.iterrows():
                    icon = TRANSACTION_TYPES.get(row['Type'], {}).get('icon', '📝')
                    st.markdown(f'''
                        <div class="report-card">
                            {icon} <strong>{row['Type']}</strong>: {int(safe_float(row['Quantity']))} units | ₹{safe_float(row['Total Amount']):,.2f}
                        </div>
                    ''', unsafe_allow_html=True)
                st.markdown("---")
                daily = report_df.groupby(report_df['Date'].dt.date)['Total Amount'].sum()
                st.line_chart(daily)
        
        elif report_type == "Monthly Analysis":
            st.subheader("📅 Monthly Analysis")
            valid_dates = df.dropna(subset=['Date'])
            if not valid_dates.empty:
                monthly_df = valid_dates.copy()
                monthly_df['Month'] = monthly_df['Date'].dt.to_period('M').astype(str)
                monthly_pivot = monthly_df.groupby(['Month', 'Type'])['Total Amount'].sum().unstack(fill_value=0)
                st.dataframe(monthly_pivot, use_container_width=True)
                st.line_chart(monthly_pivot)
        
        elif report_type == "Item Analysis":
            st.subheader("📦 Item Analysis")
            selected_item = st.selectbox("Item", ["-- All --"] + master_items)
            if selected_item == "-- All --":
                item_summary = df.groupby('Item Name').agg({'Quantity': 'sum', 'Total Amount': 'sum'}).reset_index()
                item_summary.columns = ['Item', 'Net Stock', 'Total Value']
                item_summary['Net Stock'] = item_summary['Net Stock'].apply(lambda x: int(safe_float(x)))
                item_summary['Total Value'] = item_summary['Total Value'].apply(lambda x: f"₹{safe_float(x):,.2f}")
                st.dataframe(item_summary.sort_values('Item'), use_container_width=True, hide_index=True)
            else:
                item_df = df[df['Item Name'] == selected_item].sort_values('Date', ascending=False)
                if not item_df.empty:
                    total_in = safe_float(item_df[item_df['Quantity'] > 0]['Quantity'].sum())
                    total_out = abs(safe_float(item_df[item_df['Quantity'] < 0]['Quantity'].sum()))
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        display_metric_card("📥 In", int(total_in), "green")
                    with c2:
                        display_metric_card("📤 Out", int(total_out), "red")
                    with c3:
                        display_metric_card("📦 Stock", int(total_in - total_out), "blue")
                    st.dataframe(item_df[['Date', 'Party Name', 'Type', 'Quantity', 'Price per Unit', 'Total Amount']], use_container_width=True, hide_index=True)
        
        elif report_type == "Party Analysis":
            st.subheader("👥 Party Analysis")
            selected_party = st.selectbox("Party", ["-- All --"] + master_parties)
            if selected_party == "-- All --":
                party_summary = df.groupby('Party Name').agg({'Total Amount': 'sum', 'Quantity': 'count'}).reset_index()
                party_summary.columns = ['Party', 'Total Value', 'Transactions']
                party_summary['Total Value'] = party_summary['Total Value'].apply(lambda x: f"₹{safe_float(x):,.2f}")
                st.dataframe(party_summary.sort_values('Party'), use_container_width=True, hide_index=True)
            else:
                party_df = df[df['Party Name'] == selected_party].sort_values('Date', ascending=False)
                if not party_df.empty:
                    c1, c2 = st.columns(2)
                    with c1:
                        display_metric_card("📝 Transactions", len(party_df), "blue")
                    with c2:
                        display_metric_card("💰 Total Value", f"₹{safe_float(party_df['Total Amount'].sum()):,.0f}", "green")
                    st.dataframe(party_df[['Date', 'Type', 'Item Name', 'Quantity', 'Price per Unit', 'Total Amount']], use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.download_button("📥 Export All Data", df.to_csv(index=False).encode('utf-8'), f"full_export_{datetime.today().strftime('%Y%m%d')}.csv", use_container_width=True)


# === FOOTER ===
st.markdown("---")
st.markdown('''
    <div style="text-align: center; opacity: 0.7; padding: 20px;">
        🏪 <strong>Business Inventory Tracker</strong> v2.1<br>
        <small>Works in Light & Dark Mode</small>
    </div>
''', unsafe_allow_html=True)