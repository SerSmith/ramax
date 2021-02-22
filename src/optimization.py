import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import pandas as pd

GLOBAL_PATH = r'C:\Users\rusivr\Documents\GitHub\ramax\logs'

def run_optimization(
    Qual                    = 'Q1',
    mpi_total_rests 		= 4,
	mpi_rest_year			= 184,
	mpi_prior_rests 		= 3,
	mpi_noprior_rests 		= 3,
	mpi_rest_high 			= 147,
	mpi_rest_low 			= 147,
	mpi_min_rest_lag 		= 2,
	mpi_min_rest_size		= 36,
	mpi_min_rest_part_size	= 3,
	mpi_order_weight        = -0.005,
	mpi_deviation_weight    = 1):

    input_path = r'C:\Users\rusivr\Documents\GitHub\ramax\input\input_vacation.xlsx'
    # Массив характеристик сотрудников
    WORKERS = pd.read_excel (input_path, sheet_name = 'PersonalLevel ', index_col = [0]).to_dict('index')
    # Массив характеристик квалификаций
    QUALS = pd.read_excel (input_path, sheet_name = 'Qualified ', index_col = [0, 1]).to_dict('index')
    QUALS = { (w, q): QUALS[w, q]['QualFlg'] for w, q in QUALS.keys() if q == Qual and QUALS[w,q]['QualFlg'] == 1}
    # Массив характеристик месяцев
    MONTHS = pd.read_excel (input_path, sheet_name = 'Months', index_col = [0]).to_dict('index')
    # Массив характеристик важности заявки человека
    REQUIRED = pd.read_excel (input_path, sheet_name = 'RequiredPersonal ', index_col = [0, 1]).to_dict('index')
    # Массив характеристик заявок
    RestReqPrior = pd.read_excel (input_path, sheet_name = 'RestReq ', index_col = [0, 1]).to_dict('index')

    # Создание конкретной модели pyomo
    model = pyo.ConcreteModel()

    # Ключ - (Сотрудник, квалификация)
    WORKER_QUALS_KEYS = list(QUALS.keys())
    # Ключ - (Квалификация)
    QUALS_KEYS = list(set([q for (w, q) in WORKER_QUALS_KEYS]))
    # Ключ - (Сотрудник)
    WORKERS_KEYS = list(set([w for (w, q) in WORKER_QUALS_KEYS]))
    # Ключ - (Месяц)
    MONTHS_KEYS = list(MONTHS.keys())

    # Расчет рейтинга заявки сотрудника по заданной формуле
    MaxPersonalLevel = max(WORKERS[w]['PersonalLevel'] for w in WORKERS_KEYS)
    def OrderRate(m, w, MaxPersonalLevel):
        return (4 - RestReqPrior[m,w]['RestPrior']) * (MaxPersonalLevel + 1) + WORKERS[w]['PersonalLevel']


    # Переменные решения


    # Сколько часов в месяце должен работать конкретный сотрудник с определенной квалификацией
    model.iWorkHours = pyo.Var(MONTHS_KEYS, [(w, q) for (w, q) in WORKER_QUALS_KEYS if QUALS[w,q] == 1], within = pyo.NonNegativeIntegers, initialize=0)

    # Сколько часов в месяце сотрудник находится в отпуске 
    model.iRestHoursP1 = pyo.Var(MONTHS_KEYS, WORKERS_KEYS, within=pyo.NonNegativeIntegers, initialize = 0)
    # Сколько часов в месяце сотрудник находится в перенесенном отпуске
    model.iRestHoursP2 = pyo.Var(MONTHS_KEYS, WORKERS_KEYS, within=pyo.NonNegativeIntegers, initialize = 0)

    # Индикатор того, что сотрудник уходит в отпуск в этом месяце
    model.zRestFlg = pyo.Var(MONTHS_KEYS, WORKERS_KEYS, within = pyo.Binary, initialize = 0)

    # Индикатор того, что сотрудник уходит в отпуск в этом месяце */
    model.zStartFlg = pyo.Var(MONTHS_KEYS, WORKERS_KEYS, within=pyo.Binary, initialize = 0)

	# Индикатор того, что сотрудник находился в перенесенном отпуске в этом месяце */
    model.zTransFlg = pyo.Var(MONTHS_KEYS, WORKERS_KEYS, within=pyo.Binary, initialize = 0)

    # Индикатор удовлетворения заявки сотрудника на отпуск*/
    model.zApproved = pyo.Var([(m, w) for m in MONTHS_KEYS for w in WORKERS_KEYS if RestReqPrior[m,w]['RestReq'] >= mpi_min_rest_size], within=pyo.Binary, initialize=0)
    
    
    # Неявные переменные решения


    # Суммарное время в работе сотрудника за год
    def YearWork(w):
        return sum(model.iWorkHours[m,w,q] for m in MONTHS_KEYS for q in QUALS_KEYS if QUALS[w,q] == 1)

    # Суммарное время работы по квалификации за месяц
    def QualWork(m, q):
        return sum(model.iWorkHours[m,w,q] for w in WORKERS_KEYS if QUALS[w,q] == 1)

    # Суммарное время отпуска сотрудника с учетом перенесенной на следующий месяц части (для декабря след. месяц - январь этого же года)
    def RestFull(m, w):
        if m == 12: 
            return model.iRestHoursP1[m,w] + model.iRestHoursP2[1,w] 
        else: 
            return model.iRestHoursP1[m,w] + model.iRestHoursP2[m+1,w]

    # Суммарное время отпуска сотрудника с учетом перенесенной на следующий месяц части (для декабря след. месяц - январь этого же года) 
    def iRestHours(m, w):
        return model.iRestHoursP1[m,w] + model.iRestHoursP2[m,w]
        
    # Отклонение в количестве часов отпуска от желаемых 184 часов
    def DifRestsHours(w):
        return mpi_rest_year - sum(iRestHours(m,w) for m in MONTHS_KEYS)

    # Рабочее и отпускное время в сумме не должны превышать лимит рабочего времени сотрудника в месяце
    def cMaxMonthTime_rule (model, m, w):
        return iRestHours(m,w) + sum(model.iWorkHours[m,w,q] for q in QUALS_KEYS if QUALS[w,q] == 1) <= WORKERS[w]['MaxFly']
    model.cMaxMonthTime = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cMaxMonthTime_rule)

    # Лимит на рабочее время сотрудника за год
    def cMaxYearTime_rule (model, w):
        return YearWork(w) <= 10 * WORKERS[w]['MaxFly']
    model.cMaxYearTime = pyo.Constraint(WORKERS_KEYS, rule = cMaxYearTime_rule)

    # Максимальное количество отпусков сотрудника в год
    def cMaxRestsCount_rule (model, w):
        return sum(model.zStartFlg[m,w] for m in MONTHS_KEYS) <= mpi_total_rests
    model.cMaxRestsCount = pyo.Constraint(WORKERS_KEYS, rule = cMaxRestsCount_rule)

    def cMaxRestMonth_rule (model, m, w):
        return RestFull(m,w) <= MONTHS[m]['MaxRest']
    model.cMaxRestMonth = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cMaxRestMonth_rule)
    
    # Максимальный объем отпусков сотрудника в год
    def cMaxRestsHours_rule (model, w):
        return sum(iRestHours(m,w) for m in MONTHS_KEYS) <= mpi_rest_year
    model.cMaxRestsHours = pyo.Constraint(WORKERS_KEYS, rule = cMaxRestsHours_rule)

    # Минимальное количество месяцев между отпусками одного сотрудника
    def cRestLag_rule (model, m, w):
        if m == 12:
            return model.zStartFlg[12,w] + model.zStartFlg[1,w] <= 1
        else:
            return sum(model.zStartFlg[m + t,w] for t in range(0, mpi_min_rest_lag)) <= 1
    model.cRestLag = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cRestLag_rule)

    # Максимальное количество отпусков сотрудника в топовые месяцы 
    def cMaxTopCount_rule (model, w):
        return sum(model.zStartFlg[m,w] for m in MONTHS_KEYS if MONTHS[m]['Top'] == 1) <= mpi_prior_rests
    model.cMaxTopCount = pyo.Constraint(WORKERS_KEYS, rule = cMaxTopCount_rule)

    # Максимальное количество отпусков сотрудника в нетоповые месяцы
    def cMaxNotTopCount_rule (model, w):
        return sum(model.zStartFlg[m,w] for m in MONTHS_KEYS if MONTHS[m]['Top'] == 0) <= mpi_noprior_rests
    model.cMaxNotTopCount = pyo.Constraint(WORKERS_KEYS, rule = cMaxNotTopCount_rule)

    # Максимальный объем отпусков сотрудника в топовые месяцы 
    def cMaxTopHours_rule (model, w):
        return sum(RestFull(m,w) for m in MONTHS_KEYS if MONTHS[m]['Top'] == 1) <= mpi_rest_high
    model.cMaxTopHours = pyo.Constraint(WORKERS_KEYS, rule = cMaxTopHours_rule)

    # Максимальный объем отпусков сотрудника в нетоповые месяцы
    def cMaxNotTopHours_rule (model, w):
        return sum(RestFull(m,w) for m in MONTHS_KEYS if MONTHS[m]['Top'] == 0) <= mpi_rest_low
    model.cMaxNotTopHours = pyo.Constraint(WORKERS_KEYS, rule = cMaxNotTopHours_rule)

    # Необходимо выделять требуемое количество ресурсов по квалификациям 
    def cRequired_rule (model, m, q):
        return QualWork(m, q) == REQUIRED[m,q]['Required']
    model.cRequired = pyo.Constraint(MONTHS_KEYS, QUALS_KEYS, rule = cRequired_rule)

    # Минимум 1 отпуск в топ месяц
    def cMinTop_rule (model, w):
        return sum(model.zStartFlg[m,w] for m in MONTHS_KEYS if MONTHS[m]['Top'] == 1) >= 1
    model.cMinTop = pyo.Constraint(WORKERS_KEYS, rule = cMinTop_rule)

    # Минимальная продолжительность отпуска
    def cMinRestSize_rule (model, m, w):
        return RestFull(m,w) >= mpi_min_rest_size * model.zStartFlg[m,w]
    model.cMinRestSize = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cMinRestSize_rule)

	# Если стартовых отпускных часов 0, то флаг начала отпуска = 0
    def cLinRestStart1_rule (model, m, w):
        return model.zStartFlg[m,w] <= model.iRestHoursP1[m,w]
    model.cLinRestStart1 = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cLinRestStart1_rule)

	# Если стартовых отпускных часов > 0, то флаг начала отпуска = 1
    def cLinRestStart2_rule (model, m, w):
        return model.iRestHoursP1[m,w] <= model.zStartFlg[m,w] * MONTHS[m]['MaxRest']
    model.cLinRestStart2 = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cLinRestStart2_rule)


    # Если продолженных отпускных часов 0, то флаг продолжения отпуска = 0
    def cLinRestTrans1_rule (model, m, w):
        return model.zTransFlg[m,w] <= model.iRestHoursP2[m,w]
    model.cLinRestTrans1 = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cLinRestTrans1_rule)


    # Если продолженных отпускных часов > 0, то флаг продолжения отпуска = 1
    def cLinRestTrans2_rule (model, m, w):
        return model.iRestHoursP2[m,w] <= model.zTransFlg[m,w] * MONTHS[m]['MaxRest']
    model.cLinRestTrans2 = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cLinRestTrans2_rule)

    # Минимальная продолжительность основной части отпуска
    def cMinRestSizeP1_rule (model, m, w):
        return model.iRestHoursP1[m,w] >= mpi_min_rest_part_size * model.zStartFlg[m,w]
    model.cMinRestSizeP1 = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cMinRestSizeP1_rule)


    # Минимальная продолжительность перенесенной части отпуска
    def cMinRestSizeP2_rule (model, m, w):
        return model.iRestHoursP2[m,w] >= mpi_min_rest_part_size * model.zTransFlg[m,w]
    model.cMinRestSizeP2 = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cMinRestSizeP2_rule)


    # В один месяц можно либо начать отпуск, либо продолжить
    def cOneType_rule (model, m, w):
        return model.zStartFlg[m,w] + model.zTransFlg[m,w] <= 1
    model.cOneType = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cOneType_rule)

    # Продолжить работу можно только, если она была начата в прошлый месяц
    def cContinued_rule (model, m, w):
        if m == 1: 
            return model.zTransFlg[m,w] <= model.zStartFlg[12,w]
        else:
            return model.zTransFlg[m,w] <= model.zStartFlg[m-1,w]
    model.cContinued = pyo.Constraint(MONTHS_KEYS, WORKERS_KEYS, rule = cContinued_rule)

    # Линеаризация индикатора удовлетворения заявки
    def cLinApproved1_rule (model, m, w):
        return model.zApproved[m,w] * RestReqPrior[m,w]['RestReq'] <= RestFull(m,w)
    model.cLinApproved1 = pyo.Constraint([(m,w) for m in MONTHS_KEYS for w in WORKERS_KEYS if RestReqPrior[m,w]['RestReq'] >= mpi_min_rest_size], rule = cLinApproved1_rule)

    def cLinApproved2_rule (model, m, w):
        return - 200 * (1 - model.zApproved[m,w]) <= 1 - RestFull(m,w) / RestReqPrior[m,w]['RestReq']
    model.cLinApproved2 = pyo.Constraint([(m,w) for m in MONTHS_KEYS for w in WORKERS_KEYS if RestReqPrior[m,w]['RestReq'] >= mpi_min_rest_size], rule = cLinApproved2_rule)

    # Ограничение на минимальный учет потребностей
    def cCountApprovedHARD_rule (model):
        return sum(OrderRate(m,w,MaxPersonalLevel) * model.zApproved[m,w] for m in MONTHS_KEYS for w in WORKERS_KEYS if RestReqPrior[m,w]['RestReq'] >= mpi_min_rest_size) >= 0.3 * sum(OrderRate(m,w,MaxPersonalLevel) * (RestReqPrior[m,w]['RestReq'] > 0) for m in MONTHS_KEYS for w in WORKERS_KEYS)
    model.cCountApprovedHARD = pyo.Constraint(rule = cCountApprovedHARD_rule)
        

    # Минимизация отклонений от заявок сотрудников с учетом приоритетов
    model.OBJ = pyo.Objective(expr = 
			  mpi_order_weight * sum ((model.zApproved[m,w] * OrderRate(m,w,MaxPersonalLevel)) for m in MONTHS_KEYS for w in WORKERS_KEYS if RestReqPrior[m,w]['RestReq'] >= 36)
      		+ mpi_deviation_weight * sum(DifRestsHours(w) for w in WORKERS_KEYS))
    GUROBI_LOG = GLOBAL_PATH + r'GUROBI_LOG.txt'
    SOLVE_LOG = GLOBAL_PATH + r'SOLVE_LOG.txt'
    SOLNFILE = GLOBAL_PATH + r'SOLNFILE.txt'

    # Вызов Gurobi солвера
    opt = SolverFactory("gurobi", solver_io="python", options={'TimeLimit': 1800, 'LogFile' : GUROBI_LOG, "threads" : 4})
    instance = model
    results = opt.solve(instance, logfile = SOLVE_LOG, solnfile = SOLNFILE)
 	
    # Создание выходной таблицы
    result = []
    for m,w in [(m,w) for m in MONTHS_KEYS for w in WORKERS_KEYS]:
        if RestReqPrior[m,w]['RestReq'] >= mpi_min_rest_size:
            approved = model.zApproved[m,w].value
            orderrt = OrderRate(m,w,MaxPersonalLevel)
        else:
            approved = 0
            orderrt = 0
        result.append([Qual, m, w, model.iRestHoursP1[m,w].value, model.iRestHoursP2[m,w].value, model.zRestFlg[m,w].value, model.zStartFlg[m,w].value, model.zTransFlg[m,w].value, approved, orderrt])

    return result

Quals = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9', 'Q10']

# Таблица с результататми
opt_final_results = []
for Qual in Quals:
    opt_final_results += run_optimization(Qual)


result_df = pd.DataFrame(opt_final_results, columns = ['qual', 'm', 'w', 'iRestHoursP1', 'iRestHoursP2', 'zRestFlg', 'zStartFlg', 'zTransFlg', 'approved', 'OrderRate'])
result_df.to_excel(GLOBAL_PATH + r'\result.xlsx')