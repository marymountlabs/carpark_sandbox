import streamlit as st
import json
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt
from calendar import monthrange

st.set_page_config(
    page_title="Carpark Dashboard",
    page_icon="🚗",
    layout="wide"
)

st.write("# 🚗 HDB Car Park Dashboard")
st.write("Car park data extracted for August 2022")

# preload data
# test out experimental caches here?
carpark_info = gpd.read_file('cp_info.geojson')
f = open('aug_compressed.json')
august_cp = json.load(f)

col1, space, col2 = st.columns([1,0.1,1])
with col1:
    date = st.date_input('Select a date', dt.date(2022,8,1), min_value=dt.date(2022,8,1), max_value=dt.date(2022,8,31))
    hour = st.slider('Select an hour', 6, 23, 6, format="%d:00")
with col2:
    all_pln = st.checkbox('Islandwide visualisation')
    if all_pln:
        cp_filter = carpark_info
    else:
        pln_area = st.multiselect('Select planning area', list(set(carpark_info.planning_area)))
        cp_filter = carpark_info[carpark_info.planning_area.isin(pln_area)]

occupancy_filter = august_cp['{:02d}-{:02d}'.format(date.month,date.day)]["{:02d}".format(hour)]
df = pd.merge(cp_filter,pd.DataFrame(occupancy_filter),left_on="car_park_no", right_on='n')

# to ensure all data frames have total lots
if hour != 6:
    get_lots = august_cp['{:02d}-{:02d}'.format(date.month, date.day)]['06']
    df = pd.merge(df,pd.DataFrame(get_lots)[['n','t']],left_on="car_park_no", right_on='n')

fig = go.Figure()

fig.add_trace(go.Scattermapbox(
        lat=df.geometry.y,
        lon=df.geometry.x,
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=8,
            color=df.o,
            opacity=0.7,
            reversescale=True,
            showscale=True,
            colorscale="YlOrRd"
        ),
        text=[df.car_park_no[i] + '<br>' +
              "Total Lots: {}".format(str(df.t[i])) + '<br>' +
              "Availability: {}%".format(str(df.o[i])) for i in range(len(df))],
        hoverinfo='text'
    ))

fig.update_layout(
    title='Carpark Availability',
    autosize=True,
    hovermode='closest',
    showlegend=False,
    height=750,
    mapbox=dict(
        accesstoken=st.secrets["mapbox_access_token"],
        bearing=0,
        center=dict(
            lat=1.3521,
            lon=103.8198
        ),
        pitch=0,
        zoom=10,
        style='dark'
    ),
)

st.plotly_chart(fig, use_container_width=True)
