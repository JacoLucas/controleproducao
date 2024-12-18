import os
import glob
import pandas as pd
import numpy as np
from dash import Dash, html, dcc, Output, Input
import plotly.express as px

def load_production_files():
    directory = os.path.dirname(os.path.abspath(__file__))
    files = glob.glob(os.path.join(directory, "Produção_Diária_Obra_*.xlsx"))
    data = {}
    for file in files:
        obra_id = os.path.basename(file).split('_')[-1].split('.')[0]
        df = pd.read_excel(file)
        df['Dias'] = pd.to_datetime(df['Dias'])
        df['Mes'] = df['Dias'].dt.to_period('M')
        df['Semana'] = df['Dias'].dt.to_period('W')
        df['Obra'] = f'Obra {obra_id}'
        print(f"{file} - {len(df)} linhas")
        data[obra_id] = df
    return data

production_data = load_production_files()

app = Dash(__name__)
server = app.server

activity_labels = {
    'prod diaria 1': 'Corte (m³)',
    'prod diaria 2': 'Aterro (m³)',
    'prod diaria 3': 'Tubos e Aduelas (un)',
    'prod diaria 4': 'Caixas e PVs (un)',
    'prod diaria 5': 'Escavação de Drenagem'
}

app.layout = html.Div([
    html.H1("Acompanhamento da Produdução Diária"),
    html.Div([
        dcc.Dropdown(
            id='atividade-dropdown',
            options=[{'label': label, 'value': key} for key, label in activity_labels.items()] + [{'label': 'Todos os Serviços', 'value': 'todas'}],
            value='todas',
            clearable=False,
            style={'width': '100%'}
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),
    html.Div([
        dcc.Dropdown(
            id='mes-dropdown',
            clearable=False,
            style={'width': '100%'}
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),
    html.Div([
        dcc.Dropdown(
            id='obra-dropdown',
            options=[{'label': f'Obra {obra_id}', 'value': obra_id} for obra_id in production_data.keys()] + [{'label': 'Todas as Obras', 'value': 'todas'}],
            value='todas',
            clearable=False,
            style={'width': '100%'}
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),
    html.Div([
        dcc.Dropdown(
            id='semana-dropdown',
            clearable=False,
            style={'width': '100%'}
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),
    html.Div([
        dcc.Graph(id='grafico-prod-diaria', style={'display': 'inline-block', 'width': '99%'}),
    ]),
    dcc.Graph(id='grafico-comparativo-mensal')
])

@app.callback(
    [Output('mes-dropdown', 'options'),
     Output('semana-dropdown', 'options')],
    [Input('obra-dropdown', 'value'),
     Input('mes-dropdown', 'value')]
)
def update_dropdowns(selected_obra, selected_mes):
    if selected_obra == 'todas':
        combined_df = pd.concat(production_data.values()) if production_data else pd.DataFrame()
    else:
        combined_df = production_data.get(selected_obra, pd.DataFrame())

    if not combined_df.empty and 'Mes' in combined_df.columns:
        meses = [{'label': str(mes), 'value': str(mes)} for mes in combined_df['Mes'].unique()]
    else:
        meses = []

    if not combined_df.empty and 'Mes' in combined_df.columns:
        filtered_df = combined_df[combined_df['Mes'].astype(str) == selected_mes]
        semanas = [{'label': 'Todas as Semanas', 'value': 'todas'}] + [{'label': str(semana), 'value': str(semana)} for semana in filtered_df['Semana'].unique()]
    else:
        semanas = []

    return meses, semanas

@app.callback(
    [Output('grafico-prod-diaria', 'figure'),
     Output('grafico-comparativo-mensal', 'figure')],
    [Input('atividade-dropdown', 'value'),
     Input('obra-dropdown', 'value'),
     Input('mes-dropdown', 'value'),
     Input('semana-dropdown', 'value')]
)
def update_graphs(selected_atividade, selected_obra, selected_mes, selected_semana):
    if selected_obra == 'todas':
        filtered_data = pd.concat(production_data.values()) if production_data else pd.DataFrame()
    else:
        filtered_data = production_data.get(selected_obra, pd.DataFrame())
    
    if filtered_data.empty or 'Mes' not in filtered_data.columns:
        return {}, {}

    filtered_df = filtered_data[filtered_data['Mes'].astype(str) == selected_mes]
    if filtered_df.empty:
        return {}, {}
    
    if selected_semana != 'todas':
        filtered_df = filtered_df[filtered_df['Semana'].astype(str) == selected_semana]
        if filtered_df.empty:
            return {}, {}

    if selected_atividade == 'todas':
        prod_diaria_data = filtered_df.melt(id_vars=['Dias', 'Mes', 'Obra'], value_vars=[key for key in activity_labels.keys()],
                                            var_name='Atividade', value_name='Produção')
    else:
        prod_diaria_data = filtered_df.melt(id_vars=['Dias', 'Mes', 'Obra'], value_vars=[selected_atividade],
                                            var_name='Atividade', value_name='Produção')
    
    prod_diaria_data['Atividade'] = prod_diaria_data['Atividade'].map(activity_labels)

    if selected_obra == 'todas':
        prod_diaria_data['Obra_Serviço'] = prod_diaria_data['Obra'] + ' - ' + prod_diaria_data['Atividade']
    else:
        prod_diaria_data['Obra_Serviço'] = prod_diaria_data['Atividade']

    fig_prod_diaria = px.line(
        prod_diaria_data, x='Dias', y='Produção', color='Obra_Serviço', line_group='Obra',
        title='Produção Diária por Serviço', markers=True,
        hover_data={"Obra": False, "Dias": False, "Obra_Serviço": False}
    )
    fig_prod_diaria.update_traces(connectgaps=True)

    comparacao_cols = {
        'prod acum 1': 'Corte (m³)',
        'prod acum 2': 'Aterro (m³)',
        'prod acum 3': 'Rachão (ton.)',
        'prod acum 4': 'Tubos e Aduelas (un)',
        'prod acum 5': 'Caixas e PVs (un)',
        'prev acum 1': 'Previsto Corte (m³)',
        'prev acum 2': 'Previsto Aterro (m³)',
        'prev acum 3': 'Previsto Rachão (ton.)',
        'prev acum 4': 'Previsto Tubos e Aduelas (un)',
        'prev acum 5': 'Previsto Caixas e PVs (un)'
    }

    if selected_obra == 'todas':
        combined_summary = pd.concat([df.groupby('Mes').last().reset_index() for df in production_data.values()])
    else:
        combined_summary = production_data[selected_obra].groupby('Mes').last().reset_index()

    summary_df = combined_summary[combined_summary['Mes'].astype(str) == selected_mes]
    melted_comparacao = summary_df.melt(id_vars=['Mes'], value_vars=comparacao_cols.keys(), 
                                        var_name='Tipo', value_name='Produção')
    melted_comparacao['Atividade'] = melted_comparacao['Tipo'].map(comparacao_cols)
    melted_comparacao['Serviço'] = melted_comparacao['Tipo'].str.extract(r'(\d+)')[0]
    melted_comparacao['Tipo'] = melted_comparacao['Tipo'].apply(lambda x: x.split()[0])
    
    # Map the Serviço column to actual activity names for comparison
    serviço_labels = {
        '1': 'Corte (m³)',
        '2': 'Aterro (m³)',
        '3': 'Rachão (ton.)',
        '4': 'Tubos e Aduelas (un)',
        '5': 'Caixas e PVs (un)'
    }

    tipo_labels = {
        'prod': 'Realizado',
        'prev': 'Previsto'
    }

    melted_comparacao['Serviço'] = melted_comparacao['Serviço'].map(serviço_labels)
    melted_comparacao['Tipo'] = melted_comparacao['Tipo'].map(tipo_labels)

    fig_comparativo = px.bar(
        melted_comparacao, x='Serviço', y='Produção', color='Tipo', barmode='group',
        title='Comparação de Produção Acumulada',
        hover_data={"Serviço": False}
    )
    fig_comparativo.update_layout(bargroupgap=0.1)  # Ajusta o espaçamento entre os grupos de barras

    return fig_prod_diaria, fig_comparativo

if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8050)))
