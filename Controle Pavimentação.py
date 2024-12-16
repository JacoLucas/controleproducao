import os
import glob
import pandas as pd
import numpy as np
from dash import Dash, html, dcc, Output, Input
import plotly.express as px

# Função para carregar todos os arquivos de produção
def load_production_files(directory):
    files = glob.glob(os.path.join(directory, "Produção_Diária_Obra_*.xlsx"))
    data = {}
    for file in files:
        obra_id = os.path.basename(file).split('_')[-1].split('.')[0]
        df = pd.read_excel(file)
        df['Dias'] = pd.to_datetime(df['Dias'])
        df['Mes'] = df['Dias'].dt.to_period('M')
        df['Semana'] = df['Dias'].dt.to_period('W')  # Ajustar semanas para 1 a 4 dentro de cada mês
        df['Obra'] = f'Obra {obra_id}'  # Adicionar coluna para identificar a obra
        data[obra_id] = df
    return data

# Carregar os arquivos de produção da pasta especificada
production_data = load_production_files("C:/Users/ljaco/Documents/0-Planejamento_e_Custos/")

app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Produção Obras de Pavimentação"),
    html.Div([
        dcc.Dropdown(
            id='atividade-dropdown',
            options=[{'label': f'Atividade {i}', 'value': f'prod diaria {i}'} for i in range(1, 6)] + [{'label': 'Todas as Atividades', 'value': 'todas'}],
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
    Output('mes-dropdown', 'options'),
    Input('obra-dropdown', 'value')
)
def update_mes_dropdown(selected_obra):
    if selected_obra == 'todas':
        combined_df = pd.concat(production_data.values())
        meses = [{'label': str(mes), 'value': str(mes)} for mes in combined_df['Mes'].unique()]
    else:
        df = production_data[selected_obra]
        meses = [{'label': str(mes), 'value': str(mes)} for mes in df['Mes'].unique()]
    return meses

@app.callback(
    Output('semana-dropdown', 'options'),
    [Input('obra-dropdown', 'value'),
     Input('mes-dropdown', 'value')]
)
def update_semana_dropdown(selected_obra, selected_mes):
    if selected_obra == 'todas':
        combined_df = pd.concat(production_data.values())
    else:
        combined_df = production_data[selected_obra]

    filtered_df = combined_df[combined_df['Mes'].astype(str) == selected_mes]
    semanas = [{'label': 'Todas as Semanas', 'value': 'todas'}] + [{'label': str(semana), 'value': str(semana)} for semana in filtered_df['Semana'].unique()]
    return semanas

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
        filtered_data = pd.concat(production_data.values())
    else:
        filtered_data = production_data[selected_obra]
    
    # Filtrar dados pelo mês selecionado
    filtered_df = filtered_data[filtered_data['Mes'].astype(str) == selected_mes]

    # Filtrar dados pela semana selecionada
    if selected_semana != 'todas':
        filtered_df = filtered_df[filtered_df['Semana'] == selected_semana]

    # Gráfico de linhas de produção diária por dias para cada atividade
    if selected_atividade == 'todas':
        prod_diaria_data = filtered_df.melt(id_vars=['Dias', 'Mes', 'Obra'], value_vars=[f'prod diaria {i}' for i in range(1, 6)],
                                            var_name='Atividade', value_name='Produção Diária')
    else:
        prod_diaria_data = filtered_df.melt(id_vars=['Dias', 'Mes', 'Obra'], value_vars=[selected_atividade],
                                            var_name='Atividade', value_name='Produção Diária')
    
    # Adicionar coluna combinada para diferenciar por Obra e Atividade
    if selected_obra == 'todas':
        prod_diaria_data['Obra_Atividade'] = prod_diaria_data['Obra'] + ' - ' + prod_diaria_data['Atividade']
    else:
        prod_diaria_data['Obra_Atividade'] = prod_diaria_data['Atividade']

    fig_prod_diaria = px.line(
        prod_diaria_data, x='Dias', y='Produção Diária', color='Obra_Atividade', line_group='Obra',
        title='Produção Diária por Atividade e Obra', markers=True,
        hover_data={"Obra": False, "Dias": False, "Obra_Atividade": False}  # Esconder colunas indesejadas no tooltip
    )
    fig_prod_diaria.update_traces(connectgaps=False)  # Esta linha impede que as linhas conectem pontos faltantes

    # Preparar dados para gráfico comparativo
    comparacao_cols = [f'prod acum {i}' for i in range(1, 6)] + [f'prev acum {i}' for i in range(1, 6)]

    if selected_obra == 'todas':
        combined_summary = pd.concat([df.groupby('Mes').last().reset_index() for df in production_data.values()])
    else:
        combined_summary = production_data[selected_obra].groupby('Mes').last().reset_index()

    summary_df = combined_summary[combined_summary['Mes'] == selected_mes]
    melted_comparacao = summary_df.melt(id_vars=['Mes'], value_vars=comparacao_cols, 
                                        var_name='Tipo', value_name='Produção')
    melted_comparacao['Atividade'] = melted_comparacao['Tipo'].apply(lambda x: x.split()[2])
    melted_comparacao['Tipo'] = melted_comparacao['Tipo'].apply(lambda x: 'Realizado Acumulada' if 'prod' in x else 'Produção Prevista')

    fig_comparativo = px.bar(
        melted_comparacao, x='Atividade', y='Produção', color='Tipo', barmode='group',
        title='Comparação de Produção Acumulada vs. Prevista'
    )

    return fig_prod_diaria, fig_comparativo

if __name__ == '__main__':
    app.run_server(debug=True)
