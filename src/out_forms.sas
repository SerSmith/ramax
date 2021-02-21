/*proc printto 
  log="/home/sasdemo112/casuser/ramax/logs/log_%sysfunc(translate(%sysfunc(datetime(),datetime20.3),--,.:)).log" 
  new;
run;*/

libname lib base "/home/sasdemo112/casuser/ramax/input";

%macro optimization(
  mpi_quals         = LIB.QUALS,
  mpi_months          = LIB.MONTHS,
  mpi_qualified       = LIB.QUALIFIED,
  mpi_workers        = LIB.WORKERS,
  mpi_required_personal   = LIB.REQUIRED_PERSONAL,
  mpi_rest_req       = LIB.REST_REQ,
  mpi_total_rests     = 4,
  mpi_rest_year      = 184,
  mpi_prior_rests     = 3,
  mpi_noprior_rests     = 3,
  mpi_rest_high       = 147,
  mpi_rest_low       = 147,
  mpi_min_rest_lag     = 2,
  mpi_min_rest_size    = 36,

  mpo_work_hours       = LIB.WORK_HOURS,
  mpo_months_workers     = LIB.MONTHS_WORKERS
);

  proc optmodel;

    / Объявление множеств и чтение данных /

    set <num> WORKERS;
    num PersonalLevel {WORKERS}, MaxFly {WORKERS}, Starts {WORKERS}, MaxStarts {WORKERS};

    read data &mpi_workers. into WORKERS = [worker]
    PersonalLevel MaxFly Starts MaxStarts;

    set <str> QUALS;

    read data &mpi_quals. into QUALS = [qual];

    set <num> MONTHS;
    num Top {MONTHS}, MaxRest{MONTHS};

    read data &mpi_months. into MONTHS = [month]
    Top MaxRest;

    num QualFlg {WORKERS, QUALS};

    read data &mpi_qualified. into [worker qual]
    QualFlg;

    num Required {MONTHS, QUALS};

    read data &mpi_required_personal. into [month qual]
    Required;

    num RestReq {MONTHS, WORKERS}, RestPrior {MONTHS, WORKERS};

    read data &mpi_rest_req. into [month worker]
    RestReq RestPrior;

    num MaxPersonalLevel = max {w in WORKERS} PersonalLevel[w];

    num OrderRate {MONTHS, WORKERS};
    /* Расчет рейтинга заявки сотрудника по заданной формуле */
    for {m in MONTHS, w in WORKERS} do;
      OrderRate[m,w] = (4 - RestPrior[m,w]) * (MaxPersonalLevel + 1) + PersonalLevel[w];
    end;

    /** Переменные решения **/


    /* Сколько часов в месяце должен работать конкретный сотрудник с определенной квалификацией */
    var iWorkHours {MONTHS, w in WORKERS, q in QUALS: QualFlg[w,q] = 1} >= 0 integer;

    /* Сколько часов в месяце сотрудник находится в отпуске */
    var iRestHours {m in MONTHS, WORKERS} >= 0 <= MaxRest[m] integer;

    /* Индикатор того, что сотрудник уходит в отпуск в этом месяце */
    var zRestFlg {MONTHS, WORKERS} binary;

    /*Отклонение от заявки работника в часах*/
    var xDev {MONTHS, WORKERS} >= 0;


    /** Неявные переменные решения **/


    /* Суммарное время в работе сотрудника за год */
    impvar YearWork {w in WORKERS} = 
      sum {m in MONTHS, q in QUALS: QualFlg[w,q] = 1} iWorkHours[m,w,q];

    /* Суммарное время работы по квалификации за месяц */
    impvar QualWork {m in MONTHS, q in QUALS} =
      sum {w in WORKERS: QualFlg[w,q] = 1} iWorkHours[m,w,q];
  
    /* !! */
    impvar DifRestsHours{w in WORKERS} = 
      &mpi_rest_year. - sum {m in MONTHS} iRestHours[m,w];

    /** Ограничения **/


    /* Рабочее и отпускное время в сумме не должны превышать лимит рабочего времени сотрудника в месяце */
    con cMaxMonthTime {m in MONTHS, w in WORKERS}:
      iRestHours[m,w] + sum {q in QUALS: QualFlg[w,q] = 1} iWorkHours[m,w,q] <= MaxFly[w];

    /* Лимит на рабочее время сотрудника за год */
    con cMaxYearTime {w in WORKERS}:
      YearWork[w] <= 10 * MaxFly[w];

    /* Максимальное количество отпусков сотрудника в год */
    con cMaxRestsCount {w in WORKERS}:
      sum {m in MONTHS} zRestFlg[m,w] <= &mpi_total_rests.;

    /* Максимальный объем отпусков сотрудника в год */
    con cMaxRestsHours {w in WORKERS}:
      sum {m in MONTHS} iRestHours[m,w] <= &mpi_rest_year.;

    /* Максимальный объем отпусков сотрудника в год */
/*     con cMaxRestsHours_min {w in WORKERS}: */
/*       &mpi_rest_year. * 0.5 <= sum {m in MONTHS} iRestHours[m,w]; */
    /* Максимальный объем отпусков сотрудника в год */
/*     con cMaxRestsHours_max {w in WORKERS}: */
/*       sum {m in MONTHS} iRestHours[m,w] <= &mpi_rest_year.; */

/* Минимальное количество месяцев между отпусками одного сотрудника */
    con cRestLag {m in MONTHS, w in WORKERS: m + (&mpi_min_rest_lag. - 1) in MONTHS}:
      sum {t in 0..(&mpi_min_rest_lag. - 1)} zRestFlg[m + t,w] <= 1;

    /* Максимальное количество отпусков сотрудника в топовые месяцы */
    con cMaxTopCount {w in WORKERS}:
      sum {m in MONTHS: Top[m] = 1} zRestFlg[m,w] <= &mpi_prior_rests.;

    /* Максимальное количество отпусков сотрудника в нетоповые месяцы */
    con cMaxNotTopCount {w in WORKERS}:
      sum {m in MONTHS: Top[m] = 0} zRestFlg[m,w] <= &mpi_noprior_rests.;

    /* Максимальный объем отпусков сотрудника в топовые месяцы */
    con cMaxTopHours {w in WORKERS}:
      sum {m in MONTHS: Top[m] = 1} iRestHours[m,w] <= &mpi_rest_high.;

    /* Максимальный объем отпусков сотрудника в нетоповые месяцы */
    con cMaxNotTopHours {w in WORKERS}:
      sum {m in MONTHS: Top[m] = 0} iRestHours[m,w] <= &mpi_rest_low.;

    /* Необходимо выделять требуемое количество ресурсов по квалификациям */
    con cRequired {m in MONTHS, q in QUALS}:
      QualWork[m,q] = Required[m,q];

    /* Если рабочих часов 0, то флаг отпуска = 0 */
    con cRestFlg1 {m in MONTHS, w in WORKERS}:
      zRestFlg[m,w] <= iRestHours[m,w];

    /* Если рабочих часов > 0, то флаг отпуска = 1 */
    con cRestFlg2 {m in MONTHS, w in WORKERS}:
      iRestHours[m,w] <= zRestFlg[m,w] * MaxRest[m];

    /*Линеаризация отклонения заявки сотрудника от предоставленного отпуска в часах*/
    con cLinDev {m in MONTHS, w in WORKERS}:
      RestReq[m,w] - iRestHours[m,w] <= xDev[m,w];

    /*Минимум 1 отпуск в топ месяц*/
    con cMinTop {w in WORKERS}:
      sum {m in MONTHS: Top[m] = 1} zRestFlg[m,w] >= 1;

    /*Минимальная продолжительность отпуска*/
    con cMinRestSize {m in MONTHS, w in WORKERS}:
      iRestHours[m,w] >= &mpi_min_rest_size. * zRestFlg[m,w];


    /** Целевая функция **/


    /* Минимизация отклонений от заявок сотрудников с учетом приоритетов */
    min TotalDeviation =
      sum {m in MONTHS, w in WORKERS} xDev[m,w] * OrderRate[m,w]
      + sum {w in WORKERS} DifRestsHours[w];

    solve with milp / relobjgap=0.1 maxtime = 3600 nthreads = 32 decomp=(method=concomp);


    /** Выходные таблицы **/


    create data &mpo_work_hours. from [month worker qual] = {m in MONTHS, w in WORKERS, q in QUALS: QualFlg[w,q] = 1} 
    iWorkHours;

    create data &mpo_months_workers. from [month worker] = {m in MONTHS, w in WORKERS} 
      iRestHours zRestFlg xDev OrderRate
    ;

    create data &mpo_personal_rest. from [worker month] = {w in WORKERS, m in MONTHS: iRestHours[m,w] > 0.5}
      iRestHours[m,w]
      OrderFlg = 1]
    ;

    create data &mpo_total_rests. from [worker] = {w in WORKERS}
      RestCount = (sum {m in MONTHS} zRestFlg[m,w])
      RestHours = (sum {m in MONTHS} iRestHours[m,w])
      RestLeft = (max(&mpi_rest_year. - (sum {m in MONTHS} iRestHours[m,w]),0))
    ;

    create data &mpo_summary from [month] = {m in MONTHS}
      RequiredSum = (sum {q in QUALIFIED} Required[m,q])
      WorkSum = (sum {w in WORKERS, q in QUALIFIED: QualFlg[w,q] = 1} iWorkHours[m,w,q])
      RestHours = (sum {w in WORKERS} iRestHours[m,w])
      RestCount = (sum {w in WORKERS} zRestFlg[m,w])
    ;



  quit;

%mend;


%optimization;