from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# ------------------------------------------------------------
# Page configuration
# ------------------------------------------------------------

st.set_page_config(
    page_title="E-commerce Customer Analytics",
    page_icon="📊",
    layout="wide"
)


# ------------------------------------------------------------
# File paths
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
RAW_DATA_DIR = BASE_DIR / "data" / "raw"


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

@st.cache_data
def load_data():
    orders = pd.read_csv(
        DATA_DIR / "orders_clean.csv",
        parse_dates=["order_purchase_timestamp"]
    )

    customers = pd.read_csv(
        DATA_DIR / "customers_clean.csv"
    )

    order_items = pd.read_csv(
        DATA_DIR / "order_items_clean.csv"
    )

    products = pd.read_csv(
        DATA_DIR / "products_clean.csv"
    )

    category_translation = pd.read_csv(
    RAW_DATA_DIR / "product_category_name_translation.csv"
    )

    sellers = pd.read_csv(
    DATA_DIR / "sellers_clean.csv"
    )

    payments = pd.read_csv(
    RAW_DATA_DIR / "olist_order_payments_dataset.csv"
    )


    return (
        orders,
        customers,
        order_items,
        products,
        category_translation,
        sellers,
        payments
    )


(
    orders,
    customers,
    order_items,
    products,
    category_translation,
    sellers,
    payments
) = load_data()

# ------------------------------------------------------------
# Page title
# ------------------------------------------------------------

st.title("E-commerce Customer Analytics")

st.caption(
    "Marketplace performance, customer behavior, product trends, "
    "operations, sellers, and payment analytics."
)

# ------------------------------------------------------------
# Sidebar Filters
# ------------------------------------------------------------

st.sidebar.header("Filters")


# Date filter
min_date = orders["order_purchase_timestamp"].min().date()
max_date = orders["order_purchase_timestamp"].max().date()

selected_dates = st.sidebar.date_input(
    "Order Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)


# Customer state filter
customer_states = sorted(
    customers["customer_state"].dropna().unique()
)

selected_states = st.sidebar.multiselect(
    "Customer State",
    options=customer_states,
    placeholder="Select one or more states"
)

st.sidebar.markdown("---")
st.sidebar.subheader("Current Selection")

st.sidebar.write(
    f"Date: {selected_dates[0]} to {selected_dates[1]}"
)

if selected_states:
    st.sidebar.write(
        "States: " + ", ".join(selected_states)
    )
else:
    st.sidebar.write(
        "States: All"
    )

# ------------------------------------------------------------
# Executive Overview
# ------------------------------------------------------------

st.header("Executive Overview")


# Delivered orders only
delivered_orders = orders[
    orders["order_status"] == "delivered"
].copy()


# ------------------------------------------------------------
# Apply filters
# ------------------------------------------------------------

# Date filter
start_date, end_date = selected_dates

delivered_orders = delivered_orders[
    (
        delivered_orders["order_purchase_timestamp"].dt.date >= start_date
    )
    &
    (
        delivered_orders["order_purchase_timestamp"].dt.date <= end_date
    )
].copy()


# Customer state filter
if selected_states:
    filtered_customers = customers[
        customers["customer_state"].isin(selected_states)
    ].copy()
else:
    filtered_customers = customers.copy()


delivered_orders = delivered_orders[
    delivered_orders["customer_id"].isin(
        filtered_customers["customer_id"]
    )
].copy()


# ------------------------------------------------------------
# Delivered order items
# ------------------------------------------------------------

delivered_items = order_items[
    order_items["order_id"].isin(delivered_orders["order_id"])
].copy()


# ------------------------------------------------------------
# KPI calculations
# ------------------------------------------------------------

# GMV
gmv = delivered_items["price"].sum()


# Delivered orders
total_orders = delivered_orders["order_id"].nunique()


# Customer base
customer_base = delivered_orders.merge(
    customers[
        ["customer_id", "customer_unique_id"]
    ],
    on="customer_id",
    how="left"
)


# Unique customers
unique_customers = customer_base[
    "customer_unique_id"
].nunique()


# AOV
if total_orders > 0:
    aov = gmv / total_orders
else:
    aov = 0


# Repeat customer rate
customer_frequency = (
    customer_base
    .groupby("customer_unique_id")["order_id"]
    .nunique()
)

if len(customer_frequency) > 0:
    repeat_customer_rate = (
        (customer_frequency > 1).mean() * 100
    )
else:
    repeat_customer_rate = 0


# ------------------------------------------------------------
# Monthly GMV calculation
# ------------------------------------------------------------

monthly_gmv = delivered_items.merge(
    delivered_orders[
        ["order_id", "order_purchase_timestamp"]
    ],
    on="order_id",
    how="left"
)

monthly_gmv["order_purchase_timestamp"] = pd.to_datetime(
    monthly_gmv["order_purchase_timestamp"]
)

monthly_gmv["month"] = (
    monthly_gmv["order_purchase_timestamp"]
    .dt.to_period("M")
    .astype(str)
)

monthly_gmv = (
    monthly_gmv
    .groupby("month", as_index=False)["price"]
    .sum()
)


# ------------------------------------------------------------
# KPI cards
# ------------------------------------------------------------

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "GMV",
    f"R$ {gmv:,.0f}"
)

col2.metric(
    "Delivered Orders",
    f"{total_orders:,}"
)

col3.metric(
    "Unique Customers",
    f"{unique_customers:,}"
)

col4.metric(
    "AOV",
    f"R$ {aov:,.2f}"
)

col5.metric(
    "Repeat Customer Rate",
    f"{repeat_customer_rate:.2f}%"
)


# ------------------------------------------------------------
# Key Insights
# ------------------------------------------------------------

st.subheader("Key Insights")


# Top customer state
state_insight = (
    customer_base
    .merge(
        customers[
            ["customer_id", "customer_state"]
        ],
        on="customer_id",
        how="left"
    )
    .groupby("customer_state")["customer_unique_id"]
    .nunique()
    .sort_values(ascending=False)
)


if not state_insight.empty:
    top_state = state_insight.index[0]
    top_state_customers = state_insight.iloc[0]
else:
    top_state = "N/A"
    top_state_customers = 0


# Peak GMV month
if not monthly_gmv.empty:

    peak_month_row = monthly_gmv.loc[
        monthly_gmv["price"].idxmax()
    ]

    peak_month = pd.to_datetime(
        peak_month_row["month"]
    ).strftime("%b %Y")

    peak_gmv = peak_month_row["price"]

else:
    peak_month = "N/A"
    peak_gmv = 0


# Insight cards
insight_col1, insight_col2, insight_col3 = st.columns(3)

insight_col1.info(
    f"Top customer market: {top_state} "
    f"with {top_state_customers:,.0f} unique customers."
)

insight_col2.info(
    f"Repeat customer rate: {repeat_customer_rate:.2f}%. "
    f"Most customers purchase only once."
)

insight_col3.info(
    f"Peak monthly GMV: R$ {peak_gmv:,.0f} "
    f"in {peak_month}."
)


# ------------------------------------------------------------
# Monthly GMV Trend
# ------------------------------------------------------------

st.subheader("Monthly GMV Trend")


if not monthly_gmv.empty:

    chart_data = monthly_gmv.copy()

    chart_data = chart_data.rename(
        columns={"price": "GMV"}
    )

    chart_data["month"] = pd.to_datetime(
        chart_data["month"]
    )


    gmv_chart = (
        alt.Chart(chart_data)
        .mark_line(
            point={
                "filled": True,
                "size": 80
            },
            color="#2F6BFF"
        )
        .encode(
            x=alt.X(
                "month:T",
                title="Month",
                axis=alt.Axis(
                    format="%b %Y"
                )
            ),
            y=alt.Y(
                "GMV:Q",
                title="GMV (R$)",
                scale=alt.Scale(
                    zero=True
                )
            ),
            tooltip=[
                alt.Tooltip(
                    "month:T",
                    title="Month",
                    format="%B %Y"
                ),
                alt.Tooltip(
                    "GMV:Q",
                    title="GMV",
                    format=",.2f"
                )
            ]
        )
        .properties(
            height=400
        )
    )

    st.altair_chart(
        gmv_chart,
        use_container_width=True
    )

else:

    st.info(
        "No delivered orders are available "
        "for the selected filters."
    )

# ------------------------------------------------------------
# Customer Analysis
# ------------------------------------------------------------

st.header("Customer Analysis")

customer_type = (
    customer_frequency
    .reset_index(name="order_count")
)

customer_type["customer_type"] = customer_type["order_count"].apply(
    lambda x: "Repeat Customer" if x > 1 else "One-time Customer"
)

customer_type_summary = (
    customer_type
    .groupby("customer_type")
    .size()
    .reset_index(name="customer_count")
)


# Top customer states
customer_state_summary = (
    customer_base
    .merge(
        customers[
            ["customer_id", "customer_state"]
        ],
        on="customer_id",
        how="left"
    )
    .groupby("customer_state")["customer_unique_id"]
    .nunique()
    .reset_index(name="customer_count")
    .sort_values("customer_count", ascending=False)
    .head(10)
)


left_col, right_col = st.columns(2)


# ------------------------------------------------------------
# Customer Type Chart
# ------------------------------------------------------------

with left_col:

    st.subheader("Customer Type")

    customer_chart = (
        alt.Chart(customer_type_summary)
        .mark_bar(color="#16A085")
        .encode(
            x=alt.X(
                "customer_type:N",
                title="Customer Type"
            ),
            y=alt.Y(
                "customer_count:Q",
                title="Number of Customers"
            ),
            tooltip=[
                alt.Tooltip(
                    "customer_type:N",
                    title="Customer Type"
                ),
                alt.Tooltip(
                    "customer_count:Q",
                    title="Customers",
                    format=","
                )
            ]
        )
        .properties(
            height=350
        )
    )

    st.altair_chart(
        customer_chart,
        use_container_width=True
    )


# ------------------------------------------------------------
# Top Customer States
# ------------------------------------------------------------

with right_col:

    st.subheader("Top 10 Customer States")

    state_chart = (
        alt.Chart(customer_state_summary)
        .mark_bar(color="#16A085")
        .encode(
            x=alt.X(
                "customer_count:Q",
                title="Number of Customers"
            ),
            y=alt.Y(
                "customer_state:N",
                title="State",
                sort="-x"
            ),
            tooltip=[
                alt.Tooltip(
                    "customer_state:N",
                    title="State"
                ),
                alt.Tooltip(
                    "customer_count:Q",
                    title="Customers",
                    format=","
                )
            ]
        )
        .properties(
            height=350
        )
    )

    st.altair_chart(
        state_chart,
        use_container_width=True
    )

# ------------------------------------------------------------
# Product Analysis
# ------------------------------------------------------------

st.header("Product Analysis")


# Merge delivered items with product information
product_analysis = delivered_items.merge(
    products[
        ["product_id", "product_category_name"]
    ],
    on="product_id",
    how="left"
)


# Translate Portuguese category names to English
product_analysis = product_analysis.merge(
    category_translation,
    on="product_category_name",
    how="left"
)


# Use English category name where available
product_analysis["category"] = (
    product_analysis["product_category_name_english"]
    .fillna(product_analysis["product_category_name"])
)


# ------------------------------------------------------------
# Top 10 categories by GMV
# ------------------------------------------------------------

category_gmv = (
    product_analysis
    .groupby("category", as_index=False)["price"]
    .sum()
    .rename(columns={"price": "GMV"})
    .sort_values("GMV", ascending=False)
    .head(10)
)


# ------------------------------------------------------------
# Top 10 categories by number of orders
# ------------------------------------------------------------

category_orders = (
    product_analysis
    .groupby("category")["order_id"]
    .nunique()
    .reset_index(name="order_count")
    .sort_values("order_count", ascending=False)
    .head(10)
)


product_left, product_right = st.columns(2)


# ------------------------------------------------------------
# GMV chart
# ------------------------------------------------------------

with product_left:

    st.subheader("Top 10 Categories by GMV")

    category_gmv_chart = (
        alt.Chart(category_gmv)
        .mark_bar(color="#7C3AED")
        .encode(
            x=alt.X(
                "GMV:Q",
                title="GMV (R$)"
            ),
            y=alt.Y(
                "category:N",
                title="Product Category",
                sort="-x"
            ),
            tooltip=[
                alt.Tooltip(
                    "category:N",
                    title="Category"
                ),
                alt.Tooltip(
                    "GMV:Q",
                    title="GMV",
                    format=",.2f"
                )
            ]
        )
        .properties(
            height=400
        )
    )

    st.altair_chart(
        category_gmv_chart,
        use_container_width=True
    )


# ------------------------------------------------------------
# Orders chart
# ------------------------------------------------------------

with product_right:

    st.subheader("Top 10 Categories by Orders")

    category_orders_chart = (
        alt.Chart(category_orders)
        .mark_bar(color="#7C3AED")
        .encode(
            x=alt.X(
                "order_count:Q",
                title="Number of Orders"
            ),
            y=alt.Y(
                "category:N",
                title="Product Category",
                sort="-x"
            ),
            tooltip=[
                alt.Tooltip(
                    "category:N",
                    title="Category"
                ),
                alt.Tooltip(
                    "order_count:Q",
                    title="Orders",
                    format=","
                )
            ]
        )
        .properties(
            height=400
        )
    )

    st.altair_chart(
        category_orders_chart,
        use_container_width=True
    )

# ------------------------------------------------------------
# Operations Analysis
# ------------------------------------------------------------

st.header("Operations Analysis")


# Convert delivery-related columns to datetime
delivery_analysis = delivered_orders.copy()

delivery_analysis["order_delivered_customer_date"] = pd.to_datetime(
    delivery_analysis["order_delivered_customer_date"]
)

delivery_analysis["order_estimated_delivery_date"] = pd.to_datetime(
    delivery_analysis["order_estimated_delivery_date"]
)


# ------------------------------------------------------------
# Delivery time
# ------------------------------------------------------------

delivery_analysis["delivery_days"] = (
    delivery_analysis["order_delivered_customer_date"]
    - delivery_analysis["order_purchase_timestamp"]
).dt.days


# Remove invalid values if any
delivery_analysis = delivery_analysis[
    delivery_analysis["delivery_days"] >= 0
].copy()


average_delivery_days = (
    delivery_analysis["delivery_days"].mean()
)


# ------------------------------------------------------------
# Late delivery
# ------------------------------------------------------------

delivery_analysis["is_late"] = (
    delivery_analysis["order_delivered_customer_date"]
    > delivery_analysis["order_estimated_delivery_date"]
)

late_delivery_rate = (
    delivery_analysis["is_late"].mean() * 100
)


# ------------------------------------------------------------
# Operational KPI cards
# ------------------------------------------------------------

ops_col1, ops_col2 = st.columns(2)

ops_col1.metric(
    "Average Delivery Time",
    f"{average_delivery_days:.1f} days"
)

ops_col2.metric(
    "Late Delivery Rate",
    f"{late_delivery_rate:.2f}%"
)


# ------------------------------------------------------------
# Monthly delivery time trend
# ------------------------------------------------------------

delivery_analysis["month"] = (
    delivery_analysis["order_purchase_timestamp"]
    .dt.to_period("M")
    .dt.to_timestamp()
)

monthly_delivery = (
    delivery_analysis
    .groupby("month", as_index=False)["delivery_days"]
    .mean()
)


delivery_chart = (
    alt.Chart(monthly_delivery)
    .mark_line(
        point={
            "filled": True,
            "size": 80
        },
        color="#F59E0B"
    )
    .encode(
        x=alt.X(
            "month:T",
            title="Month",
            axis=alt.Axis(format="%b %Y")
        ),
        y=alt.Y(
            "delivery_days:Q",
            title="Average Delivery Time (Days)",
            scale=alt.Scale(zero=False)
        ),
        tooltip=[
            alt.Tooltip(
                "month:T",
                title="Month",
                format="%B %Y"
            ),
            alt.Tooltip(
                "delivery_days:Q",
                title="Avg Delivery Days",
                format=".1f"
            )
        ]
    )
    .properties(
        height=350
    )
)

st.subheader("Monthly Average Delivery Time")

st.altair_chart(
    delivery_chart,
    use_container_width=True
)

# ------------------------------------------------------------
# Seller Analysis
# ------------------------------------------------------------

st.header("Seller Analysis")


# ------------------------------------------------------------
# Seller distribution by state
# ------------------------------------------------------------

seller_state_summary = (
    sellers
    .groupby("seller_state")["seller_id"]
    .nunique()
    .reset_index(name="seller_count")
    .sort_values("seller_count", ascending=False)
    .head(10)
)


# ------------------------------------------------------------
# GMV by seller
# ------------------------------------------------------------

seller_gmv = (
    delivered_items
    .groupby("seller_id", as_index=False)["price"]
    .sum()
    .rename(columns={"price": "GMV"})
    .sort_values("GMV", ascending=False)
    .head(10)
    .reset_index(drop=True)
)

seller_gmv["seller_label"] = (
    "Seller " + (seller_gmv.index + 1).astype(str)
)

seller_left, seller_right = st.columns(2)


# ------------------------------------------------------------
# Top seller states
# ------------------------------------------------------------

with seller_left:

    st.subheader("Top 10 Seller States")

    seller_state_chart = (
        alt.Chart(seller_state_summary)
        .mark_bar(
            color="#2563EB"
        )
        .encode(
            x=alt.X(
                "seller_count:Q",
                title="Number of Sellers"
            ),
            y=alt.Y(
                "seller_state:N",
                title="State",
                sort="-x"
            ),
            tooltip=[
                alt.Tooltip(
                    "seller_state:N",
                    title="State"
                ),
                alt.Tooltip(
                    "seller_count:Q",
                    title="Sellers",
                    format=","
                )
            ]
        )
        .properties(
            height=350
        )
    )

    st.altair_chart(
        seller_state_chart,
        use_container_width=True
    )


# ------------------------------------------------------------
# Top sellers by GMV
# ------------------------------------------------------------

with seller_right:

    st.subheader("Top 10 Sellers by GMV")

    seller_gmv_chart = (
        alt.Chart(seller_gmv)
        .mark_bar(
            color="#3B82F6"
        )
        .encode(
            x=alt.X(
                "GMV:Q",
                title="GMV (R$)"
            ),
            y=alt.Y(
                "seller_label:N",
                title="Seller",
                sort="-x"
            ),
            tooltip=[
                alt.Tooltip(
                    "seller_label:N",
                    title="Rank"
                ),
                alt.Tooltip(
                    "seller_id:N",
                    title="Seller ID"
                ),
                alt.Tooltip(
                    "GMV:Q",
                    title="GMV",
                    format=",.2f"
                )
            ]
        )
        .properties(
            height=350
        )
    )

    st.altair_chart(
        seller_gmv_chart,
        use_container_width=True
    )

# ------------------------------------------------------------
# Payment Analysis
# ------------------------------------------------------------

st.header("Payment Analysis")


# Delivered payments only
delivered_payments = payments[
    payments["order_id"].isin(delivered_orders["order_id"])
].copy()


# Payment method summary
payment_method_summary = (
    delivered_payments
    .groupby("payment_type")["payment_value"]
    .sum()
    .reset_index()
    .sort_values("payment_value", ascending=False)
)


# Installment summary
installment_summary = (
    delivered_payments
    .groupby("payment_installments")["order_id"]
    .nunique()
    .reset_index(name="order_count")
    .sort_values("payment_installments")
)


payment_left, payment_right = st.columns(2)


with payment_left:

    st.subheader("Payment Value by Method")

    payment_method_chart = (
        alt.Chart(payment_method_summary)
        .mark_bar(
            color="#EC4899"
        )
        .encode(
            x=alt.X(
                "payment_value:Q",
                title="Payment Value (R$)"
            ),
            y=alt.Y(
                "payment_type:N",
                title="Payment Method",
                sort="-x"
            ),
            tooltip=[
                alt.Tooltip(
                    "payment_type:N",
                    title="Payment Method"
                ),
                alt.Tooltip(
                    "payment_value:Q",
                    title="Payment Value",
                    format=",.2f"
                )
            ]
        )
        .properties(
            height=350
        )
    )

    st.altair_chart(
        payment_method_chart,
        use_container_width=True
    )


with payment_right:

    st.subheader("Orders by Number of Installments")

    installment_chart = (
        alt.Chart(installment_summary)
        .mark_bar(
            color="#DB2777"
        )
        .encode(
            x=alt.X(
                "payment_installments:O",
                title="Number of Installments"
            ),
            y=alt.Y(
                "order_count:Q",
                title="Number of Orders"
            ),
            tooltip=[
                alt.Tooltip(
                    "payment_installments:O",
                    title="Installments"
                ),
                alt.Tooltip(
                    "order_count:Q",
                    title="Orders",
                    format=","
                )
            ]
        )
        .properties(
            height=350
        )
    )

    st.altair_chart(
        installment_chart,
        use_container_width=True
    )