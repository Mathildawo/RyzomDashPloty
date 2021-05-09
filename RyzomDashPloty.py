#coding : utf-8
import plotly_express as px
import dash
import dash_html_components as html
import dash_core_components as dcc
from  dash.dependencies import Input, Output
import dash_table
import pandas as pd

import json
import requests

from datetime import timedelta
from datetime import time
from datetime import datetime

import xml.etree.ElementTree as ET

class season():
    _seasons = ['Printemps','Eté','Automne','Hiver']
    _rank = 0

    def __init__(self, refresh):
        if refresh == True:
            data = requests.get('https://api.ryzom.com/time.php?format=xml')
            root = ET.fromstring(data.text)
            season._rank = int(root.find('season').text)

    def getSeason(self):
        return season._seasons[season._rank]        

class tickConversion():
    _datacycle = list()
    _iNext = 0

    def __init__(self, nbCycle):
        startTime = datetime.now()
        min =int(startTime.strftime("%M")) % 3
        if min > 0:
            startTime = startTime - timedelta(minutes = min)
        cycleTime = timedelta(hours = 0, minutes = 1)
        tickConversion._datacycle = list()
        tickConversion._iNext = 0
        for i in range(0,nbCycle) :
            cycle = startTime.strftime("%H:%M")
            tickConversion._datacycle.append(cycle)
            cycletime = startTime + cycleTime
            startTime = cycletime

    def cycleNext(self):
        cn = tickConversion._datacycle[tickConversion._iNext]
        tickConversion._iNext += 1
        return cn 
    def cycleReset(self):
        tickConversion._iNext = 0
        

class weather():
    _data = dict()
    def __init__(self, refresh):
        if refresh == False:
            return
        response = requests.get('https://api.bmsite.net/atys/weather?cycles=19&offset=0')
        manipstr = response.text
        manipstr = manipstr.replace("cycle", "start",1)
        decoded = json.loads(manipstr)
        continents_set = list()
        heures_set = list()
        valeurs_set = list()
        timeInit = tickConversion((20+1)*3)

        offset = int(decoded.get("start"))
        for key, value in decoded.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key != "terre":
                       continue
                    timeInit.cycleReset()
                    if isinstance(sub_value, dict):
                        for x_key, x_value in sub_value.items():
                            if isinstance(x_value, dict):
                               for xx_key, xx_value in x_value.items():
                                   if xx_key == "cycle":
                                      for i in range(3): 
                                          xx_value = timeInit.cycleNext()
                                          continents_set.append(sub_key)
                                          heures_set.append(xx_value)
                                   elif xx_key == "value":
                                       v = int(float(xx_value) * 10000)
                                       for i in range(3):
                                           valeurs_set.append(v)              

            rslt = {"continents":continents_set}
            rslt.update({"dates":heures_set})
            rslt.update({"cc":valeurs_set})
            weather._data = rslt

    def getData(self):
        return weather._data

def get_CC_libelle(cc):
    #0,1670,3340,5000,6666,8340,10000
    #"Good 16.7%","Good 33.4%","Bad 50%","Bad 66.6%","Worst 83.4%","Worst"
    if cc > 8339:
        cclib = "Worst"
    elif cc > 6660:
        cclib = "Worst"
    elif cc > 4999:
        cclib = "Bad"
    elif cc > 3339:
        cclib = "Bad"
    elif cc > 1666:
        cclib = "Good"
    else:
        cclib = "Best"
    return cclib

content_string = "./data/Ryzom_Table_MP_CC.csv"
df_global = pd.read_csv(content_string,sep=';')
df_global_saison = '*'
df_global_cc = 'Good'

colors = {
    'background': '#111111',
    'text': '#7FDBFF'
}

external_stylesheets = ['https://api.ryzom.com/data/css/ryzom_ui.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.Div([
        html.H4('Ryzom météo (raffraichi toutes les 3mn)'),
        html.Div(id='live-update-text'),
        html.H4('Liste des CC par continent (3mn irl = 1h Atys)'),
        html.Div(
            [dash_table.DataTable(
            id='table_mp',
            data=df_global.to_dict('records'),
            filter_action='native',
            style_header={'backgroundColor': 'rgb(192, 192, 192)','color': 'black','text-align': 'center','fontWeight': 'bold'},
            style_cell={'backgroundColor': 'rgb(50, 50, 50)','color': 'white', 'textAlign': 'left'},
            style_data={'width': '150px', 'minWidth': '150px', 'maxWidth': '150px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'},
            #indice	Saison	Continent	pays	cc	TauxMini	TauxMaxi	MP	Excel	Supreme
            columns=[
            {'name': 'Saison',      'id': 'Saison',     'type': 'text'},
            {'name': 'Continent',   'id': 'Continent',  'type': 'text'},
            {'name': 'Pays',        'id': 'pays',       'type': 'text'},
            {'name': 'CC',          'id': 'cc',         'type': 'text'},
            {'name': 'MP',          'id': 'MP',         'type': 'text'},
            {'name': 'Excel',       'id': 'Excel',      'type': 'text'},
            {'name': 'Supreme',     'id': 'Supreme',    'type': 'text'}])]),
            
        dcc.Graph(id='live-update-graph', figure={}),
        dcc.Interval(id='graph-update', interval= 60 * 1000, n_intervals=0),
        dcc.Interval(id='table-update', interval= 60 * 1000, n_intervals=0)
    ])
],                 
    style={'backgroundColor': colors['background'], 'color': colors['text']}
)

@app.callback(Output('live-update-graph','figure'),[Input('graph-update', 'n_intervals')])
def update_graph_live(n):
    global df_global_saison
    global df_global_cc

    if (n % 15 == 0):
        ryzom = weather(True)
        saison = season(True)
    else:
        saison = season(False)
        ryzom = weather(False)
    df_global_saison = saison.getSeason()
    df = pd.DataFrame(ryzom.getData())
    df_dates = df.loc[df['dates']==datetime.now().strftime("%H:%M"),:]
    df_global_cc = get_CC_libelle(df_dates.iloc[0,2])
    fig = px.line (df,x = "dates", y = "cc" ,color = "continents",  title= "Saison : " + saison.getSeason())
    fig.update_yaxes(tickmode = "array",tickvals = [0,1670,3340,5000,6666,8340,10000],ticktext = ["Best", "Good 16.7%","Good 33.4%","Bad 50%","Bad 66.6%","Worst 83.4%","Worst"],showgrid = True)
    fig.update_xaxes(tickmode = "linear",showline = True,showgrid = True, dtick = 3)
    fig.update_layout(legend_uirevision='true')
    fig.add_vline(x=datetime.now().strftime("%H:%M"), line_width=1, line_dash="dash", line_color="red")
    fig.update_xaxes(showline=True, linewidth=2, linecolor='black', gridcolor='rgba(211, 211, 211, 0.75)')
    #fig.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)','paper_bgcolor': 'rgba(0, 0, 0, 0)'})
    #fig.update_yaxes(showline=True, linewidth=2, linecolor='black', gridcolor='grey')
    return fig


@app.callback(Output('table_mp','data'),[Input('table-update', 'n_intervals')])
def update_table_live(n):
    global df_global_saison
    global df_global_cc
    global df_global

    if df_global_saison == '*':
        filtered_df = df_global
    else:
        filtered_df = df_global.query("Saison == '" + df_global_saison + "' and cc == '" + df_global_cc + "'") 
    return filtered_df.to_dict('records')

app.run_server (debug = True)


