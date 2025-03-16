import streamlit as st
import pandas as pd
import plotly.express as px
from utils.sparql_util import (
    init_fuseki_connection,
    execute_query,
    get_country_options,
    get_available_years,
    get_trade_data
)
from utils.format_util import format_number, calculate_yoy_change, calculate_change, format_change
from utils.viz_util import display_trade_metrics, display_trade_trends
from Home import FEATURED_ORG_IDS

# set page config
st.set_page_config(
    page_title="Country Analysis - Trade Data Explorer",
    page_icon="🌍",
    layout="wide"
)

# initialize Fuseki connection
sparql = init_fuseki_connection()


# show country selector in sidebar
def show_country_selector(sparql):
    st.sidebar.title("Country Selection")
    country_options = get_country_options(sparql)

    search_term = st.sidebar.text_input("Search by Country Name or ISO Code", "").strip().upper()

    if search_term:
        filtered_options = [
            opt for opt in country_options
            if search_term in opt[0].upper() or search_term in opt[1].upper()
        ]
    else:
        filtered_options = country_options

    if filtered_options:
        selected_display = st.sidebar.selectbox(
            "Select Country",
            options=[opt[0] for opt in filtered_options],
            key="country_selector"  # add key for rendering
        )

        selected_info = next(opt for opt in filtered_options if opt[0] == selected_display)
        st.session_state.selected_iso = selected_info[1]
        st.session_state.selected_country = selected_info[2]

        # about section
        st.sidebar.divider()
        st.sidebar.subheader("Navigation")
        st.sidebar.page_link("Home.py", label="Home", icon="🏠")
        st.sidebar.page_link("pages/1_Country_Analysis.py", label="Country Analysis", icon="🌎", disabled=True)
        st.sidebar.page_link("pages/2_Organization_Analysis.py", label="Organization Analysis", icon="🏢")
        st.sidebar.page_link("pages/3_Organization_Comparison.py", label="Organization Comparison", icon="📊")

        return selected_info[1], selected_info[2]

    return None, None


# get current trade data for selected country
def get_country_trade_data(sparql, iso_code, year):
    trade_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?year ?totalBalance ?totalExport ?totalImport 
           ?goodsExport ?goodsImport ?servicesExport ?servicesImport
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :hasTradeAggregate ?measurement .
        ?measurement :year ?year ;
                     :totalTradeBalance ?totalBalance ;
                     :totalExportValue ?totalExport ;
                     :totalImportValue ?totalImport ;
                     :goodsExportValue ?goodsExport ;
                     :goodsImportValue ?goodsImport ;
                     :servicesExportValue ?servicesExport ;
                     :servicesImportValue ?servicesImport .
        FILTER(?year IN ({year}, {year - 1}))
    }}
    ORDER BY ?year
    """
    return execute_query(sparql, trade_query)


# get all years of trade data for a country
def get_country_trade_trends(sparql, iso_code):
    trend_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?year ?totalBalance ?totalExport ?totalImport
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :hasTradeAggregate ?measurement .
        ?measurement :year ?year ;
                     :totalTradeBalance ?totalBalance ;
                     :totalExportValue ?totalExport ;
                     :totalImportValue ?totalImport .
    }}
    ORDER BY ?year
    """
    return execute_query(sparql, trend_query)


# display trade overview for selected country and year (show latest first)
def show_trade_overview(sparql, iso_code, country_name, selected_year=None):
    available_years, most_recent_year = get_available_years(sparql, iso_code)

    if not available_years:
        st.warning(f"No trade data available for {country_name}")
        return

    # if no year is selected, use the most recent year
    if selected_year is None:
        selected_year = most_recent_year

    # show year selector with most recent year as default
    selected_year = st.selectbox(
        "Select Year",
        available_years,
        index=available_years.index(selected_year),
        key="year_selector"
    )

    # get data for current and previous year
    trade_results = get_country_trade_data(sparql, iso_code, selected_year)

    if not trade_results:
        st.warning(f"No trade data available for {country_name} in {selected_year}")
        return

    # separate current and previous year data
    if len(trade_results) == 2:
        prev_data = trade_results[0]  # Previous year
        current_data = trade_results[1]  # Current year
    else:
        current_data = trade_results[0]  # Only current year available
        prev_data = None

    # display trade metrics
    display_trade_metrics(current_data, prev_data)

    # get and display trade trends
    trend_data = get_country_trade_trends(sparql, iso_code)
    display_trade_trends(trend_data, country_name)


# trade partner data query
def partners_get_data(sparql, iso_code, time_period="recent"):
    current_year = 2023  # update based on your data availability

    # define year filter based on time period
    if time_period == "recent":
        year_filter = f"FILTER(?year >= {current_year - 2})"
    elif isinstance(time_period, int):
        year_filter = f"FILTER(?year = {time_period})"
    else:  # "all" time
        year_filter = ""

    partners_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?partnerName ?partnerIso ?year
           (SUM(IF(?flowType = "Export", ?tradeValue, 0)) as ?exportValue)
           (SUM(IF(?flowType = "Import", ?tradeValue, 0)) as ?importValue)
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :hasTradeMeasurement ?measurement .
        ?measurement :hasPartnerCountry ?partner ;
                    :year ?year ;
                    :tradeValue ?tradeValue ;
                    :flowType ?flowType .
        ?partner :name ?partnerName ;
                :isoCode ?partnerIso .

        {year_filter}
        FILTER(?partnerIso != "W00")  # Exclude World aggregate
    }}
    GROUP BY ?partnerName ?partnerIso ?year
    ORDER BY DESC(?year)
    """

    return execute_query(sparql, partners_query)


# process data into DataFrame
def partners_process_data(raw_data):
    if not raw_data:
        return None

    # create initial DataFrame
    df = pd.DataFrame([{
        'Partner': r['partnerName']['value'],
        'Partner ISO': r['partnerIso']['value'],
        'Year': int(float(r['year']['value'])),
        'Total Exports': float(r.get('exportValue', {}).get('value', 0)),
        'Total Imports': float(r.get('importValue', {}).get('value', 0))
    } for r in raw_data])

    # aggregate if multiple years exist
    df = df.groupby(['Partner', 'Partner ISO']).agg({
        'Total Exports': 'sum',
        'Total Imports': 'sum'
    }).reset_index()

    # calculate additional metrics
    df['Trade Balance'] = df['Total Exports'] - df['Total Imports']
    df['Total Trade'] = df['Total Exports'] + df['Total Imports']
    df['Export Share'] = (df['Total Exports'] / df['Total Exports'].sum()) * 100
    df['Import Share'] = (df['Total Imports'] / df['Total Imports'].sum()) * 100

    return df


# display trade partners metrics
def partners_display_metrics(df):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Trading Partners", len(df))

        # add total trade volume
        total_trade = df['Total Trade'].sum()
        st.metric("Total Trade Volume", format_number(total_trade))

    with col2:
        st.write("Top Export Markets")
        top_exporters = df.nlargest(3, 'Total Exports')
        for _, row in top_exporters.iterrows():
            st.write(f"{row['Partner']}: {format_number(row['Total Exports'])} ({row['Export Share']:.1f}%)")

    with col3:
        st.write("Top Import Sources")
        top_importers = df.nlargest(3, 'Total Imports')
        for _, row in top_importers.iterrows():
            st.write(f"{row['Partner']}: {format_number(row['Total Imports'])} ({row['Import Share']:.1f}%)")


# create treemap visualization
def partners_create_treemap(df, trade_type="exports"):
    if trade_type.lower() == "exports":
        values = 'Total Exports'
        title = 'Top Export Partners'
    else:
        values = 'Total Imports'
        title = 'Top Import Partners'

    # filter for top 15 partners
    plot_df = df.nlargest(15, values)

    fig = px.treemap(
        plot_df,
        path=['Partner'],
        values=values,
        title=title,
        color='Trade Balance',
        color_continuous_scale=['red', 'white', 'green'],
        color_continuous_midpoint=0
    )

    fig.update_layout(height=500)
    return fig


# add regional concentration analysis
def partners_create_regional_chart(df):
    region_mapping = {
        'Europe': ['ALB', 'AND', 'AUT', 'BLR', 'BEL', 'BIH', 'BGR', 'HRV', 'CZE', 'DNK',
                   'EST', 'FIN', 'FRA', 'DEU', 'GRC', 'HUN', 'ISL', 'IRL', 'ITA', 'LVA',
                   'LIE', 'LTU', 'LUX', 'MLT', 'MDA', 'MCO', 'MNE', 'NLD', 'MKD', 'NOR',
                   'POL', 'PRT', 'ROU', 'RUS', 'SMR', 'SRB', 'SVK', 'SVN', 'ESP', 'SWE',
                   'CHE', 'UKR', 'GBR', 'VAT'],

        'Asia': ['BGD', 'BTN', 'BRN', 'KHM', 'CHN', 'HKG', 'IND', 'IDN', 'JPN',
                 'LAO', 'MAC', 'MYS', 'MDV', 'MNG', 'MMR', 'NPL', 'PHL', 'SGP',
                 'KOR', 'LKA', 'TWN', 'THA', 'VNM'],

        'Middle East': ['ARM', 'AZE', 'BHR', 'CYP', 'GEO', 'IRN', 'IRQ', 'ISR',
                        'JOR', 'KWT', 'LBN', 'OMN', 'PAK', 'PSE', 'QAT', 'SAU',
                        'SYR', 'TUR', 'ARE', 'YEM', 'KAZ', 'KGZ', 'TJK', 'TKM',
                        'UZB'],

        'North America': ['CAN', 'MEX', 'USA'],

        'Central America & Caribbean': ['AIA', 'ATG', 'ABW', 'BHS', 'BRB', 'BLZ', 'BMU',
                                        'VGB', 'CYM', 'CRI', 'CUB', 'CUW', 'DMA', 'DOM',
                                        'SLV', 'GRD', 'GLP', 'GTM', 'HTI', 'HND', 'JAM',
                                        'MTQ', 'MSR', 'NIC', 'PAN', 'PRI', 'BES', 'KNA',
                                        'LCA', 'MAF', 'VCT', 'SXM', 'TTO', 'TCA', 'VIR'],

        'South America': ['ARG', 'BOL', 'BRA', 'CHL', 'COL', 'ECU', 'FLK', 'GUF', 'GUY',
                          'PRY', 'PER', 'SUR', 'URY', 'VEN'],

        'Africa': ['DZA', 'AGO', 'BEN', 'BWA', 'BFA', 'BDI', 'CPV', 'CMR', 'CAF', 'TCD',
                   'COM', 'COG', 'CIV', 'COD', 'DJI', 'EGY', 'GNQ', 'ERI', 'SWZ', 'ETH',
                   'GAB', 'GMB', 'GHA', 'GIN', 'GNB', 'KEN', 'LSO', 'LBR', 'LBY', 'MDG',
                   'MWI', 'MLI', 'MRT', 'MUS', 'MYT', 'MAR', 'MOZ', 'NAM', 'NER', 'NGA',
                   'REU', 'RWA', 'STP', 'SEN', 'SYC', 'SLE', 'SOM', 'ZAF', 'SSD', 'SDN',
                   'TZA', 'TGO', 'TUN', 'UGA', 'ESH', 'ZMB', 'ZWE'],

        'Oceania': ['AUS', 'COK', 'FJI', 'PYF', 'KIR', 'MHL', 'FSM', 'NRU', 'NCL', 'NZL',
                    'NIU', 'NFK', 'MNP', 'PLW', 'PNG', 'PCN', 'WSM', 'SLB', 'TKL', 'TON',
                    'TUV', 'UMI', 'VUT', 'WLF'],

        'Other': []  # default for unmapped countries
    }

    # add region column to DataFrame
    df['Region'] = df['Partner ISO'].map(lambda x: next(
        (region for region, countries in region_mapping.items() if x in countries), 'Other'))

    # create regional aggregation
    region_df = df.groupby('Region').agg({
        'Total Exports': 'sum',
        'Total Imports': 'sum'
    }).reset_index()

    fig = px.bar(
        region_df,
        x='Region',
        y=['Total Exports', 'Total Imports'],
        title='Trade by Region',
        barmode='group'
    )

    return fig


# main function to display trade partner tab
def partners_display_tab(sparql, iso_code, country_name):
    st.header("Trade Partners Analysis")

    # time period selector
    time_options = ["All Time", "Recent (Last 3 Years)", "Single Year"]
    selected_time = st.radio("Select Time Period", time_options, horizontal=True)

    # get available years and most recent year
    available_years, most_recent_year = get_available_years(sparql, iso_code)

    if not available_years:
        st.warning(f"No trade data available for {country_name}")
        return

    # convert selection to query parameter
    if selected_time == "Single Year":
        selected_year = st.selectbox(
            "Select Year",
            available_years,  # from def get_available_years
            key=f"year_select_partners_{iso_code}"  # unique key per country
        )
        time_period = selected_year
    else:
        time_period = "all" if selected_time == "All Time" else "recent"

    # get and process data
    raw_data = partners_get_data(sparql, iso_code, time_period)

    if not raw_data:
        st.warning(f"No trade partner data available for {country_name}")
        return

    # process data
    df = partners_process_data(raw_data)

    if df is None or len(df) == 0:
        st.warning(f"No trade data available for {country_name}")
        return

    # display metrics
    partners_display_metrics(df)

    # create visualization tabs
    viz_tab1, viz_tab2 = st.tabs(["Trade Partners Overview", "Regional Analysis"])

    with viz_tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(partners_create_treemap(df, "exports"), use_container_width=True)
        with col2:
            st.plotly_chart(partners_create_treemap(df, "imports"), use_container_width=True)

    with viz_tab2:
        st.plotly_chart(partners_create_regional_chart(df), use_container_width=True)


# key data for sociodemographic
def get_indicator_data(sparql, iso_code, measurement_type, value_property):
    query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?year ?value
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :{measurement_type} ?measurement .
        ?measurement :year ?year ;
                     :{value_property} ?value .
    }}
    ORDER BY ?year
    """

    results = execute_query(sparql, query)
    if results:
        return pd.DataFrame([
            {
                'Year': int(float(r['year']['value'])),
                'Value': float(r['value']['value'])
            } for r in results
        ])
    return pd.DataFrame()


# show sociodemographic data
def show_sociodemographic(sparql, iso_code, country_name):
    st.header("Sociodemographic Indicators")

    # create columns for key metrics
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    # population Data
    pop_df = get_indicator_data(sparql, iso_code, "hasDemographicMeasurement", "populationValue")
    if not pop_df.empty:
        latest_pop = pop_df.iloc[-1]
        if len(pop_df) >= 2:
            prev_pop = pop_df.iloc[-2]
            pop_change = calculate_change(latest_pop['Value'], prev_pop['Value'])
            pop_change_str, is_positive = format_change(pop_change, 'Population')
        else:
            pop_change_str = "No previous data"
            is_positive = None

        col1.metric(
            f"Population ({int(latest_pop['Year'])})",
            format_number(latest_pop['Value']),
            pop_change_str,
            delta_color="normal"
        )

    # HDI data
    hdi_df = get_indicator_data(sparql, iso_code, "hasSocialMeasurement", "hdiValue")
    if not hdi_df.empty:
        latest_hdi = hdi_df.iloc[-1]
        if len(hdi_df) >= 2:
            prev_hdi = hdi_df.iloc[-2]
            hdi_change = calculate_change(latest_hdi['Value'], prev_hdi['Value'])
            hdi_change_str, is_positive = format_change(hdi_change, 'HDI')
        else:
            hdi_change_str = "No previous data"
            is_positive = None

        col2.metric(
            f"Human Development Index ({int(latest_hdi['Year'])})",
            f"{latest_hdi['Value']:.3f}",
            hdi_change_str,
            delta_color="normal" if is_positive is None else ("normal" if is_positive else "inverse")
        )

    # unemployment data
    unemp_df = get_indicator_data(sparql, iso_code, "hasSocialMeasurement", "unemploymentValue")
    if not unemp_df.empty:
        latest_unemp = unemp_df.iloc[-1]
        if len(unemp_df) >= 2:
            prev_unemp = unemp_df.iloc[-2]
            unemp_change = latest_unemp['Value'] - prev_unemp['Value']  # Use absolute change for unemployment
            unemp_change_str, is_positive = format_change(unemp_change, 'Unemployment')
        else:
            unemp_change_str = "No previous data"
            is_positive = None

        col3.metric(
            f"Unemployment Rate ({int(latest_unemp['Year'])})",
            f"{latest_unemp['Value']:.1f}%",
            unemp_change_str,
            delta_color="normal" if is_positive is None else ("normal" if is_positive else "inverse")
        )

    # Democracy Index data
    dem_df = get_indicator_data(sparql, iso_code, "hasSocialMeasurement", "democracyIndexValue")
    if not dem_df.empty:
        latest_dem = dem_df.iloc[-1]
        if len(dem_df) >= 2:
            prev_dem = dem_df.iloc[-2]
            dem_change = calculate_change(latest_dem['Value'], prev_dem['Value'])
            dem_change_str, is_positive = format_change(dem_change, 'Democracy Index')
        else:
            dem_change_str = "No previous data"
            is_positive = None

        col4.metric(
            f"Democracy Index ({int(latest_dem['Year'])})",
            f"{latest_dem['Value']:.2f}",
            dem_change_str,
            delta_color="normal" if is_positive is None else ("normal" if is_positive else "inverse")
        )

    # create sub-tabs for visualizations only if data exists
    tabs = []
    if not pop_df.empty:
        tabs.append(("Population Trend", pop_df, "Population Count"))
    if not hdi_df.empty:
        tabs.append(("HDI Trend", hdi_df, "HDI Score"))
    if not unemp_df.empty:
        tabs.append(("Unemployment Trend", unemp_df, "Unemployment Rate (%)"))
    if not dem_df.empty:
        tabs.append(("Democracy Index Trend", dem_df, "Democracy Index Score"))

    if tabs:
        tab_list = st.tabs([tab[0] for tab in tabs])

        for i, (title, df, y_label) in enumerate(tabs):
            with tab_list[i]:
                fig = px.line(
                    df,
                    x='Year',
                    y='Value',
                    title=f'{title} - {country_name}'
                )
                fig.update_layout(
                    yaxis_title=y_label,
                    xaxis_title="Year",
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"No sociodemographic data available for {country_name}")


# get country memberships in organizations
def get_country_organizations(sparql, iso_code):
    # primary query pattern that matches the ontology structure
    primary_query = f"""
    PREFIX : <http://example.org/country-data#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?org ?orgName ?extractedId AS ?orgId
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :isMemberOf ?org .

        ?org a :Organization ;
             :name ?orgName .

        OPTIONAL {{ ?org :orgId ?tempOrgId }}

        # Extract id from URI as fallback
        BIND(STRAFTER(STR(?org), "#org_") AS ?uriId)

        # Use available ID or fallback
        BIND(COALESCE(?tempOrgId, ?uriId, "unknown") AS ?extractedId)
    }}
    ORDER BY ?orgName
    """

    results = execute_query(sparql, primary_query)

    # If standard query returns results, use them
    if results and len(results) > 0:
        return results

    # If not, try a more flexible query approach that might match different patterns
    flexible_query = f"""
    PREFIX : <http://example.org/country-data#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?org ?orgName ?idValue AS ?orgId
    WHERE {{
        # Get the country
        ?country :isoCode "{iso_code}" .

        # Try multiple membership patterns
        {{
            # Pattern 1: Standard isMemberOf property
            ?country :isMemberOf ?org .
        }} UNION {{
            # Pattern 2: Maybe a variant property name
            ?country :memberOf ?org .
        }} UNION {{
            # Pattern 3: Inverse relationship
            ?org :hasMember ?country .
        }}

        # Get organization data - require name but make type optional
        ?org :name ?orgName .
        OPTIONAL {{ ?org a :Organization }}

        # Try to get orgId in multiple ways
        OPTIONAL {{ ?org :orgId ?id1 }}
        OPTIONAL {{ ?org :identifier ?id2 }}

        # Extract from URI as fallback
        BIND(STRAFTER(STRAFTER(STR(?org), "country-data#"), "org_") AS ?id3)

        # Use first available ID
        BIND(COALESCE(?id1, ?id2, ?id3, "unknown") AS ?idValue)
    }}
    """

    flexible_results = execute_query(sparql, flexible_query)

    # For debug purposes, if still no results, try a very permissive query to see if any connection exists
    if not flexible_results or len(flexible_results) == 0:
        debug_query = f"""
        PREFIX : <http://example.org/country-data#>

        SELECT ?prop ?org ?orgName
        WHERE {{
            ?country :isoCode "{iso_code}" .
            ?country ?prop ?org .

            # Only select objects that might be organizations
            ?org :name ?orgName .

            # Exclude common non-organization relationships
            FILTER(?prop != :hasNeighbor)
            FILTER(?prop != :hasMeasurement)
            FILTER(?prop != :hasTradeMeasurement)
            FILTER(?prop != :hasTradeAggregate)
            FILTER(?prop != :hasEconomicMeasurement)
            FILTER(?prop != :hasSocialMeasurement)
            FILTER(?prop != :hasDemographicMeasurement)
        }}
        LIMIT 20
        """

        debug_results = execute_query(sparql, debug_query)

        if debug_results and len(debug_results) > 0:
            # Transform the debug results into a structure that matches our expected format
            for result in debug_results:
                if 'orgName' in result and 'org' in result:
                    # Extract org ID from URI if possible
                    uri = result['org']['value']
                    # Add orgId based on the URI
                    if '#' in uri:
                        result['orgId'] = {'value': uri.split('#')[-1]}
                    elif '/' in uri:
                        result['orgId'] = {'value': uri.split('/')[-1]}
                    else:
                        result['orgId'] = {'value': 'unknown'}

            return debug_results

    return flexible_results if flexible_results else []


# organization memberships tab with featured orgs and filterable table
def show_organizations_tab(sparql, iso_code, country_name):
    st.header("Organization Memberships")

    # This is the list of featured organization IDs
    # In production, you would import this from Home.py
    # from Home import FEATURED_ORG_IDS
    featured_org_ids = FEATURED_ORG_IDS

    # Query to get organizations the country is a member of
    org_query = f"""
    PREFIX : <http://example.org/country-data#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?org ?orgName ?orgId ?typeLabel ?memberCount
    WHERE {{
        # Get country's membership in organizations
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :isMemberOf ?org .

        # Get organization basic details
        ?org a :Organization ;
             :name ?orgName .

        # Get organization ID (this is from the URI)
        BIND(STRAFTER(STR(?org), "#org_") AS ?orgId)

        # Get organization type if available
        OPTIONAL {{
            ?org :hasOrgType ?typeEntity .
            ?typeEntity :orgTypeLabel ?typeLabel .
        }}

        # Count members
        {{
            SELECT ?org (COUNT(?member) AS ?memberCount)
            WHERE {{
                ?member a :Country ;
                       :isMemberOf ?org .
            }}
            GROUP BY ?org
        }}
    }}
    ORDER BY ?orgName
    """

    try:
        org_data = execute_query(sparql, org_query)
    except Exception as e:
        st.error(f"Error fetching organization data: {str(e)}")

        # Use simplified query as fallback
        fallback_query = f"""
        PREFIX : <http://example.org/country-data#>

        SELECT ?org ?orgName ?orgId
        WHERE {{
            ?country :isoCode "{iso_code}" ;
                     :isMemberOf ?org .
            ?org :name ?orgName .
            BIND(STRAFTER(STR(?org), "#org_") AS ?orgId)
        }}
        ORDER BY ?orgName
        """

        org_data = execute_query(sparql, fallback_query)

    if not org_data:
        st.warning(f"No organization membership data available for {country_name}")
        return

    # Process the data into a more usable format
    table_data = []
    for org in org_data:
        # Extract basic information
        org_name = org.get('orgName', {}).get('value', 'Unknown')
        org_id = org.get('orgId', {}).get('value', 'unknown')

        # Get organization type, defaulting to "International Organization" if not specified
        org_type = org.get('typeLabel', {}).get('value', 'International Organization')

        # Get member count, defaulting to '?' if not available
        member_count = org.get('memberCount', {}).get('value', '?')
        if member_count != '?':
            try:
                member_count = int(member_count)
            except:
                member_count = '?'

        # Track if this is a featured organization
        is_featured = org_id in featured_org_ids

        table_data.append({
            "Organization": org_name,
            "Type": org_type,
            "Members": member_count,
            "Trade Volume": "N/A",  # Placeholder - can implement actual trade data if needed
            "orgId": org_id,
            "is_featured": is_featured
        })

    # Display total count
    st.subheader(f"{country_name} is a member of {len(table_data)} international organizations")

    # Sort the data - featured orgs first, then alphabetically by name
    table_data.sort(key=lambda x: (not x["is_featured"], x["Organization"]))

    # Create a DataFrame for display
    df = pd.DataFrame(table_data)

    # Add search functionality
    search_term = st.text_input("Search Organizations", "")
    if search_term:
        df = df[df['Organization'].str.contains(search_term, case=False)]

    if not df.empty:
        # Create display dataframe without the metadata columns
        display_df = df[['Organization', 'Type', 'Members', 'Trade Volume']]

        # Display the DataFrame
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        # Add a way to select an organization for more details
        selected_org_name = st.selectbox(
            "Select an organization to view details",
            options=df['Organization'].tolist(),
            key="org_selector"
        )

        # Get the selected organization data
        selected_org = df[df['Organization'] == selected_org_name].iloc[0]

        # Add a button to navigate to the organization analysis page
        if st.button("Analyze Organization", key="analyze_org_btn", use_container_width=True):
            st.session_state.selected_org_id = selected_org['orgId']
            st.session_state.selected_org_name = selected_org['Organization']
            st.page_link("pages/2_Organization_Analysis.py", label="Go to Organization Analysis")
    else:
        st.info("No organizations found matching your search criteria.")


def main():
    # initialize session state for country selection
    if 'selected_iso' not in st.session_state:
        st.session_state.selected_iso = None
    if 'selected_country' not in st.session_state:
        st.session_state.selected_country = None

    # set page title
    st.title("🌎 Country Trade Analysis")

    # get selected country info
    selected_iso, selected_country = show_country_selector(sparql)

    if selected_iso and selected_country:
        # create dynamic header with selected country
        st.header(f"🌍 Trade Data Analysis for {selected_country}")

        # main content area
        tab1, tab2, tab3, tab4 = st.tabs(["Trade Overview", "Trade Partners", "Sociodemographics", "Organizations"])

        with tab1:
            st.header("Trade Overview")
            if st.session_state.selected_iso and st.session_state.selected_country:
                show_trade_overview(sparql,
                                    st.session_state.selected_iso,
                                    st.session_state.selected_country)

        with tab2:
            partners_display_tab(sparql, selected_iso, selected_country)

        with tab3:
            show_sociodemographic(sparql, selected_iso, selected_country)

        with tab4:
            show_organizations_tab(sparql, selected_iso, selected_country)
    else:
        st.info("👈 Please select a country from the sidebar to begin analysis")


if __name__ == "__main__":
    main()