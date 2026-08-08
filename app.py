import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

st.set_page_config(page_title="US Grid & Bottleneck Analyzer", layout="wide", initial_sidebar_state ="expanded")

st.title("US Energy Grid & AI Infrastructure Analyzer")
st.markdown("""
This dashboard analyzes bottlenecks in the U.S. power grid based on LBNL's interconnection queues.
It shows where the energy demands of AI data centers are reaching regulatory and physical limits.
""")

# Database connection
@st.cache_resource
def init_connection():
    try:
        db_url = st.secrets["DATABASE_URL"]
        return create_engine(db_url)
    except Exception as e:
        st.error(f"Critical Error: No Connection to Database. Details: {e}")
        st.stop()

engine = init_connection()

# Call data (using caching)
@st.cache_data(ttl=3600) # Saves data for one hour in cache
def load_bottleneck_data():
    try:
        query = "SELECT * FROM vw_queue_bottlenecks;"
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Error while loading Bottleneck-Data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_state_data():
    try:
        query = "SELECT * FROM vw_state_capacity;"
        df = pd.read_sql(query, engine)
        # Normalize column-name
        if 'total_mw' in df.columns:
            df = df.rename(columns={'total_mw': 'total_planned_mw'})
        return df
    except Exception as e:
        st.error(f"Error while loading State-Data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_raw_data():
    try:
        query = "SELECT q_date, state, region, project_name, developer, resource_type, capacity_mw FROM interconnection_queue LIMIT 200"
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Error while loading Raw-Data: {e}")
        return pd.DataFrame()

# Load data
df_bottlenecks = load_bottleneck_data()
df_states = load_state_data()
df_raw = load_raw_data()

# Canceling app, if data is empty
if df_bottlenecks.empty or df_states.empty:
    st.warning("Dashboard waits for available data...")
    st.stop()

# Global variables (calculated KPIs)
total_gw = df_bottlenecks['total_planned_mw'].sum() / 1000
total_projects = df_bottlenecks['active_projects'].sum()
avg_wait = df_bottlenecks['avg_years_in_queue'].mean()

# Dashboard
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. Overview",
    "2. Regional Analysis",
    "3. Capacity vs. AI Demand",
    "4. Risk Assessment",
    "5. Data & Methodology"
])

with tab1:
    st.header("Executive Summary")

    # KPI UI
    col1, col2, col3 = st.columns(3)
    col1.metric("Planned Capacity (total)", f"{total_gw:,.1f} GW")
    col2.metric("Active Projects in Queue", f"{total_projects:,}")
    col3.metric("Average Years in Queue (National)", f"{avg_wait:.1f} years")

    st.divider()

    # Interactive map
    st.subheader("Map of planned capacity per state")

    resource_list = df_states['resource_type'].dropna().unique().tolist()
    resource_list.sort()
    selected_resource = st.selectbox("Choose a Energy-Resource:", ["All"] + resource_list, key="overview_map")

    if selected_resource == "All":
        map_data = df_states.groupby('state', as_index=False)['total_planned_mw'].sum()
    else:
        filtered_df = df_states[df_states['resource_type'] == selected_resource]
        map_data = filtered_df.groupby('state', as_index=False)['total_planned_mw'].sum()

    fig_map = px.choropleth(
        map_data, locations='state', locationmode="USA-states", color='total_planned_mw',
        scope="usa", color_continuous_scale="Reds",
        labels={'total_planned_mw': 'Planned Capacity (MW)'},
        title=f"Capacity of: {selected_resource}"
    )
    fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

with tab2:
    st.header("Regional Analysis (ISO/RTO)")

    with st.expander("Reading Guide: “What Do These Grid Regions (ISOs) Mean?"):
        st.markdown("""
        The U.S. power grid is divided into various independent operators (known as **ISOs** or **RTOs**):
        * **PJM:** The world’s largest data center market (East Coast, including Virginia)
        * **ERCOT:** The Texas power grid (completely isolated from the rest of the U.S.)
        * **CAISO:** California (strong focus on solar and batteries)
        * **MISO:** Midwest (huge wind power potential)
        * **SPP:** Great Plains (the wind power hub of the U.S.)
        * **NYISO / ISONE:** New York and New England
        * **West / Southeast:** Often regions without a centralized market
        """)

    selected_region = st.selectbox("Choose a region (ISO):", df_bottlenecks['region'].unique())

    reg_df = df_states[df_states['region'] == selected_region]
    reg_grouped = reg_df.groupby('resource_type', as_index=False)['total_planned_mw'].sum().sort_values('total_planned_mw', ascending=False)

    fig_bar = px.bar(
        reg_grouped, x='resource_type', y='total_planned_mw',
        title=f"Energy-Mix in queue: {selected_region}",
        labels={'total_planned_mw': 'Planned Capacity (MW)', 'resource_type': 'Energy Resource'},
        color='total_planned_mw', color_continuous_scale="Blues"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    st.header("Capacity vs. AI Demand Simulation (2024-2030)")
    st.markdown("""
    **Scenario Calculator:** Simulate how the power supply from the queue scales with the AI-predicted demand.
    """)

    col_sim1, col_sim2 = st.columns(2)

    with col_sim1:
        st.subheader("1. AI-Demand-Scenario")
        ai_growth = st.slider("Annual Growth in AI Demand (%)", min_value=5, max_value=35, value=20, step=5)
        base_ai_gw = st.number_input("Current AI-Demand (GW in 2024)", min_value=0.0, value=25.0, step=5.0)

    with col_sim2:
        st.subheader("2. Grid Connection Scenario")
        realization_rate = st.slider("Queue Completion Rate (%)", min_value=10, max_value=60, value=16, step=2, 
                                     help="Based on this dataset, the historical realization rate "
                                          "(operational projects ÷ operational + withdrawn projects) is "
                                          "approximately 16.5%.")
        base_supply_gw = st.number_input("Available Base-Capacity (GW in 2024)", min_value=0.0, value=25.0, step=5.0,
                                         help="Currently allocated grid capacity for data centers. By default, this is equated with demand (market equilibrium in 2024).")
        
    years = list(range(2024, 2031))

    ai_demand_path = [base_ai_gw * ((1 + ai_growth / 100.0) ** (i)) for i in range(len(years))]

    realized_pipeline_gw = total_gw * (realization_rate / 100.0)
    yearly_addition = realized_pipeline_gw / (len(years) -1)
    supply_path = [base_supply_gw + (yearly_addition * i) for i in range(len(years))]

    df_sim = pd.DataFrame({
        "Year": years,
        "Projected AI Demand (GW)": ai_demand_path,
        "Feasible Proposal (GW)": supply_path
    })

    df_melted = df_sim.melt(
        id_vars="Year",
        value_vars=["Projected AI Demand (GW)", "Feasible Proposal (GW)"],
        var_name="Scenario",
        value_name="Capacity (GW)"
    )

    fig_sim = px.line(
        df_melted,
        x="Year",
        y="Capacity (GW)",
        color="Scenario",
        title="Projections Through 2030: AI Power Demand vs. Feasible Grid Capacity",
        markers=True,
        color_discrete_map={
            "Projected AI Demand (GW)": "#EF553B",
            "Feasible Proposal (GW)": "#00CC96"
        }
    )
    fig_sim.update_layout(hovermode="x unified")
    st.plotly_chart(fig_sim, use_container_width=True)

    gap_2030 = ai_demand_path[-1] - supply_path[-1]

    st.subheader("Analysis for the year 2030")
    if gap_2030 > 0:
        st.error(f"**Critical Shortfall:** With AI growth of {ai_growth}% per year and a realization rate of {realization_rate}%, a **supply gap of {gap_2030:,.1f} GW** will emerge by 2030.")
    else:
        st.success(f"**Supply Secured:** The feasible supply is sufficient to meet AI demand (buffer: {abs(gap_2030):,.1f} GW).")
        

with tab4:
    st.header("Grid Risk Assessment")
    st.markdown("Which regions pose the greatest risk of delays for AI data centers?")

    with st.expander("Methodology: How is the Risk Score calculated?"):
        st.markdown("""
        **Column Definitions:**
        * **active_projects:** Number of power plants/storage facilities in the local queue.
        * **total_planned_mw:** The total capacity of these projects in megawatts (storage volume).
        * **avg_years_in_queue:** Average waiting time a project has already spent awaiting grid connection.

        **The Grid Risk Score (0–100):**
        In practice, engineers use highly complex, local grid expansion costs. For this executive dashboard, i have developed a strategic **proxy score** that is immediately understandable to investors:
        It weights the *regional congestion volume (50%)* and the *historical wait time (50%)* relative to the national maximum. A score above 80 signals an urgent need for action on the part of data center developers.
        """)

    max_wait = df_bottlenecks['avg_years_in_queue'].max()
    max_mw = df_bottlenecks["total_planned_mw"].max()

    # DIVISION-BY-ZERO Safty
    max_wait = max_wait if max_wait > 0 else 1
    max_mw = max_mw if max_mw > 0 else 1

    df_risk = df_bottlenecks.copy()
    df_risk['Risk Score (0-100)'] = ((df_risk['avg_years_in_queue'] / max_wait) * 50 +
                                     (df_risk['total_planned_mw'] / max_mw) * 50).round(1)
    
    df_risk = df_risk.sort_values('Risk Score (0-100)', ascending=False)

    st.dataframe(
        df_risk[['region', 'active_projects', 'total_planned_mw', 'avg_years_in_queue', 'Risk Score (0-100)']],
        use_container_width=True, hide_index=True
    )

with tab5:
    st.header("Data Explorer & Methodology")

    with st.expander("View details on methodology and data sources"):
        st.markdown("""
        **Data source:** Lawrence Berkeley National Laboratory (LBNL) “Queued Up” dataset.
        **Filter Logic:**
        - Active projects only (`Status = Active/Operational`).
        - Withdrawn projects have been removed.
        **Risk Score:** A synthetic score (0–100) that normalizes and sums the average wait time and total congestion volume within an ISO region.

        **Data Quality Note:** The dataset contains one exceptionally large project (16,875 MW, classified as "Other"
         , in Mississippi) that accounts for roughly 23% of the total capacity in its resource category "Other". 
         This value was retained as provided by LBNL without independent verification.
        """)

    st.subheader("Export of Raw-Data")
    st.markdown("Download a sample of the cleaned database to perform your own analyses.")

    st.dataframe(df_raw, use_container_width=True, hide_index=True)

    csv = df_raw.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='us_grid_queue_sample.csv',
        mime='text/csv'
    )
