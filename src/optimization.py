import pyomo.environ as pyo
from random import randrange
from pyomo.opt import SolverFactory
import pandas as pd

def run_optimization(Qual):
    WORKERS = pd.read_excel (r'C:\Users\rusivr\Documents\GitHub\ramax\input\input_vacation.xlsx', sheet_name = 'PersonalLevel ', index_col = [0]).to_dict('index')
    QUALS = pd.read_excel (r'C:\Users\rusivr\Documents\GitHub\ramax\input\input_vacation.xlsx', sheet_name = 'Qualified ', index_col = [0, 1]).to_dict('index')
    QUALS = { (w, q): QUALS[w, q]['QualFlg'] for w, q in QUALS.keys() if q == Qual and QUALS[w,q]['QualFlg'] == 1}
    MONTHS = pd.read_excel (r'C:\Users\rusivr\Documents\GitHub\ramax\input\input_vacation.xlsx', sheet_name = 'Months', index_col = [0]).to_dict('index')
    REQUIRED = pd.read_excel (r'C:\Users\rusivr\Documents\GitHub\ramax\input\input_vacation.xlsx', sheet_name = 'RequiredPersonal ', index_col = [0, 1]).to_dict('index')
    RestReqPrior = pd.read_excel (r'C:\Users\rusivr\Documents\GitHub\ramax\input\input_vacation.xlsx', sheet_name = 'RestReq ', index_col = [0, 1]).to_dict('index')

    model = pyo.ConcreteModel()

    WORKER_QUALS_KEYS = list(QUALS.keys())
    QUALS_KEYS = list(set([q for (w, q) in WORKER_QUALS_KEYS]))
    WORKERS_KEYS = list(set([w for (w, q) in WORKER_QUALS_KEYS]))
    MONTHS_KEYS = list(MONTHS.keys())

    # print('SIZE OF WORKER_QUALS_KEYS = ', len(WORKER_QUALS_KEYS))
    # print('SIZE OF QUALS_KEYS = ', len(QUALS_KEYS))
    # print('SIZE OF WORKERS_KEYS = ', len(WORKERS_KEYS))
    # print('SIZE OF MONTHS_KEYS = ', len(MONTHS_KEYS))

    # Переменные решения

    # Сколько часов в месяце должен работать конкретный сотрудник с определенной квалификацией
    model.iWorkHours = pyo.Var(MONTHS_KEYS, [(w, q) for (w, q) in WORKER_QUALS_KEYS if QUALS[w,q] == 1], within = pyo.NonNegativeIntegers)

    # Сколько часов в месяце сотрудник находится в отпуске
    def RestHours_bounds(model, m, w):
        return (0, MONTHS[m]['MaxRest'])
    model.iRestHours = pyo.Var(MONTHS_KEYS, WORKERS_KEYS, within=pyo.NonNegativeIntegers, bounds = RestHours_bounds)


    # Индикатор того, что сотрудник уходит в отпуск в этом месяце
    model.zRestFlg = pyo.Var(MONTHS_KEYS, WORKERS_KEYS, within = pyo.Binary)


    # /** Неявные переменные решения **/


    # /* Суммарное время в работе сотрудника за год */
    def YearWork(w):
        return sum(model.iWorkHours[m,w,q] for m in MONTHS_KEYS for q in QUALS_KEYS if QUALS[w,q] == 1)

    # /* Суммарное время работы по квалификации за месяц */
    def QualWork(m, q):
        return sum(model.iWorkHours[m,w,q] for w in WORKERS_KEYS if QUALS[w,q] == 1)

    # /* !! */
    def DifRestsHours(w):
        return 184 - sum(model.iRestHours[m,w] for m in MONTHS_KEYS)

    # /* Рабочее и отпускное время в сумме не должны превышать лимит рабочего времени сотрудника в месяце */
    def cMaxMonthTime_rule (model, m, w):
        return model.iRestHours[m,w] + sum(model.iWorkHours[m,w,q] for q in QUALS_KEYS if QUALS[w,q] == 1) <= WORKERS[w]['MaxFly']
    model.cMaxMonthTime = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cMaxMonthTime_rule)

    # /* Лимит на рабочее время сотрудника за год */
    def cMaxYearTime_rule (model, w):
        return YearWork(w) <= 10 * WORKERS[w]['MaxFly']
    model.cMaxYearTime = pyo.Constraint(WORKERS_KEYS, rule = cMaxYearTime_rule)

    # /* Максимальное количество отпусков сотрудника в год */
    def cMaxRestsCount_rule (model, w):
        return sum(model.zRestFlg[m,w] for m in MONTHS_KEYS) <= 4
    model.cMaxRestsCount = pyo.Constraint(WORKERS_KEYS, rule = cMaxRestsCount_rule)

    # /* Максимальный объем отпусков сотрудника в год */
    def cMaxRestsHours_rule (model, w):
        return sum(model.iRestHours[m,w] for m in MONTHS_KEYS) <= 184
    model.cMaxRestsHours = pyo.Constraint(WORKERS_KEYS, rule = cMaxRestsHours_rule)

    # /* Минимальное количество месяцев между отпусками одного сотрудника */
    def cRestLag_rule (model, m, w):
        return sum(model.zRestFlg[m + t,w] for t in range(0, 2)) <= 1
    model.cRestLag = pyo.Constraint([m for m in MONTHS_KEYS if m + 1 in MONTHS_KEYS], WORKERS_KEYS, rule = cRestLag_rule)

    # /* Максимальное количество отпусков сотрудника в топовые месяцы */
    def cMaxTopCount_rule (model, w):
        return sum(model.zRestFlg[m,w] for m in MONTHS_KEYS if MONTHS[m]['Top'] == 1) <= 3
    model.cMaxTopCount = pyo.Constraint(WORKERS_KEYS, rule = cMaxTopCount_rule)

    # /* Максимальное количество отпусков сотрудника в нетоповые месяцы */
    def cMaxNotTopCount_rule (model, w):
        return sum(model.zRestFlg[m,w] for m in MONTHS_KEYS if MONTHS[m]['Top'] == 0) <= 3
    model.cMaxNotTopCount = pyo.Constraint(WORKERS_KEYS, rule = cMaxNotTopCount_rule)

    # /* Максимальный объем отпусков сотрудника в топовые месяцы */
    def cMaxTopHours_rule (model, w):
        return sum(model.iRestHours[m,w] for m in MONTHS_KEYS if MONTHS[m]['Top'] == 1) <= 147
    model.cMaxTopHours = pyo.Constraint(WORKERS_KEYS, rule = cMaxTopHours_rule)

    # /* Максимальный объем отпусков сотрудника в нетоповые месяцы */
    def cMaxNotTopHours_rule (model, w):
        return sum(model.iRestHours[m,w] for m in MONTHS_KEYS if MONTHS[m]['Top'] == 0) <= 147
    model.cMaxNotTopHours = pyo.Constraint(WORKERS_KEYS, rule = cMaxNotTopHours_rule)

    # /* Необходимо выделять требуемое количество ресурсов по квалификациям */
    def cRequired_rule (model, m, q):
        return QualWork(m, q) == REQUIRED[m,q]['Required']
    model.cRequired = pyo.Constraint(MONTHS_KEYS, QUALS_KEYS, rule = cRequired_rule)

    # /* Если рабочих часов 0, то флаг отпуска = 0 */
    def cRestFlg1_rule (model, m, w):
        return model.zRestFlg[m,w] <= model.iRestHours[m,w]
    model.cRestFlg1 = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cRestFlg1_rule)

    # /* Если рабочих часов > 0, то флаг отпуска = 1 */
    def cRestFlg2_rule (model, m, w):
        return model.iRestHours[m,w] <= model.zRestFlg[m,w] * MONTHS[m]['MaxRest']
    model.cRestFlg2 = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cRestFlg2_rule)

    # /*Минимум 1 отпуск в топ месяц*/
    def cMinTop_rule (model, w):
        return sum(model.zRestFlg[m,w] for m in MONTHS_KEYS if MONTHS[m]['Top'] == 1) >= 1
    model.cMinTop = pyo.Constraint(WORKERS_KEYS, rule = cMinTop_rule)

    # /*Минимальная продолжительность отпуска*/
    def cMinRestSize_rule (model, m, w):
        return model.iRestHours[m,w] >= 36 * model.zRestFlg[m,w]
    model.cMinRestSize = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cMinRestSize_rule)


    # /* Минимизация отклонений от заявок сотрудников с учетом приоритетов */
    model.OBJ = pyo.Objective(expr = sum(DifRestsHours(w) for w in WORKERS_KEYS))

    opt = SolverFactory("gurobi", solver_io="python", options={'TimeLimit': 100})
    instance = model
    results = opt.solve(instance)

    result = []
    for m,w in [(m,w) for m in MONTHS_KEYS for w in WORKERS_KEYS]:
        result.append([Qual, m, w, model.iRestHours[m,w].value])
    return result
    
Quals = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9', 'Q10']
opt_final_results = []
for Qual in Quals:
    opt_final_results += run_optimization(Qual)

result_df = pd.DataFrame(opt_final_results, columns = ['Квалификация', 'Месяц', 'Сотрудник', 'Количество дней отпуска'])
result_df.to_excel(r'C:\Users\rusivr\Documents\GitHub\ramax\logs\result1.xlsx')
