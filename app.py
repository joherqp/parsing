import streamlit as st
import asyncio
import pandas as pd
from scraper import run_full_fetcher
import json
import os
from datetime import date

# Page config
st.set_page_config(
    page_title="Skjaya Data Intelligence",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background: #0b0e14;
        color: #e2e8f0;
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(99, 102, 241, 0.4);
        filter: brightness(1.1);
    }
    
    .card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border-radius: 24px;
        padding: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 2rem;
    }
    
    h1, h2, h3 {
        background: linear-gradient(to right, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        letter-spacing: -0.02em;
    }
    
    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
    }
    
    .metric-container {
        display: flex;
        gap: 1rem;
        margin-top: 1rem;
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 1rem;
        border-radius: 12px;
        flex: 1;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)

def load_local_data():
    if os.path.exists("data.json"):
        with open("data.json", "r", encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return None
    return None


def clean_dataframe(df):
    """Remove UUIDs, technical IDs, and empty columns."""
    if df.empty:
        return df
    
    # Drop columns that are entirely null
    df = df.dropna(axis=1, how='all')
    
    # Identify technical columns to drop (UUIDs, internal IDs)
    cols_to_drop = []
    for col in df.columns:
        col_lower = col.lower()
        # Drop UUIDs and very long IDs
        if any(x in col_lower for x in ['uuid', 'id_']) or (col_lower == 'id' and df[col].astype(str).str.len().max() > 20):
            cols_to_drop.append(col)
            continue
            
        # Drop constant columns (only 1 unique value) to keep the view clean
        try:
            if df[col].astype(str).nunique() <= 1:
                cols_to_drop.append(col)
        except:
            # If for some reason we can't determine uniqueness, keep the column
            pass
            
    return df.drop(columns=cols_to_drop, errors='ignore')

def format_id_number(val):
    """Format numbers with thousand separators (1.000.000)."""
    try:
        f_val = float(val)
        return f"{f_val:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return val

def get_defaults(ordered_keys, options, total_limit=3):
    """Smart default column selector based on priority keys."""
    found = []
    for keys in ordered_keys:
        for c in options:
            if any(k in c.lower() for k in keys) and c not in found:
                found.append(c)
                break
    return found[:total_limit]

async def perform_sync(username, password):
    results, error = await run_full_fetcher(username, password, "data.json")
    return results, error

def clean_branch_name(name):
    """Membersihkan nama cabang: B11 -> Bogor, Wilayah Cikupa -> Cikupa, dll."""
    if not name or not isinstance(name, str): return name
    
    # 1. Mapping Kode Khusus
    code_map = {
        'B11': 'Bogor',
        'B21': 'Serang',
        'B42': 'Karawaci',
        'B43': 'Cikupa',
        'B31': 'Rangkas'
    }
    name_upper = name.strip().upper()
    if name_upper in code_map:
        return code_map[name_upper]
    
    # 2. Hapus kata 'Wilayah' (case insensitive)
    import re
    cleaned = re.sub(r'(?i)wilayah\s*', '', name).strip()
    return cleaned

def get_branch_map(full_data):
    """Build a mapping of Name -> Branch from all available datasets"""
    mapping = {}
    if not full_data: return mapping
    for key in full_data:
        if not isinstance(full_data[key], list): continue
        df_tmp = pd.DataFrame(full_data[key])
        n_col = next((c for c in df_tmp.columns if any(x in c.lower() for x in ['nama', 'name', 'pelanggan'])), None)
        # Tambahkan 'wilayah' sebagai alternatif cabang
        c_col = next((c for c in df_tmp.columns if any(x in c.lower() for x in ['cabang', 'branch', 'wilayah'])), None)
        if n_col and c_col:
            pairs = df_tmp[[n_col, c_col]].dropna().drop_duplicates()
            for _, row in pairs.iterrows():
                mapping[str(row[n_col]).strip().lower()] = clean_branch_name(str(row[c_col]).strip())
    return mapping

def main():
    if 'full_data' not in st.session_state:
        st.session_state['full_data'] = load_local_data()
    branch_map = get_branch_map(st.session_state['full_data'])

    # --- 1. Data Selection & Loading (Early for Sidebar) ---
    categories = {
        "Salesman": ["employee", "attendance"],
        "Pelanggan": ["customer", "customer_movement"],
        "Barang": ["product", "category"],
        "Penjualan": ["transaction_report", "transaction_po", "big_query"],
        "Setoran": ["deposit"],
        "Stok": ["inventory", "restock", "lost_return"]
    }
    
    # We need to know the menu first to decide if we show filters
    # So we use st.sidebar.radio directly to get the menu early
    with st.sidebar:
        st.header("⚙️ Actions")
        if 'sync_username' not in st.session_state: st.session_state['sync_username'] = "owner"
        if 'sync_password' not in st.session_state: st.session_state['sync_password'] = "admin"
        
        if st.button("🔄 Sync Data Sekarang", key="sync_top"):
            with st.spinner("Sinkronisasi data sedang berlangsung..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results, error = loop.run_until_complete(perform_sync(st.session_state['sync_username'], st.session_state['sync_password']))
                if error:
                    st.error(f"Sync failed: {error}")
                else:
                    st.success(f"Sync complete!")
                    st.session_state['full_data'] = load_local_data()
                    st.rerun()

    # Determine Menu (Use a placeholder for logic, but call later for UI order)
    if "nav_menu" not in st.session_state: st.session_state["nav_menu"] = "Data Monitoring"
    
    # Logic to get the menu value without rendering yet if possible, 
    # but in Streamlit, rendering is execution. 
    # So we'll render Sync, then Filters, then Navigation.
    
    # 1. Sync Button (Already rendered above)
    
    # 2. Data Selection & Filter (Rendered here if in Monitoring)
    df = None
    cat_choice = "Penjualan"
    selected_key = "big_query"
    
    # We use the session_state for the radio to "look ahead"
    menu = st.session_state.get("nav_menu", "Data Monitoring")

    if menu == "Data Monitoring" and st.session_state['full_data']:
        data = st.session_state['full_data']
        with st.sidebar:
            st.divider()
            st.header("📂 Data Selection")
            cat_list = list(categories.keys())
            cat_choice = st.selectbox("Select Category", cat_list, index=cat_list.index("Penjualan") if "Penjualan" in cat_list else 0)
            
            available_keys = [k for k in categories[cat_choice] if k in data and isinstance(data[k], list)]
            if available_keys:
                selected_key = st.selectbox("Select Dataset", available_keys, index=available_keys.index("big_query") if "big_query" in available_keys else 0)
                
                # Reset date mode if dataset changed
                if 'last_selected_dataset' not in st.session_state or st.session_state['last_selected_dataset'] != selected_key:
                    if 'date_mode_key' in st.session_state: del st.session_state['date_mode_key']
                    st.session_state['last_selected_dataset'] = selected_key

                raw_df = pd.DataFrame(data[selected_key])
                df = clean_dataframe(raw_df)
                
                # --- Smart Branch Fill ---
                c_col_existing = next((c for c in df.columns if any(x in c.lower() for x in ['cabang', 'branch', 'wilayah'])), None)
                n_col_existing = next((c for c in df.columns if any(x in c.lower() for x in ['nama', 'name', 'pelanggan'])), None)
                if c_col_existing:
                    df[c_col_existing] = df[c_col_existing].apply(clean_branch_name)
                elif n_col_existing:
                    df['cabang'] = df[n_col_existing].astype(str).str.strip().str.lower().map(branch_map)
                
                # --- Filter Pintar ---
                with st.expander("🔍 Filter Pintar", expanded=False):
                    date_cols = [c for c in df.columns if any(x in c.lower() for x in ['date', 'registered', 'time', 'tanggal'])]
                    if date_cols:
                        d_col = date_cols[0]
                        # Convert to datetime for filtering logic
                        df[d_col] = pd.to_datetime(df[d_col], errors='coerce')
                        # --- Smart Default Logic ---
                        if 'date_mode_key' not in st.session_state:
                            # Try 'Single' (Today) first
                            today_check = df[df[d_col].dt.date == date.today()]
                            if today_check.empty:
                                st.session_state['date_mode_key'] = "All Time"
                            else:
                                st.session_state['date_mode_key'] = "Single"
                        
                        date_options = ["All Time", "Single", "Range", "Multiple"]
                        current_mode = st.radio(
                            "Mode Tanggal", 
                            date_options, 
                            index=date_options.index(st.session_state['date_mode_key']),
                            horizontal=True,
                            key="date_mode_radio"
                        )
                        # Update session state for next run
                        st.session_state['date_mode_key'] = current_mode
                        
                        if current_mode == "Range":
                            today_val = date.today()
                            date_range = st.date_input("Rentang Tanggal", [today_val, today_val])
                            if len(date_range) == 2:
                                df = df[(df[d_col].dt.date >= date_range[0]) & (df[d_col].dt.date <= date_range[1])]
                        elif current_mode == "Single":
                            single_date = st.date_input("Pilih Tanggal", date.today())
                            df = df[df[d_col].dt.date == single_date]
                        elif current_mode == "Multiple":
                            valid_dates = [d for d in df[d_col].dt.date.unique() if pd.notnull(d)]
                            multi_dates = st.multiselect("Pilih Beberapa Tanggal", sorted(valid_dates, reverse=True))
                            if multi_dates:
                                df = df[df[d_col].dt.date.isin(multi_dates)]
                        # If "All Time", do nothing to df
                    
                    search_query = st.text_input("Pencarian Global")
                    if search_query:
                        df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]
                    
                    filter_col = st.selectbox("Filter Kolom Spesifik", ["None"] + list(df.columns))
                    if filter_col != "None":
                        unique_vals = sorted([str(x) for x in df[filter_col].unique() if pd.notnull(x)])
                        selected_vals = st.multiselect(f"Pilih {filter_col}", unique_vals)
                        if selected_vals:
                            df = df[df[filter_col].astype(str).isin(selected_vals)]

    # 3. Navigation (Rendered below Filter Pintar)
    st.sidebar.divider()
    menu = st.sidebar.radio("🛰️ Navigation", ["Data Monitoring", "Sync Engine"], key="nav_menu")

    if menu == "Sync Engine":
        st.title("🕸️ Skjaya Sync Engine")
        st.markdown("### Universal API Extraction & JSON Consolidation")
        
        if st.session_state['full_data']:
            data = st.session_state['full_data']
            st.markdown("""<div class="card"><h3>📊 Extraction Summary</h3>""", unsafe_allow_html=True)
            
            list_data = {k: v for k, v in data.items() if isinstance(v, list)}
            if list_data:
                cols = st.columns(min(len(list_data), 4))
                for i, (key, val) in enumerate(list_data.items()):
                    col_idx = i % 4
                    count = len(val)
                    cols[col_idx].markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 0.8rem; color: #94a3b8;">{key.upper()}</div>
                        <div style="font-size: 1.5rem; font-weight: 800; color: #818cf8;">{format_id_number(count)}</div>
                        <div style="font-size: 0.7rem; color: #64748b;">Records</div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.divider()
            st.markdown("### 🛠️ Raw Preview")
            available_preview = list(data.keys())
            if available_preview:
                preview_key = st.selectbox("Select API result to preview", available_preview)
                if isinstance(data[preview_key], list):
                    st.dataframe(pd.DataFrame(data[preview_key]), width="stretch")
                else:
                    st.json(data[preview_key])
        else:
            st.warning("No data found. Please start a sync or ensure data.json exists.")

    elif menu == "Data Monitoring":
        st.title("📈 Smart Monitoring Dashboard")
        
        if df is not None:
            # --- MAIN CONTENT ---
            st.markdown(f"""<div class="card"><h3>📊 Ringkasan {cat_choice}: {selected_key.title()}</h3>""", unsafe_allow_html=True)
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Data", format_id_number(len(df)))
            
            # Specialized Summaries
            if cat_choice == "Penjualan":
                price_col = next((c for c in df.columns if any(x in c.lower() for x in ['price', 'harga'])), None)
                qty_col = next((c for c in df.columns if any(x in c.lower() for x in ['qty', 'quantity', 'jumlah', 'terjual'])), None)
                disc_col = next((c for c in df.columns if any(x in c.lower() for x in ['discount', 'diskon', 'potongan'])), None)
                total_col = next((c for c in df.columns if any(x in c.lower() for x in ['total', 'amount', 'nominal'])), None)
                
                if price_col and qty_col:
                    temp_df = df.copy()
                    temp_df[price_col] = pd.to_numeric(temp_df[price_col], errors='coerce').fillna(0)
                    temp_df[qty_col] = pd.to_numeric(temp_df[qty_col], errors='coerce').fillna(0)
                    if disc_col:
                        temp_df[disc_col] = pd.to_numeric(temp_df[disc_col], errors='coerce').fillna(0)
                        calc_total = (temp_df[qty_col] * temp_df[price_col]) - temp_df[disc_col]
                    else:
                        calc_total = (temp_df[qty_col] * temp_df[price_col])
                    promo_qty = temp_df[temp_df[price_col] == 0][qty_col].sum()
                    m2.metric("Total Penjualan", f"Rp {format_id_number(calc_total.sum())}")
                    m3.metric("Qty Terjual", format_id_number(temp_df[qty_col].sum()))
                    m4.metric("Qty Promo", format_id_number(promo_qty))
                elif total_col:
                    m2.metric("Total Penjualan", f"Rp {format_id_number(pd.to_numeric(df[total_col], errors='coerce').sum())}")
            
            elif cat_choice == "Stok":
                stock_cols = [c for c in df.columns if any(x in c.lower() for x in ['stock', 'stok', 'qty', 'jumlah'])]
                if stock_cols:
                    # Robust numeric conversion
                    s_vals = pd.to_numeric(df[stock_cols[0]], errors='coerce').fillna(0)
                    total_stock = s_vals.sum()
                    m2.metric("Total Unit Stok", format_id_number(total_stock))
                    m3.metric("Item Unik", format_id_number(df[stock_cols[0]].nunique()))
                else:
                    m2.metric("Total Unit Stok", "0")
                    st.info("ℹ️ Kolom stok/qty tidak terdeteksi otomatis untuk dataset ini.")
            
            elif cat_choice == "Setoran":
                nominal_cols = [c for c in df.columns if any(x in c.lower() for x in ['amount', 'nominal', 'total'])]
                if nominal_cols:
                    total_setoran = df[nominal_cols[0]].astype(float).sum()
                    m2.metric("Total Setoran", f"Rp {format_id_number(total_setoran)}")

            st.markdown("</div>", unsafe_allow_html=True)
            
            # --- TABLE SECTION ---
            st.divider()
            view_mode = st.radio("Mode Tampilan", ["Pivot Mode (Pintar)", "Tabel Standar"], horizontal=True)
            
            if view_mode == "Tabel Standar":
                st.markdown("### 📄 Data Detail (Cleaned)")
                display_df = df.copy()
                for col in display_df.select_dtypes(include=['datetime']).columns:
                    display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M')
                st.dataframe(display_df, width="stretch")
            else:
                st.markdown("### 📊 Pivot Table (Pintar)")
                pivot_df_source = df.copy()
                # (Pivot logic continues here...)
                price_col = next((c for c in df.columns if any(x in c.lower() for x in ['price', 'harga'])), None)
                qty_col = next((c for c in df.columns if any(x in c.lower() for x in ['qty', 'quantity', 'jumlah', 'terjual'])), None)
                disc_col = next((c for c in df.columns if any(x in c.lower() for x in ['discount', 'diskon', 'potongan'])), None)
                if price_col and qty_col:
                    p_vals = pd.to_numeric(pivot_df_source[price_col], errors='coerce').fillna(0)
                    q_vals = pd.to_numeric(pivot_df_source[qty_col], errors='coerce').fillna(0)
                    d_vals = pd.to_numeric(pivot_df_source[disc_col], errors='coerce').fillna(0) if disc_col else 0
                    pivot_df_source['TOTAL'] = (p_vals * q_vals) - d_vals
                    st.info("💡 Kolom 'TOTAL' otomatis dibuat dari (Qty * Harga) - Diskon")

                all_cols = [c for c in pivot_df_source.columns if not any(x in c.lower() for x in ['uuid', 'id_', 'productid'])]
                p_col1, p_col2, p_col3, p_col4 = st.columns(4)
                with p_col1:
                    d_rows = get_defaults([['tanggal', 'date'], ['cabang', 'branch', 'warehouse', 'location'], ['nama', 'name', 'pelanggan', 'customer']], all_cols, 3)
                    p_index = st.multiselect("Baris (Rows)", all_cols, default=d_rows if d_rows else [all_cols[0]])
                with p_col2:
                    d_cols = get_defaults([['produk', 'product', 'barang', 'item']], all_cols, 1)
                    p_columns = st.multiselect("Kolom (Columns)", all_cols, default=d_cols)
                with p_col3:
                    numeric_cols = pivot_df_source.select_dtypes(include=['number']).columns.tolist()
                    d_vals = get_defaults([['qty', 'jumlah', 'stok', 'stock'], ['total', 'amount', 'calc_total']], numeric_cols, 2)
                    p_values = st.multiselect("Nilai (Values)", numeric_cols if numeric_cols else all_cols, default=d_vals)
                with p_col4:
                    p_agg = st.selectbox("Fungsi", ["sum", "count", "mean", "max", "min"])
                    show_total = st.checkbox("Tampilkan Grand Total", value=True)
                
                if p_index and p_values:
                    try:
                        needed_cols = list(set(p_index + p_values + p_columns))
                        pivot_df_source = pivot_df_source[needed_cols].copy()
                        for col in p_index + p_columns:
                            pivot_df_source[col] = pivot_df_source[col].astype(str)
                        for v_col in p_values:
                            pivot_df_source[v_col] = pd.to_numeric(pivot_df_source[v_col], errors='coerce').fillna(0).astype(float)

                        agg_map = {v: p_agg for v in p_values}
                        pivot_table_res = pd.pivot_table(pivot_df_source, index=p_index, columns=None if not p_columns else p_columns, values=p_values, aggfunc=agg_map, margins=show_total, margins_name='TOTAL AKHIR')
                        
                        if isinstance(pivot_table_res.index, pd.MultiIndex):
                            pivot_table_res.index.names = [n.upper() if n else n for n in pivot_table_res.index.names]
                        else:
                            pivot_table_res.index.name = pivot_table_res.index.name.upper() if pivot_table_res.index.name else None

                        if isinstance(pivot_table_res.columns, pd.MultiIndex):
                            new_levels = [[str(x).upper() for x in level] for level in pivot_table_res.columns.levels]
                            pivot_table_res.columns = pivot_table_res.columns.set_levels(new_levels)
                        else:
                            pivot_table_res.columns = [c.upper() for c in pivot_table_res.columns]
                        if p_columns and len(p_values) > 1:
                            pivot_table_res = pivot_table_res.reorder_levels([1, 0], axis=1) if len(p_columns) == 1 else pivot_table_res
                            val_order = {v.upper(): i for i, v in enumerate(p_values)}
                            sorted_cols = sorted(pivot_table_res.columns, key=lambda x: (1 if x[0] == 'TOTAL AKHIR' or x[0] == '' else 0, x[0], val_order.get(str(x[1]).upper(), 99)))
                            pivot_table_res = pivot_table_res[sorted_cols]
                        
                        if len(p_index) > 1 and not pivot_table_res.empty:
                            final_rows = []
                            has_grand = 'TOTAL AKHIR' in pivot_table_res.index.get_level_values(0)
                            main_data = pivot_table_res.drop('TOTAL AKHIR', level=0) if has_grand else pivot_table_res
                            
                            if not main_data.empty:
                                # Level 0 Grouping (e.g. Tanggal)
                                for name0, group0 in main_data.groupby(level=0, sort=False):
                                    # --- HEADER LEVEL 0 ---
                                    label0 = f"● {name0}"
                                    sub_val0 = group0.sum() if p_agg == "sum" else group0.mean()
                                    sub_idx0 = list(group0.index[0])
                                    sub_idx0[0] = label0
                                    for i in range(1, len(sub_idx0)): sub_idx0[i] = ""
                                    final_rows.append(pd.DataFrame([sub_val0.values], columns=group0.columns, index=pd.MultiIndex.from_tuples([tuple(sub_idx0)], names=group0.index.names)))
                                    
                                    if len(p_index) == 2:
                                        # Case for exactly 2 levels: Header 0 -> Details (Level 1)
                                        details = group0.copy()
                                        new_indices = []
                                        for idx in details.index:
                                            idx_list = list(idx)
                                            idx_list[0] = "  └ ●"
                                            if len(idx_list) > 1:
                                                idx_list[1] = f"○ {idx_list[1]}"
                                            new_indices.append(tuple(idx_list))
                                        details.index = pd.MultiIndex.from_tuples(new_indices, names=details.index.names)
                                        final_rows.append(details)
                                    
                                    elif len(p_index) >= 3:
                                        # Case for 3+ levels: Header 0 -> Header 1 -> Details (Level 2)
                                        for name1, group1 in group0.groupby(level=1, sort=False):
                                            # --- HEADER LEVEL 1 ---
                                            label1 = f"○ {name1}"
                                            sub_val1 = group1.sum() if p_agg == "sum" else group1.mean()
                                            sub_idx1 = list(group1.index[0])
                                            sub_idx1[0] = "  └ ●"
                                            sub_idx1[1] = label1
                                            for i in range(2, len(sub_idx1)): sub_idx1[i] = ""
                                            final_rows.append(pd.DataFrame([sub_val1.values], columns=group1.columns, index=pd.MultiIndex.from_tuples([tuple(sub_idx1)], names=group1.index.names)))
                                            
                                            # --- DETAILS (Level 2) ---
                                            details = group1.copy()
                                            new_indices = []
                                            for idx in details.index:
                                                idx_list = list(idx)
                                                idx_list[0] = "  └ ●"
                                                idx_list[1] = "    └ ○"
                                                if len(idx_list) > 2:
                                                    idx_list[2] = f"      • {idx_list[2]}"
                                                new_indices.append(tuple(idx_list))
                                            details.index = pd.MultiIndex.from_tuples(new_indices, names=details.index.names)
                                            final_rows.append(details)
                                    else:
                                        final_rows.append(group0)
                                
                            if has_grand:
                                grand_row = pivot_table_res.xs('TOTAL AKHIR', level=0, drop_level=False)
                                final_rows.append(grand_row)
                            
                            if final_rows:
                                pivot_table_res = pd.concat(final_rows)

                        # --- MERGE LOOK WITH STYLING (Camouflage) ---
                        df_styled = pivot_table_res.reset_index()
                        
                        def highlight_repeats(data):
                            attr = 'color: transparent;'
                            mask = pd.DataFrame('', index=data.index, columns=data.columns)
                            for col_name in df_styled.columns[:len(p_index)]:
                                is_repeat = data[col_name] == data[col_name].shift()
                                is_grand_total = data.apply(lambda x: any("TOTAL AKHIR" in str(v).upper() for v in x), axis=1)
                                mask.loc[is_repeat & ~is_grand_total, col_name] = attr
                            return mask

                        st.dataframe(
                            df_styled.style.apply(highlight_repeats, axis=None).format(lambda x: format_id_number(x) if isinstance(x, (int, float)) else x),
                            width="stretch",
                            hide_index=True
                        )
                    except Exception as e:
                        st.error(f"⚠️ Gagal membuat pivot: {str(e)}")
                        st.info("Saran: Jika kolom 'tanggal' terpilih sebagai 'Nilai', pindahkan ke 'Baris' atau hapus.")
                else:
                    st.info("Pilih Baris dan Nilai untuk melihat tabel pivot.")
            st.download_button(
                label=f"📥 Download {selected_key}_filtered.csv",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name=f"{selected_key}_filtered.csv",
                mime="text/csv"
            )
        else:
            st.warning("Data belum tersedia. Silakan lakukan Sinkronisasi di menu Sync Engine.")

    # --- SIDEBAR BOTTOM SECTION ---
    with st.sidebar:
        st.divider()
        st.header("🔐 Authentication")
        # Menggunakan key agar tersambung dengan session_state yang dipakai tombol Sync di atas
        st.text_input("Username", value="owner", key="sync_username")
        st.text_input("Password", value="admin", type="password", key="sync_password")

if __name__ == "__main__":
    main()
