# ramax

Репозиторий посвящен онлайн-хакатону по оптимизации ramax https://ramaximization.ru/.  
Данное решение заняло 1-ое место.

## Требования

Python 3.7.6

## Структура проекта
    1.Презентация: Presentation_no_constraints.pptx 
    2.Результаты оптимизации: data/Выходные данные/output_vacation.xlsx
    3.Код оптимизации: src/optimization.py
    4.Код Дэшборда визуализации: src/draw_dashboard.py

## Запуск Визуализации

    1. Установите python 3.7.6
    2. Создайте виртуальное окружение 
       python3 -m venv .venv # или {virtualenv .venv}
    3. Активируйте виртуальное окружение
       source .venv/bin/activate
    4. Установите requirements
       pip3 install -r requirements.txt
    5. Запустите src/draw_dashboard.py
    6. Дэшборд должен появиться в http://127.0.0.1:8050/
 
## Задача
Описание постановки задачи «Оптимизация назначения отпусков»

Цель
Написание модели, оптимизирующей назначение отпусков для данного набора сотрудников, исходя из заданного набора заданий и набора требований к назначению отпусков и заданий (бизнес-требования).
Постановка.
Требуется составить план отпусков на период планирования 12 месяцев для заданного набора сотрудников. Планирование производится в разрезе месяцев. Каждый сотрудник обладает набором квалификаций. В каждом месяце есть потребность в определенном количестве рабочих часов по каждой квалификации. Исходя из наличия сотрудников данной квалификации в каждом месяце и пределов их рабочей загрузки, надо распланировать распределение отпусков по месяцам для каждого отдельного сотрудника. Например, в месяце 3 по квалификации 1 задана нагрузка в 100 часов. При этом есть 3 сотрудника данной квалификации с лимитом в 80 часов для каждого. Максимально эти три сотрудника могут выполнить заданий на 240 часов. Но так как потребность в заданиях только 100 часов, то остается 140 часов, на которые можно запланировать некоторым или всем сотрудникам отпуска, суммарно не превосходящие это значение.
Входные данные.
Входные данные находятся в файле Отпуска_входные_данные.xlsx. Информация расположена по разделам (листам файла)
Params. Исходные параметры (объяснение параметров в разделе Бизнес-ограничения)
Quals. Набор квалификаций сотрудников. Один сотрудник может обладать несколькими квалификациями одновременно.
PersonalLevel. Список сотрудников с уникальными идентификаторами. Приоритеты сотрудников. Приоритет имеет значение при назначении отпусков с учетом пожеланий сотрудников.
Months. Список месяцев. Флаги (1/0) указания принадлежности месяцев к топовым/нетоповым (топовые – это, как правило, летние месяцы, в которые каждый хотел бы получить хотя бы один отпуск) . Допустимые максимальные размеры отпусков в данном месяце.
QualLevels. Относительный приоритет квалификаций. Имеет значение при дефиците сотрудников, при вычислении нехватки рабочих часов. В этом случае задания с более приоритетными квалификациями должны быть удовлетворены максимально полно за счет менее приоритетных квалификаций.
MaxFly. Максимальное количество рабочих часов в месяц для данного сотрудника.
Qualified. Матрица обладания квалификациями для каждого сотрудника (квалификации Х сотрудники).
RequiredPersonal. Потребность помесячно в сотрудниках данной квалификации (квалификации Х месяцы), в часах.
RestReq. Заявки сотрудников на отпуска по месяцам (сотрудники Х месяцы), в часах.
RestPrior. Приоритетность отпусков для сотрудников. Какие-то отпуска сотрудник желает получить именно в том месяце, на который подал заявку, а для каких-то отпусков допустим сдвиг.
Starts. Месяц, не ранее которого может назначаться первый отпуск сотруднику.
maxStarts. Месяц, не позднее которого может назначаться первый отпуск сотруднику.
Целевая функция.
Необходимо обеспечить 100% выполнение заданий по всем квалификациям (зарезервировать нужное количество часов по каждой квалификации в каждом месяце) и сообразно с оставшимся количеством часов максимизировать назначение отпусков для сотрудников согласно нижеописанным бизнес-требованиям.
Бизнес-ограничения.
Учет ведется в часах. Потребность в сотрудниках, лимиты рабочего времени, размеры отпусков.
Количество рабочего времени для каждого сотрудника не превосходит заданного для него лимита. При этом общее рабочее время за год не может превосходить его месячного лимита, умноженного на 10.
Время работы сотрудника может быть зарезервировано только по имеющейся у него квалификации-ям.
Оставшееся от работы время может быть использовано для назначения отпуска. Отпуск может попадать на границу между месяцами, но при этом меньшая часть  не может быть меньше 3 часов.
Каждому сотруднику должно быть назначено в течение года не более чем 4 отпуска (параметр TOTAL_RESTS). Минимальный размер отпуска в часах– параметр MIN_REST_SIZE. Суммарный максимальный объем отпусков в часах – параметр REST_YEAR.
Между отпусками не может быть разрыв менее заданного параметром MIN_REST_LAG, в месяцах. То есть, если первый отпуск планируется в месяц 1, то второй планируется не ранее чем в месяц 3.
Есть месяцы топовые и нетоповые (см Months). Количество отпусков в топовые месяцы не может превосходить 3 (параметр PRIOR_RESTS), в нетоповые месяцы также  не может превосходить 3 (параметр NOPRIOR_RESTS). При этом если отпуск начинается в топовый месяц, но продолжается в нетоповый, он считается назначенным в топовый месяц. Аналогичная ситуация и с нетоповыми отпусками.
Количество часов отпусков, назначенных в топовые месяцы, не может суммарно превосходить 147 часов (параметр REST_HIGH), в нетоповые месяцы действует аналогичное ограничение (параметр REST_LOW).
Необходимо учитывать приоритетность сотрудников и заявок. Для каждой заявки каждого сотрудника вычисляется ее рейтинг 
Рейтинг заявки = (4- RestPrior[p][m]) * (MAX_PERSONAL_LEVEL + 1) + PersonalLevel[p]
Где MAX_PERSONAL_LEVEL = max(PersonalLevel[p])			
Чем выше рейтинг заявки, тем приоритетней ее реализация для данного сотрудника в желаемый месяц.



