import streamlit as st
import json
import pandas as pd
import geopandas as gpd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime as dt

st.set_page_config(
    page_title="Analysis",
    page_icon="📈",
    layout="wide"
)

st.write("# 📈 Car Park Analysis")

carpark_info = gpd.read_file('cp_info.geojson')
ts = json.load(open('ts.json'))
dow = json.load(open('dow.json'))
town_stats = json.load(open('town_stats.json'))
cluster_df = pd.read_csv('final_clusters.csv', index_col=0)
cluster_attr = pd.read_csv('cluster_attr.csv', index_col=0)
with open('all_clusters.npy', 'rb') as f:
    cc = np.load(f)

type = st.radio('Type of analysis', ['Car Park Availability', 'Clustering Analysis', 'Town-Level Analysis'])

if type == 'Car Park Availability':
    col1, space, col2 = st.columns([0.6, 0.05, 1])
    with col1:
        pln_area = st.selectbox('Select planning area', list(set(carpark_info.planning_area)))
        filter_json = dow[pln_area]
        analysis_cp = st.selectbox('Select car park for analysis', list(filter_json.keys()))

        df = pd.DataFrame(filter_json[analysis_cp])[['0','1','2','3','4','5','6']].stack().reset_index()
        df.columns = ['hour','dow','availability']
        dow_dict = {'0': 'Monday', '1': 'Tuesday', '2': 'Wednesday', '3': 'Thursday', '4': 'Friday', '5': 'Saturday', '6': 'Sunday'}
        df.replace({'dow': dow_dict}, inplace=True)

        all_dow  = st.checkbox('Select all days')
        if all_dow:
            dow_select = st.multiselect('Select day of week', ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'],
                                        default = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
        else:
            dow_select = st.multiselect('Select day of week', ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                                        default = 'Monday')
        df_filter = df[df.dow.isin(list(dow_select))]
        df_filter['hour'] = df_filter['hour'].apply(lambda x: "{:02d}:00".format(x+6))
        df_filter['availability'] = df_filter['availability'].apply(lambda x: round(x, 2))

    with col2:
        fig = go.Figure()

        lat = carpark_info[carpark_info.car_park_no == analysis_cp].geometry.y.iloc[0]
        lon = carpark_info[carpark_info.car_park_no == analysis_cp].geometry.x.iloc[0]

        fig.add_trace(go.Scattermapbox(
                lat=carpark_info.geometry.y, lon=carpark_info.geometry.x, mode='markers',
                marker=dict(symbol='car', size=20),
                text=carpark_info.car_park_no,
                hoverinfo='text'
            ))

        fig.update_layout(
            autosize=True,
            hovermode='closest',
            showlegend=False,
            height=400,
            margin=dict(l=0, r=0, t=0, b=0),
            mapbox=dict(
                accesstoken=st.secrets["mapbox_access_token"],
                bearing=0,
                center=dict(lat=lat, lon=lon),
                pitch=0,
                zoom=16,
                style='streets'
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

    try:
        fig = px.line(df_filter, x=df_filter['hour'], y=df_filter['availability'], color=df_filter['dow'])
        fig.update_yaxes(range=[0,100])
        st.plotly_chart(fig, use_container_width=True)

    except:
        st.write('No data available for the select car parks')

if type == 'Clustering Analysis':
    df = pd.merge(carpark_info, cluster_df, left_on="car_park_no", right_on='CAR_PARK_NO')
    df.labels = df.labels.fillna(99).astype(int)

    centroids = pd.DataFrame(columns=range(36))
    for n in range(13):
        centroids = centroids.append(pd.DataFrame([round(i[0], 2) for i in cc[n]]).T)
    centroids = centroids.reset_index(drop=True).T

    col1, col2 = st.columns([0.3, 1])
    with col1:
        st.subheader('Cluster Trends')
        viz_clusters = st.checkbox('Visualise all clusters')
        if viz_clusters:
            viz_nums = list(range(13))
        else:
            viz_nums = st.multiselect('Select clusters to visualise:', list(range(13)), default=0)

    with col2:
        colors = matplotlib.cm.get_cmap('viridis')

        fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=['Weekday Average','Weekend Average'], horizontal_spacing=0.02)

        for i in viz_nums:
            fig.add_trace(go.Scatter(x=["{:02d}:00".format(x+6) for x in range(18)], mode='lines', y=centroids.loc[:18, i],
                                     name='cluster {}'.format(i), line=dict(color='rgba{}'.format(colors(1*i/13)))), row=1, col=1)
            fig.add_trace(go.Scatter(x=["{:02d}:00".format(x+6) for x in range(18)], mode='lines', y=centroids.loc[18:, i],
                                     name='cluster {}'.format(i), line=dict(color='rgba{}'.format(colors(1*i/13)))), row=1, col=2)

        fig.update_yaxes(range=[0, 100])
        fig.update_layout(showlegend=False, xaxis_title='Hour', yaxis_title='Availability')
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns([0.3, 1])
    with col3:
        st.subheader('Map Clusters')
        select_clusters = st.checkbox('Map islandwide clusters')
        if select_clusters:
            select_nums = list(range(13))
        else:
            select_nums = st.multiselect('Select clusters to map:', list(range(13)), default=0)

        cp_count = pd.DataFrame([list(range(13)),[len(df[df.labels==c]) for c in range(13)]]).T
        cp_count.columns = ['Cluster', 'Carpark Count']
        st.write(cp_count[cp_count['Cluster'].isin(select_nums)])

    with col4:
        fig = go.Figure()

        # for l in list(set(df.labels)):
        for l in select_nums:

            fig.add_trace(go.Scattermapbox(
                    name='Cluster {}'.format(l),
                    lat=df[df.labels==l].geometry.y,
                    lon=df[df.labels==l].geometry.x,
                    mode='markers',
                    marker=go.scattermapbox.Marker(size=8, opacity=0.7),
                    text=[df[df.labels==l].car_park_no[i] + '<br>Cluster {}'.format(l) for i in df[df.labels==l].index],
                    hoverinfo='text'
                ))

        fig.update_layout(
            autosize=True,
            hovermode='closest',
            showlegend=True,
            height=750,
            mapbox=dict(
                accesstoken=st.secrets["mapbox_access_token"],
                bearing=0,
                center=dict(lat=1.3521, lon=103.8198),
                pitch=0,
                zoom=10,
                style='dark'
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

if type == 'Town-Level Analysis':
    pln_areas = list(set(carpark_info.planning_area))
    col1, col2 = st.columns(2)
    with col1: pln_area_1 = st.selectbox('Select first planning area', pln_areas)
    with col2: pln_area_2 = st.selectbox('Select second planning area', pln_areas)

    total_cp, total_lots, mscp_lots, surface_lots = [], [], [], []
    for pa in pln_areas:
        total_cp.append(town_stats[pa]['TOTAL_CP'])
        total_lots.append(town_stats[pa]['TOTAL_LOTS'])
        mscp_lots.append(town_stats[pa]['MSCP_LOTS'])
        surface_lots.append(town_stats[pa]['SURFACE_LOTS'])

    compare_df = pd.DataFrame(zip(total_cp, pln_areas, total_lots, mscp_lots, surface_lots),
                              columns=['Car Parks','Planning Area', 'All Lots', 'Multi-Storey Car Park', 'Surface Car Park'])
    compare_df['color'] = ['0' if pa in [pln_area_1, pln_area_2] else '1' for pa in pln_areas]

    # number of car parks
    fig = px.bar(compare_df.sort_values(by='Car Parks'), y='Car Parks', x='Planning Area', color='color', height=400, title='Number of Car Parks')
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # number of car park lots
    cp_lot_type = st.radio('Select type of car park to view', ['All Lots', 'Multi-Storey Car Park', 'Surface Car Park'],
                           horizontal=True)
    fig = px.bar(compare_df.sort_values(by=cp_lot_type), y=cp_lot_type, x='Planning Area', color='color', height=400, title='Number of CP Lots')
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # line chart for weekday and weekend time series
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=['Weekday Average', 'Weekend Average'],
                        horizontal_spacing=0.02)
    colors = matplotlib.cm.get_cmap('viridis')

    for i in range(2):
        pa = [pln_area_1, pln_area_2][i]
        fig.add_trace(go.Scatter(x=["{:02d}:00".format(x + 6) for x in range(18)], mode='lines', y=town_stats[pa]['WD_TS'],
                                 name=pa, line=dict(color='rgba{}'.format(colors(1 * i / 2)))), row=1, col=1)
        fig.add_trace(go.Scatter(x=["{:02d}:00".format(x + 6) for x in range(18)], mode='lines', y=town_stats[pa]['WE_TS'],
                                 name=pa, line=dict(color='rgba{}'.format(colors(1 * i / 2)))), row=1, col=2)

    fig.update_yaxes(range=[0, 100])
    fig.update_layout(showlegend=False, xaxis_title='Hour', yaxis_title='Availability')
    st.plotly_chart(fig, use_container_width=True)
