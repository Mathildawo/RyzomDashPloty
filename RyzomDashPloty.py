import plotly_express as px
import dash
import dash_html_components as html
import dash_core_components as dcc
from  dash.dependencies import Input, Output
import pandas as pd

import json
import requests

from datetime import timedelta
from datetime import time
from datetime import datetime

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
    def __init__(self):
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
                                       v = int(float(xx_value) * 100)
                                       for i in range(3):
                                           valeurs_set.append(v)              

            rslt = {"continents":continents_set}
            rslt.update({"dates":heures_set})
            rslt.update({"cc":valeurs_set})
            weather._data = rslt

    def getData(self):
        return weather._data


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
        dcc.Graph(id='live-update-graph', figure={}),
        dcc.Interval(
            id='graph-update',
            interval= 45 * 1000,  # in milliseconds
            n_intervals=0,
        )
    ])
],                 
    style={'backgroundColor': colors['background'], 'color': colors['text']}
)

@app.callback(Output('live-update-graph', 'figure'),[Input('graph-update', 'n_intervals')])

def update_graph_live(input_data):
    ryzom = weather()
    df = pd.DataFrame(ryzom.getData())
    fig = px.line (df,x = "dates", y = "cc" ,color = "continents")
    fig.update_yaxes(tickmode = "array",tickvals = [0,16,33,50,66,82,100],ticktext = ["Best", "Good 16%","Good 33%","Bad 50%","Bad 66%","Worst 82%","Worst 100%"],showgrid = True)
    fig.update_xaxes(tickmode = "linear",showline = True,showgrid = True, dtick = 3)
    fig.update_layout(legend_uirevision='true')
    print ('callback : ', input_data)
    return fig

app.run_server (debug = True)


