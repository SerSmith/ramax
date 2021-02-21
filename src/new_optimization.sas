libname lib base "/home/sasdemo112/casuser/ramax/input";

%macro optimization(
	mpi_quals 				= LIB.QUALS,
	mpi_months		    	= LIB.MONTHS,
	mpi_qualified 			= LIB.QUALIFIED,
	mpi_workers				= LIB.WORKERS,
	mpi_required_personal   = LIB.REQUIRED_PERSONAL,
	mpi_rest_req 			= LIB.REST_REQ,
	mpi_total_rests 		= 4,
	mpi_rest_year			= 184,
	mpi_prior_rests 		= 3,
	mpi_noprior_rests 		= 3,
	mpi_rest_high 			= 147,
	mpi_rest_low 			= 147,
	mpi_min_rest_lag 		= 2,
	mpi_min_rest_size		= 36,
	mpi_min_rest_part_size	= 3,
	mpi_order_weight        = 0.005,
	mpi_deviation_weight    = 1,

	mpo_work_hours 			= LIB.WORK_HOURS,
	mpo_months_workers 		= LIB.MONTHS_WORKERS,
	mpo_personal_rest    	= LIB.PERSONAL_RESTS,
 	mpo_total_rests     	= LIB.TOTAL_RESTS,
 	mpo_summary         	= LIB.SUMMARY
);

	proc optmodel;

		/** Объявление множеств и чтение данных **/

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

		set <num> SHIFTS = {0..1};

		/** Переменные решения **/


		/* Сколько часов в месяце должен работать конкретный сотрудник с определенной квалификацией */
		var iWorkHours {MONTHS, w in WORKERS, q in QUALS: QualFlg[w,q] = 1} >= 0 integer;

		/* Сколько часов в месяце сотрудник находится в отпуске */
		var iRestHoursP1 {m in MONTHS, WORKERS} >= 0 integer;

		/* Сколько часов в месяце сотрудник находится в перенесенном отпуске */
		var iRestHoursP2 {m in MONTHS, WORKERS} >= 0 integer;

		/* Индикатор того, что сотрудник уходит в отпуск в этом месяце */
		var zStartFlg {MONTHS, WORKERS} binary;

		/*  Индикатор того, что сотрудник находился в перенесенном отпуске в этом месяце */
		var zTransFlg {MONTHS, WORKERS} binary;

		/* Индикатор удовлетворения заявки сотрудника на отпуск*/
		var zApproved {m in MONTHS, w in WORKERS: RestReq[m,w] >= &mpi_min_rest_size.} binary;


		/** Неявные переменные решения **/


		/* Суммарное время в работе сотрудника за год */
		impvar YearWork {w in WORKERS} = 
			sum {m in MONTHS, q in QUALS: QualFlg[w,q] = 1} iWorkHours[m,w,q];

		/* Суммарное время работы по квалификации за месяц */
		impvar QualWork {m in MONTHS, q in QUALS} =
			sum {w in WORKERS: QualFlg[w,q] = 1} iWorkHours[m,w,q];

		/* Суммарное время отпуска сотрудника с учетом перенесенной на следующий месяц части (для декабря след. месяц - январь этого же года) */
		impvar RestFull {m in MONTHS, w in WORKERS} =
			iRestHoursP1[m,w] + (if m = 12 then iRestHoursP2[1,w] else iRestHoursP2[m+1,w]);		

		/* Отклонение в количестве часов отпуска от желаемых 184 часов*/
    	impvar DifRestsHours{w in WORKERS} = 
     		&mpi_rest_year. - sum {m in MONTHS} (iRestHoursP1[m,w] + iRestHoursP2[m,w]);



		/** Ограничения **/


		/* Рабочее и отпускное время в сумме не должны превышать лимит рабочего времени сотрудника в месяце */
		con cMaxMonthTime {m in MONTHS, w in WORKERS}:
			iRestHoursP1[m,w] + iRestHoursP2[m,w] + sum {q in QUALS: QualFlg[w,q] = 1} iWorkHours[m,w,q] <= MaxFly[w];

		/* Лимит на рабочее время сотрудника за год */
		con cMaxYearTime {w in WORKERS}:
			YearWork[w] <= 10 * MaxFly[w];

		/* Максимальное количество отпусков сотрудника в год */
		con cMaxRestsCount {w in WORKERS}:
			sum {m in MONTHS} zStartFlg[m,w] <= &mpi_total_rests.;

		con cMaxRestMonth {m in MONTHS, w in WORKERS}:
			iRestHoursP1[m,w] + iRestHoursP2[m,w] <= MaxRest[m];

		/* Максимальный объем отпусков сотрудника в год */
		con cMaxRestsHours {w in WORKERS}:
			sum {m in MONTHS} (iRestHoursP1[m,w] + iRestHoursP2[m,w]) <= &mpi_rest_year.;

		/* Минимальное количество месяцев между отпусками одного сотрудника */
		con cRestLag {m in MONTHS, w in WORKERS: m + (&mpi_min_rest_lag. - 1) in MONTHS}:
			sum {t in 0..(&mpi_min_rest_lag. - 1)} zStartFlg[m + t,w] <= 1;

		/* Максимальное количество отпусков сотрудника в топовые месяцы */
		con cMaxTopCount {w in WORKERS}:
			sum {m in MONTHS: Top[m] = 1} zStartFlg[m,w] <= &mpi_prior_rests.;

		/* Максимальное количество отпусков сотрудника в нетоповые месяцы */
		con cMaxNotTopCount {w in WORKERS}:
			sum {m in MONTHS: Top[m] = 0} zStartFlg[m,w] <= &mpi_noprior_rests.;

		/* Максимальный объем отпусков сотрудника в топовые месяцы */
		con cMaxTopHours {w in WORKERS}:
			sum {m in MONTHS: Top[m] = 1} RestFull[m,w] <= &mpi_rest_high.;

		/* Максимальный объем отпусков сотрудника в нетоповые месяцы */
		con cMaxNotTopHours {w in WORKERS}:
			sum {m in MONTHS: Top[m] = 0} RestFull[m,w] <= &mpi_rest_low.;

		/* Необходимо выделять требуемое количество ресурсов по квалификациям */
		con cRequired {m in MONTHS, q in QUALS}:
			QualWork[m,q] = Required[m,q];

		/* Минимум 1 отпуск в топ месяц */
		con cMinTop {w in WORKERS}:
			sum {m in MONTHS: Top[m] = 1} zStartFlg[m,w] >= 1;

		/* Минимальная продолжительность отпуска */ 
		con cMinRestSize {m in MONTHS, w in WORKERS}:
			RestFull[m,w] >= &mpi_min_rest_size. * zStartFlg[m,w];

		/* Если стартовых отпускных часов 0, то флаг начала отпуска = 0 */
		con cLinRestStart1 {m in MONTHS, w in WORKERS}:
			zStartFlg[m,w] <= iRestHoursP1[m,w];

		/* Если стартовых отпускных часов > 0, то флаг начала отпуска = 1 */
		con cLinRestStart2 {m in MONTHS, w in WORKERS}:
			iRestHoursP1[m,w] <= zStartFlg[m,w] * MaxRest[m];

		/* Если продолженных отпускных часов 0, то флаг продолжения отпуска = 0 */
		con cLinRestTrans1 {m in MONTHS, w in WORKERS}:
			zTransFlg[m,w] <= iRestHoursP2[m,w];

		/* Если продолженных отпускных часов > 0, то флаг продолжения отпуска = 1 */
		con cLinRestTrans2 {m in MONTHS, w in WORKERS}:
			iRestHoursP2[m,w] <= zTransFlg[m,w] * MaxRest[m];

		/* Минимальная продолжительность основной части отпуска */ 
		con cMinRestSizeP1 {m in MONTHS, w in WORKERS}:
			iRestHoursP1[m,w] >= &mpi_min_rest_part_size. * zStartFlg[m,w];

		/* Минимальная продолжительность перенесенной части отпуска */ 
		con cMinRestSizeP2 {m in MONTHS, w in WORKERS}:
			iRestHoursP1[m,w] >= &mpi_min_rest_part_size. * zTransFlg[m,w];

		num BigM = 200;

		/*Линеаризация индикатора удовлетворения заявки*/
		con cLinApproved1 {m in MONTHS, w in WORKERS: RestReq[m,w] >= &mpi_min_rest_size.}:
			zApproved[m,w] * RestReq[m,w] <= RestFull[m,w];

		con cLinApproved2 {m in MONTHS, w in WORKERS: RestReq[m,w] >= &mpi_min_rest_size.}:
			- BigM * (1 - zApproved[m,w]) <= 1 - RestFull[m,w] / RestReq[m,w];		

		/** Целевая функция **/


		/* Минимизация отклонений от заявок сотрудников с учетом приоритетов */
		max Objective =
			  &mpi_order_weight * sum {m in MONTHS, w in WORKERS: RestReq[m,w] >= &mpi_min_rest_size.} zApproved[m,w] * OrderRate[m,w]
      		- &mpi_deviation_weight * sum {w in WORKERS} DifRestsHours[w];

		solve with milp / maxtime = 3600 nthreads = 32 decomp=(method=concomp);


		/** Выходные таблицы **/


		create data &mpo_work_hours. from [month worker qual] = {m in MONTHS, w in WORKERS, q in QUALS: QualFlg[w,q] = 1} 
		iWorkHours;

		create data &mpo_months_workers. from [month worker] = {m in MONTHS, w in WORKERS} 
		iRestHoursP1 iRestHoursP2;

		create data &mpo_personal_rest. from [worker month] = {w in WORKERS, m in MONTHS: iRestHours[m,w] > 0.5}
		  iRestHours = (iRestHoursP1[m,w] + iRestHoursP2[m,w])
		  Approved = (if RestReq[m,w] >= &mpi_min_rest_size. then zApproved[m,w] else 0)
		;

		create data &mpo_total_rests. from [worker] = {w in WORKERS}
		  RestCount = (sum {m in MONTHS} zStartFlg[m,w])
		  RestHours = (sum {m in MONTHS} iRestHours[m,w])
		  RestLeft = (max(&mpi_rest_year. - (sum {m in MONTHS} iRestHoursP1[m,w] + iRestHoursP2[m,w]),0))
		;

		create data &mpo_summary from [month] = {m in MONTHS}
		  RequiredSum = (sum {q in QUALS} Required[m,q])
		  WorkSum = (sum {w in WORKERS, q in QUALS: QualFlg[w,q] = 1} iWorkHours[m,w,q])
		  RestHours = (sum {w in WORKERS} iRestHours[m,w])
		  RestCount = (sum {w in WORKERS} zStartFlg[m,w])
		;
	quit;

%mend;


%optimization;







