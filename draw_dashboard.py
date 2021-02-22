import dash
import dash_html_components as html
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import n_colors
import numpy as np
import dash_core_components as dcc
import plotly.express as px
import datetime



class input_file:
    """Класс - загрузчик данных
    """
    def __init__(self, path_output, path_input, path_output_additional):
        """
        Args:
            path_output (str): Путь к Файлу с вохдными данными по задаче
            path_input (str): Путь к файлу решению в формате, предложенном организаторами
            path_output_additional (str): Путь к файлу с дополнительными данными по решению 
        """        
        self.personal_rest = pd.read_excel(path_output, sheet_name="personal_rest")
        self.total_rests = pd.read_excel(path_output, sheet_name="total_rests")
        self.qual_deficit = pd.read_excel(path_output, sheet_name="qual_deficit")
        self.working_hours = pd.read_excel(path_output, sheet_name="working_hours")
        self.summary = pd.read_excel(path_output, sheet_name="summary")

        self.PersonalLevel = pd.read_excel(path_input, sheet_name="PersonalLevel ")
        self.params = pd.read_excel(path_input, sheet_name="params", header=None)
        self.RestReq = pd.read_excel(path_input, sheet_name="RestReq ")
        self.rest_table = pd.read_excel(path_output_additional, sheet_name="rest_parts")
    
    def get_personal_rest(self):
        return self.personal_rest
    
    def get_total_rests(self):
        return self.total_rests

    def get_qual_deficit(self):
        return self.qual_deficit

    def get_working_hours(self):
        return self.working_hours

    def get_summary(self):
        return self.summary
    
    def get_RestReq(self):
        return self.RestReq
    
    def get_personal_level(self):
        return self.PersonalLevel
    
    def get_MergedReq(self):

        RestReq = self.get_RestReq()

        PersonalRest = self.get_personal_rest()

        MergedReq = RestReq.merge(PersonalRest, left_on=["worker", "month"], right_on=["Сотрудник",	"Месяц"], how='left')

        MergedReq = MergedReq.fillna(0)

        personal_level = self.get_personal_level()
        
        MergedReq = MergedReq.merge(personal_level, on=['worker'], how='left')

        MAX_PERSONAL_LEVEL = personal_level["PersonalLevel"].max()

        MergedReq['Preority_weight'] = (4 - MergedReq["RestPrior"]) * (MAX_PERSONAL_LEVEL + 1) + MergedReq['PersonalLevel']

        MergedReq.loc[MergedReq["RestReq"] != 0, 'Заявка_сделана'] = 1
        return MergedReq

    def get_rest_table(self):
        return self.rest_table

def create_parameters_table(data, MAIN_COLOUR, HEADER_FONT_SIZE):
    """Функция, создающая fig для целевых параметров

    Args:
        data (input_file): Входные данные

    Returns:
        go.fig: Объект для отображения
    """    
    summary = data.get_summary().drop(columns=['Unnamed: 0'])

    need_hours = summary.sum(axis=1).loc[0]

    working_hours = summary.sum(axis=1).loc[1]

    needed_vacation = data.get_total_rests()

    all_vacation = needed_vacation['Всего часов'].sum()

    not_found_vacation = needed_vacation['Недобор отпусков'].sum()

    MergedReq = data.get_MergedReq()

    req_quant = MergedReq['Заявка'].sum()

    max_req = MergedReq['Заявка_сделана'].sum()

    max_possible_priority = (MergedReq['Preority_weight'] * MergedReq['Заявка_сделана']).sum()

    gotten_priority = (MergedReq['Preority_weight'] * MergedReq['Заявка']).sum()


    res = pd.DataFrame([[' ', ' ', ' ', ' '],
                        [f"{round(100 * (need_hours / working_hours))} %",
                         f"{round(100 * (1 - not_found_vacation / (all_vacation + not_found_vacation)))} %",
                         f"{round(100 * (req_quant / max_req))} %",
                         f"{round(100 * (gotten_priority / max_possible_priority))} %"]
                        ],
                       columns=["Процент удовлетворенной рабочей потребности",
                                "Cредний процент 'отгулянных' часов",
                                "Процент удовлетворенных заявок",
                                "Процент удовлетворенных заявок c учетом рейтинга"])

    fig = go.Figure(data=[go.Table(
                                   header=dict(
                                               values=res.columns,
                                               line_color='white',
                                               fill_color='white',
                                               align='center',
                                               font=dict(color=MAIN_COLOUR,
                                                         size=HEADER_FONT_SIZE + MAIN_PARAMETERS_PLUS)
                                    ),
                                   cells=dict(
                                              values=[res[c] for c in res.columns],
                                              line_color='rgb(255, 255, 255)',
                                              fill_color='rgb(255, 255, 255)',
                                              align='center',
                                              font=dict(color=MAIN_COLOUR,
                                                        size=TABLE_FONT_SIZE + 
                                                             MAIN_PARAMETERS_PLUS + 
                                                             MAIN_PARAMETERS_ADDITIONAL_PLUS),
                                              height=CELL_HEIGHT + 
                                                     MAIN_PARAMETERS_PLUS + 
                                                     MAIN_PARAMETERS_ADDITIONAL_PLUS + 
                                                     40)
                                   )
                          ],
                    layout=dict(title=dict(text='Целевые показатели',
                                           font=dict(color=MAIN_COLOUR,
                                                     size=BIG_HEADER_FONT_SIZE)),
                    height=450))

    return fig


def coloured_table(tab, name, colours_from, colours_to, MAIN_COLOUR, HEADER_FONT_SIZE, BIG_HEADER_FONT_SIZE):
    """Стандартная функция для отображения таблицы с выделением градиента по значениям

    Args:
        tab (pd.DataFrame): Таблица для отображения
        name (str): Title
        colours_from (str, optionsl): Начальный цвет градиента
        colours_to (str, optional): Конечный цвет градиента. Defaults to 'rgb(255, 255, 255)'.

    Returns:
        ОТображаемый объект
    """
    month_names = ['',
                   'Январь',
                   'Февраль',
                   "Март",
                   'Апрель',
                   'Май',
                   "Июнь",
                   'Июль',
                   'Август',
                   "Сентябрь",
                   'Октябрь',
                   'Ноябрь',
                   "Декабрь"]

    min_value = tab.drop(columns='Unnamed: 0').min().min()

    quantity_colours = tab.drop(columns='Unnamed: 0').max().max() - min_value

    if quantity_colours: 
        colors_c = np.array(n_colors(colours_from, colours_to, quantity_colours, colortype='rgb'))
        colors_f = np.array(n_colors(colours_to, colours_from, quantity_colours, colortype='rgb'))
        # Первая колонка всегда белая
        colors_f[0] = 'rgb(255, 255, 255)'
    else:
        # Первая колонка все=гда белая
        colors_c = np.array(['rgb(255, 255, 255)'])
        colors_f = np.array(['rgb(255, 255, 255)'])
        colors_f[0] = 'rgb(255, 255, 255)'

    color_cells = [colors_c[tab[c]-min_value-1] if c != 'Unnamed: 0' else colours_to for c in tab]

    color_fonts = [colors_f[tab[c]-min_value-1] if c != 'Unnamed: 0' else colours_from for c in tab]

    qual_deficit_fig = go.Figure(data=[go.Table(header=dict(
                                                            values=[month_names[c] for c in range(len(tab.columns))],
                                                            line_color='white',
                                                            fill_color='white',
                                                            align='center',
                                                            font=dict(
                                                                      color=MAIN_COLOUR,
                                                                      size=HEADER_FONT_SIZE)
                                                          ),
                                                cells=dict(
                                                           values=[tab[c] for c in tab],
                                                           line_color=color_cells,
                                                           fill_color=color_cells,
                                                           align='center',
                                                           font=dict(
                                                                     color=color_fonts,
                                                                     size=TABLE_FONT_SIZE
                                                                    ),
                                                           height=CELL_HEIGHT
                                                            )
                                                )
                                       ],
                                 layout=dict(
                                             title=dict(
                                                        text=name,
                                                        font=dict(
                                                                  color=MAIN_COLOUR,
                                                                  size=BIG_HEADER_FONT_SIZE)),
                                             height=500)
                                 )

    return qual_deficit_fig


def get_priority_graph(data, name, bins_num, MAIN_COLOUR, BIG_HEADER_FONT_SIZE):
    """Функция, выдающая диаграммы приоритетов

    Args:
        data (input_file): Данные
        name (str): Отображаемое имя
        bins_num (int, optional): Количество бинов
    """
    MergedReq = data.get_MergedReq()
    
    data_hist = MergedReq[MergedReq["Заявка_сделана"] == 1]

    fig = go.Figure(data=[                       
                          go.Histogram(
                                       x=data_hist['Preority_weight'][data_hist['Заявка'] == 1],
                                       name='Выполненые пожелания',
                                       nbinsx=bins_num,
                                       marker_color=MAIN_COLOUR
                                       ),  
                         go.Histogram(
                                       x=data_hist['Preority_weight'][data_hist['Заявка'] == 0],
                                       name='Невыполненные пожелания',
                                       nbinsx=bins_num,
                                       marker_color=MAIN_COLOUR2
                                    )
                         ],
                    layout=dict(
                                title=dict(
                                           text=name,
                                           font=dict(
                                                     color=MAIN_COLOUR,
                                                     size=BIG_HEADER_FONT_SIZE
                                                    )
                                          ),
                                barmode='group',
                                plot_bgcolor='rgb(255,255,255)',
                                height=500,
                                xaxis=dict(
                                           color=MAIN_COLOUR
                                           ),
                                yaxis = dict(
                                             color=MAIN_COLOUR
                                             )
                                )
                    )
    return fig

def histogram_rest_hours(data, name, bins_num, MAIN_COLOUR, BIG_HEADER_FONT_SIZE):
    """Гистограмма годовых отпусков

    Args:
        data (input_file): Данные
        name (str): Отображаемое название
        bins_num (int, optional): Количество бинов

    """    
    total_rests = data.get_total_rests()

    fig = go.Figure(data=[go.Histogram(
                                        x=total_rests['Всего часов'],
                                        name='Часы в отпуске',
                                        nbinsx=bins_num,
                                        marker_color=MAIN_COLOUR)
                          ],
                    layout=dict(
                                title=dict(
                                           text=name,
                                           font=dict(
                                                       color=MAIN_COLOUR,
                                                       size=BIG_HEADER_FONT_SIZE)
                                            ),
                                barmode='overlay',
                                plot_bgcolor='rgb(255,255,255)',
                                xaxis=dict(color=MAIN_COLOUR),
                                yaxis=dict(color=MAIN_COLOUR),
                                height=500)
                    )
    return fig


def calculate_date_for_gantt(month, maxfly, rest_hours, start_bool, year=2021):
    """Оценка дат на основе часов
    Args:
        month (int): месяц
        maxfly (int): Количество часов в месясце
        rest_hours (int): Количество часов отдыха
        start_bool (int): Месяц начала
        year (int, optional): Год

    Returns:
        timedate: дата
    """
    if start_bool:
        day = 28 - round((rest_hours / maxfly) * 27) 
    else:
        day = round((rest_hours / maxfly) * 27) + 1
    out_date = datetime.date(year, month, day)

    if rest_hours == 0:
        if month == 1:
            out_date = out_date - datetime.timedelta(days=1) + datetime.timedelta(days=365)
        else:
            out_date = out_date - datetime.timedelta(days=1)
    return out_date


def get_gantt_for_one_data(rest_table_merged, guy=11835):
    """ПОдготовка примеров расписания

    Args:
        rest_table_merged (pd.DataFrame): Данные
        guy (int, optional): Работник. Defaults to 11835.
    """    
    cycled_indexes1 = {i: i - 1 if i != 1 else 12 for i in range(1, 13)}
    cycled_indexes2 = {i: i + 1 if i != 12 else 1 for i in range(1, 13)}

    filtered = rest_table_merged[rest_table_merged['worker'] == guy]

    filtered1 = filtered[['worker', 'month', "iRestHoursP1", 'MaxFly']]

    filtered2 = filtered[['worker', 'month', "iRestHoursP2"]]
    filtered2["month"] = filtered2["month"].map(cycled_indexes1)

    merged = filtered1.merge(filtered2, on=['worker', 'month'])

    merged = merged[merged["iRestHoursP1"] != 0]

    merged["date_start"] = merged.apply(lambda x: calculate_date_for_gantt(x['month'],
                                                                           x['MaxFly'],
                                                                           x["iRestHoursP1"],
                                                                           True), axis=1)
    merged["date_finish"] = merged.apply(lambda x: calculate_date_for_gantt(cycled_indexes2[x['month']],
                                                                            x['MaxFly'],
                                                                            x["iRestHoursP2"],
                                                                            False), axis=1)

    merged['worker'] = merged['worker'].astype('str')

    return merged


def get_gantt_fig(data, name, guys, MAIN_COLOUR, BIG_HEADER_FONT_SIZE):

    rest_table = data.get_rest_table()
    personal_level = data.get_personal_level()
    rest_table_merged = rest_table.merge(personal_level, on='worker')

    merged = pd.DataFrame(columns=["worker", "date_start", "date_finish"])

    for guy in guys:
        additional_data = get_gantt_for_one_data(rest_table_merged, guy)
        if additional_data.shape[0]:
            merged = merged.append(additional_data, ignore_index=True)

    fig = px.timeline(merged,
                      x_start="date_start",
                      x_end="date_finish",
                      y="worker",
                      color="worker",
                      color_discrete_map={str(guy): MAIN_COLOUR for guy in guys},
                      range_x=[datetime.date(YEAR, 1, 1), datetime.date(YEAR, 12, 31)])

    fig.update_layout(dict(
                            title=dict(text=name,
                                       font=dict(
                                                 color=MAIN_COLOUR,
                                                 size=BIG_HEADER_FONT_SIZE)
                                        ),
                            xaxis=dict(
                                       tickmode='linear',
                                       dtick='M1',
                                       color=MAIN_COLOUR,
                                       showgrid=True,
                                       gridcolor=MAIN_COLOUR2),
                            yaxis=dict(color=MAIN_COLOUR),
                            plot_bgcolor='rgb(255,255,255)')
                    )
    return fig




if __name__ == '__main__':
    # Initialise the app
    app = dash.Dash(__name__)

    MAIN_COLOUR = 'rgb(156, 60, 56)'
    MAIN_COLOUR2 = n_colors(MAIN_COLOUR, 'rgb(255, 255, 255)', 3, colortype='rgb')[1]

    BIG_HEADER_FONT_SIZE = 30
    HEADER_FONT_SIZE = 18
    TABLE_FONT_SIZE = 14
    CELL_HEIGHT = 28

    MAIN_PARAMETERS_PLUS = 5
    MAIN_PARAMETERS_ADDITIONAL_PLUS = 20

    HISTOGRAM_BINS_NUM = 12
    YEAR = 2021

    GUYS_CODES = [11842, 12230, 12455, 33717, 93898]

    data = input_file("/Users/sergey_kuznetsov/Documents/ramax/data/Выходные данные/output_vacation.xlsx", "/Users/sergey_kuznetsov/Documents/ramax/data/Входные данные/input_vacation.xlsx", "/Users/sergey_kuznetsov/Documents/ramax/data/Выходные данные/output_vacation_additional.xlsx")

    panels = html.Div(className='main',  # Define the row element
                  children=[
                            html.H1('Решение команды NO CONSTRAINTS',
                                    style=dict(textAlign='center',
                                    color=MAIN_COLOUR,
                                    size=BIG_HEADER_FONT_SIZE + 40)),

                            dcc.Graph(id='Целевые показатели',
                                      config={'displayModeBar': False},
                                      animate=True,
                                      figure=create_parameters_table(data, MAIN_COLOUR, HEADER_FONT_SIZE)),

                            dcc.Graph(id='Количество рабочих часов',
                                      config={'displayModeBar': False},
                                      animate=True,
                                      figure=coloured_table(data.get_working_hours(), 'Количество рабочих часов', MAIN_COLOUR, 'rgb(255, 255, 255)', MAIN_COLOUR, HEADER_FONT_SIZE, BIG_HEADER_FONT_SIZE)),

                            dcc.Graph(id='Дефицит ресурсов',
                                      config={'displayModeBar': False},
                                      animate=True,
                                      figure=coloured_table(data.get_qual_deficit(), 'Дефицит ресурсов', MAIN_COLOUR, 'rgb(255, 255, 255)', MAIN_COLOUR, HEADER_FONT_SIZE, BIG_HEADER_FONT_SIZE)),

                            dcc.Graph(id='Распределение часов отпуска',
                                      config={'displayModeBar': False},
                                      animate=True,
                                      figure=histogram_rest_hours(data, 'Распределение часов отпуска', HISTOGRAM_BINS_NUM, MAIN_COLOUR, BIG_HEADER_FONT_SIZE)),
        
                            dcc.Graph(id='Гистограммы приоритета',
                                      config={'displayModeBar': False},
                                      animate=True,
                                      figure=get_priority_graph(data, "Распределение приоритетов", HISTOGRAM_BINS_NUM, MAIN_COLOUR, BIG_HEADER_FONT_SIZE)),

                            dcc.Graph(id='Гант чарт',
                                      config={'displayModeBar': False},
                                      animate=True,
                                      figure=get_gantt_fig(data, "Примеры графиков", GUYS_CODES, MAIN_COLOUR, BIG_HEADER_FONT_SIZE))
                            ])
    
    app.layout = html.Div(className='row',
                      children=[panels])

    app.run_server(debug=True)