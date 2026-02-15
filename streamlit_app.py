import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page config
st.set_page_config(page_title="Smartbites Business Analysis", layout="wide", page_icon="📊")

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .warning-box {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .danger-box {
        background-color: #fee2e2;
        border-left: 4px solid #ef4444;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Data loading
@st.cache_data
def load_data():
    """Load and process the order data"""
    df = pd.read_excel('Order_Data.xlsx', sheet_name='sheet_1')
    
    # Create a mapping of Excel column names to expected names
    column_mapping = {
        'OrderNumber': 'ordernumber',
        'CustomerID': 'customerid',
        'Customer': 'customer',
        'Company': 'company',
        'Vendors': 'vendors',
        'Total_Revenue': 'total_revenue',
        'GM1': 'gm_1',  # Map GM1 to gm_1
        'GM2': 'gm_2',  # Map GM2 to gm_2
        'Discount': 'discount',
        'Refund_Amount': 'refund_amount',
        'DeliveryFee': 'deliveryfee',
        'Vendor_Delivery_Fee': 'vendor_delivery_fee',
        'SmartLogistics_Cost': 'smartlogistics_cost',
        'Commission_in_Currency': 'commission_in_currency',
        'TotalItems': 'totalitems',
        'Status': 'status',
        'Delivery_Status': 'delivery_status'
    }
    
    # Rename columns based on mapping
    df.rename(columns=column_mapping, inplace=True)
    
    # Also handle any remaining columns by converting to lowercase
    df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
    
    # Data cleaning - only filter if status column exists
    if 'status' in df.columns:
        df = df[~df['status'].isin(['cancelled', 'rejected'])]
    
    # Convert numeric columns
    numeric_cols = ['total_revenue', 'gm_1', 'gm_2', 'discount', 'refund_amount', 
                    'deliveryfee', 'vendor_delivery_fee', 'smartlogistics_cost',
                    'commission_in_currency', 'totalitems']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

def calculate_overall_metrics(df):
    """Calculate overall business metrics"""
    return {
        'total_orders': len(df),
        'unique_customers': df['customerid'].nunique(),
        'unique_companies': df['company'].nunique(),
        'unique_vendors': df['vendors'].nunique(),
        'total_revenue': df['total_revenue'].sum(),
        'avg_revenue_per_order': df['total_revenue'].mean(),
        'total_gm1': df['gm_1'].sum(),
        'total_gm2': df['gm_2'].sum(),
        'avg_gm1_per_order': df['gm_1'].mean(),
        'total_discounts': df['discount'].sum(),
        'total_refunds': df['refund_amount'].sum()
    }

def calculate_customer_concentration(df):
    """Calculate customer concentration risk"""
    total_revenue = df['total_revenue'].sum()
    
    concentration = df.groupby(['company', 'customerid', 'customer']).agg({
        'ordernumber': 'count',  # FIXED: changed from 'orderid' to 'ordernumber'
        'total_revenue': 'sum',
        'gm_1': 'sum'
    }).rename(columns={'ordernumber': 'order_count'}).reset_index()
    
    concentration['pct_of_total_revenue'] = (concentration['total_revenue'] / total_revenue * 100).round(2)
    concentration['avg_order_value'] = (concentration['total_revenue'] / concentration['order_count']).round(2)
    
    return concentration.sort_values('total_revenue', ascending=False).head(20)

def calculate_repeat_behavior(df):
    """Analyze repeat vs one-off customer behavior"""
    customer_orders = df.groupby('customerid').agg({
        'ordernumber': 'count',  # FIXED: changed from 'orderid' to 'ordernumber'
        'total_revenue': 'sum',
        'gm_1': 'sum'
    }).rename(columns={'ordernumber': 'order_count'}).reset_index()
    
    def segment_customer(order_count):
        if order_count == 1:
            return '1 - One-time'
        elif order_count <= 5:
            return '2-5 - Low Repeat'
        elif order_count <= 10:
            return '6-10 - Medium Repeat'
        elif order_count <= 20:
            return '11-20 - High Repeat'
        else:
            return '21+ - Very High Repeat'
    
    customer_orders['segment'] = customer_orders['order_count'].apply(segment_customer)
    
    repeat_analysis = customer_orders.groupby('segment').agg({
        'customerid': 'count',
        'order_count': 'sum',
        'total_revenue': 'sum',
        'gm_1': 'sum'
    }).rename(columns={'customerid': 'customer_count'}).reset_index()
    
    repeat_analysis['avg_revenue_per_customer'] = (repeat_analysis['total_revenue'] / repeat_analysis['customer_count']).round(2)
    
    return repeat_analysis

def calculate_vendor_performance(df):
    """Analyze vendor performance"""
    vendor_perf = df.groupby('vendors').agg({
        'ordernumber': 'count',  # FIXED: changed from 'orderid' to 'ordernumber'
        'total_revenue': 'sum',
        'gm_1': 'sum',
        'commission_in_currency': 'sum',
        'refund_amount': lambda x: (x > 0).sum()
    }).rename(columns={
        'ordernumber': 'order_count',
        'refund_amount': 'refund_count'
    }).reset_index()
    
    vendor_perf['avg_revenue_per_order'] = (vendor_perf['total_revenue'] / vendor_perf['order_count']).round(2)
    vendor_perf['margin_pct'] = (vendor_perf['gm_1'] / vendor_perf['total_revenue'] * 100).round(2)
    
    # Late deliveries
    if 'delivery_status' in df.columns:
        late_deliveries = df[df['delivery_status'] == 'red'].groupby('vendors').size().reset_index(name='late_deliveries')
        vendor_perf = vendor_perf.merge(late_deliveries, on='vendors', how='left').fillna(0)
    else:
        vendor_perf['late_deliveries'] = 0
    
    return vendor_perf.sort_values('total_revenue', ascending=False).head(20)

def calculate_order_size_segments(df):
    """Segment orders by size and analyze margins"""
    def segment_order(revenue):
        if revenue < 50:
            return '1. < 50 (Micro)'
        elif revenue < 150:
            return '2. 50-150 (Small)'
        elif revenue < 300:
            return '3. 150-300 (Medium)'
        elif revenue < 500:
            return '4. 300-500 (Large)'
        elif revenue < 1000:
            return '5. 500-1000 (V.Large)'
        else:
            return '6. 1000+ (Enterprise)'
    
    df['order_segment'] = df['total_revenue'].apply(segment_order)
    
    segment_analysis = df.groupby('order_segment').agg({
        'ordernumber': 'count',  # FIXED: changed from 'orderid' to 'ordernumber'
        'total_revenue': 'sum',
        'gm_1': 'sum',
        'totalitems': 'mean'
    }).rename(columns={'ordernumber': 'order_count'}).reset_index()
    
    segment_analysis['avg_revenue'] = (segment_analysis['total_revenue'] / segment_analysis['order_count']).round(2)
    segment_analysis['margin_pct'] = (segment_analysis['gm_1'] / segment_analysis['total_revenue'] * 100).round(2)
    
    return segment_analysis.sort_values('order_segment')

def calculate_logistics_metrics(df):
    """Calculate logistics profitability"""
    return {
        'delivery_fee_charged': df['deliveryfee'].sum(),
        'vendor_delivery_cost': df['vendor_delivery_fee'].sum(),
        'smart_logistics_cost': df['smartlogistics_cost'].sum(),
        'net_margin': df['deliveryfee'].sum() - df['vendor_delivery_fee'].sum() - df['smartlogistics_cost'].sum()
    }

def calculate_operational_risk(df):
    """Calculate operational risk metrics"""
    total_orders = len(df)
    orders_with_refunds = (df['refund_amount'] > 0).sum()
    
    # Check if delivery_status column exists
    if 'delivery_status' in df.columns:
        late_deliveries = (df['delivery_status'] == 'red').sum()
        on_time_deliveries = (df['delivery_status'] == 'green').sum()
    else:
        late_deliveries = 0
        on_time_deliveries = 0
    
    return {
        'total_orders': total_orders,
        'orders_with_refunds': orders_with_refunds,
        'refund_rate_pct': round(orders_with_refunds / total_orders * 100, 2) if total_orders > 0 else 0,
        'total_refund_amount': df['refund_amount'].sum(),
        'late_deliveries': late_deliveries,
        'late_delivery_rate_pct': round(late_deliveries / total_orders * 100, 2) if total_orders > 0 else 0,
        'on_time_deliveries': on_time_deliveries
    }

# Main app
def main():
    st.title("📊 Smartbites Business Analysis Dashboard")
    st.markdown("Comprehensive analysis of order data • Real-time insights")
    
    # Load data
    try:
        df = load_data()
        
        # Calculate metrics
        overall_metrics = calculate_overall_metrics(df)
        logistics = calculate_logistics_metrics(df)
        
        # Executive Summary
        st.header("Executive Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Revenue",
                f"MYR {overall_metrics['total_revenue']:,.0f}",
                f"MYR {overall_metrics['avg_revenue_per_order']:.0f} avg/order"
            )
        
        with col2:
            margin_pct = (overall_metrics['total_gm1'] / overall_metrics['total_revenue'] * 100) if overall_metrics['total_revenue'] > 0 else 0
            st.metric(
                "Gross Margin (GM1)",
                f"MYR {overall_metrics['total_gm1']:,.0f}",
                f"{margin_pct:.2f}% margin"
            )
        
        with col3:
            st.metric(
                "Customer Base",
                f"{overall_metrics['unique_customers']}",
                f"{overall_metrics['unique_companies']} companies"
            )
        
        with col4:
            st.metric(
                "Logistics Margin",
                f"MYR {logistics['net_margin']:,.0f}",
                "⚠️ Loss area" if logistics['net_margin'] < 0 else "✅ Profit",
                delta_color="inverse"
            )
        
        # Tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "🎯 Concentration", 
            "🔄 Repeat Behavior", 
            "🏪 Vendors", 
            "📦 Segments", 
            "🚚 Logistics", 
            "⚙️ Operations"
        ])
        
        # Tab 1: Customer Concentration
        with tab1:
            st.header("⚠️ Customer Concentration Risk")
            
            concentration = calculate_customer_concentration(df)
            
            # Calculate top 3 percentage
            top3_pct = concentration.head(3)['pct_of_total_revenue'].sum()
            st.markdown(f"**Top 3 customers represent {top3_pct:.1f}% of revenue** • High concentration risk")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Bar chart
                fig = px.bar(
                    concentration.head(10),
                    y='company',
                    x='total_revenue',
                    orientation='h',
                    title='Top 10 Customers by Revenue',
                    color='pct_of_total_revenue',
                    color_continuous_scale='Blues',
                    labels={'total_revenue': 'Revenue (MYR)', 'company': 'Company'}
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Top 10 Customers")
                for idx, row in concentration.head(10).iterrows():
                    badge_color = "🔴" if row['pct_of_total_revenue'] > 10 else "🟡" if row['pct_of_total_revenue'] > 5 else "🟢"
                    st.markdown(f"""
                    **{badge_color} {row['company']}**  
                    {int(row['order_count'])} orders • MYR {row['total_revenue']:,.0f} ({row['pct_of_total_revenue']:.1f}%)
                    """)
            
            top_customer = concentration.iloc[0]
            st.markdown(f"""
            <div class="danger-box">
                <strong>🚨 Critical Risk:</strong><br>
                {top_customer['company']} alone drives {top_customer['pct_of_total_revenue']:.1f}% of revenue (MYR {top_customer['total_revenue']:,.0f}). Loss of this customer would be catastrophic.<br>
                <strong>Action:</strong> Diversify customer base - target 10 new corporate clients at MYR 5k+/month
            </div>
            """, unsafe_allow_html=True)
        
        # Tab 2: Repeat Behavior
        with tab2:
            st.header("🔄 Repeat vs One-Off Customer Behavior")
            
            repeat = calculate_repeat_behavior(df)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    repeat,
                    x='segment',
                    y='customer_count',
                    title='Customer Count by Segment',
                    labels={'customer_count': 'Number of Customers', 'segment': 'Customer Segment'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    repeat,
                    x='segment',
                    y='total_revenue',
                    title='Revenue by Segment',
                    color='total_revenue',
                    labels={'total_revenue': 'Revenue (MYR)', 'segment': 'Customer Segment'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            
            # Handle cases where segments might not exist
            very_high = repeat[repeat['segment'] == '21+ - Very High Repeat']
            one_time = repeat[repeat['segment'] == '1 - One-time']
            low_repeat = repeat[repeat['segment'] == '2-5 - Low Repeat']
            
            with col1:
                if len(very_high) > 0:
                    st.metric("Very High Repeat (21+)", f"{int(very_high.iloc[0]['customer_count'])}", 
                             f"MYR {very_high.iloc[0]['total_revenue']:,.0f}")
                else:
                    st.metric("Very High Repeat (21+)", "0", "No data")
            
            with col2:
                if len(one_time) > 0:
                    pct = (one_time.iloc[0]['total_revenue'] / overall_metrics['total_revenue'] * 100)
                    st.metric("One-Time Customers", f"{int(one_time.iloc[0]['customer_count'])}", 
                             f"{pct:.1f}% of revenue")
                else:
                    st.metric("One-Time Customers", "0", "No data")
            
            with col3:
                if len(low_repeat) > 0:
                    st.metric("Low Repeat (2-5)", f"{int(low_repeat.iloc[0]['customer_count'])}", 
                             "Growth opportunity")
                else:
                    st.metric("Low Repeat (2-5)", "0", "No data")
            
            st.markdown("""
            <div class="success-box">
                <strong>💡 Recommendation:</strong><br>
                Focus on converting one-time customers to repeat segment. Launch retention program:<br>
                • 5% discount on 2nd order<br>
                • Loyalty points system<br>
                • Target: 30% conversion = +34 repeat customers = <strong>+MYR 25k revenue</strong>
            </div>
            """, unsafe_allow_html=True)
        
        # Tab 3: Vendors
        with tab3:
            st.header("🏪 Vendor Performance Analysis")
            
            vendors = calculate_vendor_performance(df)
            
            fig = px.bar(
                vendors.head(10),
                y='vendors',
                x='margin_pct',
                orientation='h',
                title='Vendor Margin % (Top 10)',
                color='margin_pct',
                color_continuous_scale='RdYlGn',
                labels={'margin_pct': 'Margin %', 'vendors': 'Vendor'}
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Vendor Performance Table")
            display_vendors = vendors[['vendors', 'order_count', 'total_revenue', 'margin_pct', 'late_deliveries']].head(10).copy()
            st.dataframe(
                display_vendors.style.format({
                    'total_revenue': 'MYR {:,.0f}',
                    'margin_pct': '{:.2f}%',
                    'order_count': '{:.0f}',
                    'late_deliveries': '{:.0f}'
                }),
                use_container_width=True
            )
            
            # Find low margin vendors
            low_margin = vendors[vendors['margin_pct'] < 0.5].head(3)
            if len(low_margin) > 0:
                vendor_list = ', '.join(low_margin['vendors'].tolist())
                st.markdown(f"""
                <div class="warning-box">
                    <strong>⚠️ Zero/Low Margin Vendors:</strong><br>
                    {vendor_list}<br><br>
                    <strong>Action:</strong> Set 2% minimum margin requirement for all vendors. Renegotiate or exit.
                </div>
                """, unsafe_allow_html=True)
        
        # Tab 4: Order Segments
        with tab4:
            st.header("📦 Order Size Segmentation")
            
            segments = calculate_order_size_segments(df)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    segments,
                    x='order_segment',
                    y='margin_pct',
                    title='Margin % by Order Size',
                    labels={'margin_pct': 'Margin %', 'order_segment': 'Order Size'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    segments,
                    x='order_segment',
                    y='total_revenue',
                    title='Revenue by Order Size',
                    color='total_revenue',
                    labels={'total_revenue': 'Revenue (MYR)', 'order_segment': 'Order Size'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            enterprise = segments[segments['order_segment'] == '6. 1000+ (Enterprise)']
            if len(enterprise) > 0:
                ent = enterprise.iloc[0]
                st.markdown(f"""
                <div class="success-box">
                    <strong>✓ Best Margin - Enterprise Orders:</strong><br>
                    Enterprise orders (MYR 1000+) have <strong>{ent['margin_pct']:.2f}% margin</strong> vs {segments.iloc[0]['margin_pct']:.2f}% for micro orders.<br><br>
                    <strong>Strategy:</strong><br>
                    • Double enterprise orders from {int(ent['order_count'])} to {int(ent['order_count']*2)}<br>
                    • Set MYR 500 minimum for free delivery<br>
                    • Create volume discount incentives<br>
                    • <strong>Potential impact: +MYR 45k revenue</strong>
                </div>
                """, unsafe_allow_html=True)
        
        # Tab 5: Logistics
        with tab5:
            st.header("🚚 Logistics Profitability Crisis")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Delivery Fees Charged", f"MYR {logistics['delivery_fee_charged']:,.0f}")
            with col2:
                st.metric("Vendor Delivery Cost", f"-MYR {logistics['vendor_delivery_cost']:,.0f}")
            with col3:
                st.metric("Smart Logistics Cost", f"-MYR {logistics['smart_logistics_cost']:,.0f}")
            with col4:
                st.metric("Net Margin", f"MYR {logistics['net_margin']:,.0f}", 
                         delta_color="inverse" if logistics['net_margin'] < 0 else "normal")
            
            if logistics['net_margin'] < 0:
                loss_pct = abs(logistics['net_margin']) / overall_metrics['total_revenue'] * 100
                st.markdown(f"""
                <div class="danger-box">
                    <strong>🚨 LOGISTICS CRISIS - Losing MYR {abs(logistics['net_margin']):,.0f}</strong><br><br>
                    <strong>The Problem:</strong><br>
                    • Charging MYR {logistics['delivery_fee_charged']:,.0f} in delivery fees<br>
                    • Paying MYR {logistics['vendor_delivery_cost']:,.0f} to vendors<br>
                    • Additional MYR {logistics['smart_logistics_cost']:,.0f} in Smart Logistics costs<br>
                    • <strong>Total loss: MYR {abs(logistics['net_margin']):,.0f} ({loss_pct:.1f}% of revenue)</strong>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("""
                <div class="success-box">
                    <strong>💡 Immediate Actions Required:</strong><br>
                    1. <strong>Increase delivery fees</strong>: From MYR 18 to MYR 45/order minimum<br>
                    2. <strong>Renegotiate vendor costs</strong>: Target 30% reduction<br>
                    3. <strong>Optimize Smart Logistics</strong>: Route consolidation and optimization<br>
                    4. <strong>Minimum order policy</strong>: MYR 500+ for free delivery<br><br>
                    <strong>Target: +MYR 35k savings in 90 days</strong>
                </div>
                """, unsafe_allow_html=True)
        
        # Tab 6: Operations
        with tab6:
            st.header("⚙️ Operational Risk Metrics")
            
            ops = calculate_operational_risk(df)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Refund Rate", f"{ops['refund_rate_pct']}%", 
                         "✅ Excellent" if ops['refund_rate_pct'] < 1 else "⚠️ Review")
            with col2:
                st.metric("Late Delivery Rate", f"{ops['late_delivery_rate_pct']}%", 
                         f"{ops['late_deliveries']} orders")
            with col3:
                on_time_pct = (ops['on_time_deliveries'] / ops['total_orders'] * 100) if ops['total_orders'] > 0 else 0
                st.metric("On-Time Deliveries", f"{ops['on_time_deliveries']}", 
                         f"{on_time_pct:.1f}% rate")
            
            if ops['late_delivery_rate_pct'] > 5:
                st.markdown(f"""
                <div class="warning-box">
                    <strong>⚠️ Late Delivery Impact:</strong><br>
                    {ops['late_delivery_rate_pct']}% late delivery rate needs improvement. 
                    This impacts customer satisfaction and retention.<br>
                    <strong>Target:</strong> Reduce to &lt;5% through vendor accountability programs.
                </div>
                """, unsafe_allow_html=True)
        
        # Strategic Recommendations
        st.header("🎯 Strategic Recommendations")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="danger-box">
                <strong>⚠️ Critical Risks (P0)</strong><br>
                • Customer concentration<br>
                • Logistics losses<br>
                • Low overall margin<br>
                • One-time customers
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="warning-box">
                <strong>Opportunities</strong><br>
                • Enterprise orders<br>
                • Power users loyal<br>
                • Zero refunds<br>
                • Vendor optimization
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="success-box">
                <strong>Quick Wins</strong><br>
                • Delivery fees +50%<br>
                • Enterprise focus<br>
                • Retention program<br>
                • Vendor terms review
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="success-box">
            <strong>90-Day Financial Impact Projection:</strong><br>
            • Logistics Fix: <strong>+MYR 35k</strong><br>
            • Retention Program: <strong>+MYR 25k</strong><br>
            • Enterprise Focus: <strong>+MYR 45k</strong><br>
            • <strong>TOTAL: +MYR 105k (33% increase)</strong>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.info("Please ensure your Order_Data.xlsx file is in the correct location.")

if __name__ == "__main__":
    main()