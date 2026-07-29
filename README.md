<div align="center">

<img src="./ascii.svg" width="460" alt="Кирилл Силантьев"/>

<img src="./stats.svg" width="620" alt="Контрибуции за последний год"/>

[почта](mailto:kirill_silantev2@mail.ru) &nbsp;·&nbsp;
[github](https://github.com/NeverLucky-DS) &nbsp;·&nbsp;
[hub-ml.ru](https://hub-ml.ru)

</div>

<img src="./hd-about.svg" width="620" alt="о себе"/>

> Студент ПМИ Финансового университета. ML / Data Science, NLP, LLM.<br>
> Пайплайн целиком: от парсера до модели и до сервиса вокруг неё.

Собираю end-to-end: парсинг и ETL → фичи → CatBoost и классика → LLM-разметка<br>
и генерация. Когда модели нужен продакшен-контур, поднимаю его сам на FastAPI<br>
и PostgreSQL — так живёт [Closed_hub](https://hub-ml.ru). Открыт к стажировкам<br>
и проектам в ML / DS / NLP.

<img src="./hd-stack.svg" width="620" alt="стек"/>

<samp>python &nbsp; sql &nbsp; catboost &nbsp; scikit-learn &nbsp; pandas &nbsp; mistral &nbsp; fastapi &nbsp; postgres &nbsp; sqlalchemy &nbsp; playwright &nbsp; docker &nbsp; pytest &nbsp; uv</samp>

<img src="./hd-projects.svg" width="620" alt="проекты"/>

**[Cian](https://github.com/NeverLucky-DS/Cian)** &nbsp;·&nbsp; <samp>catboost, playwright, postgres</samp><br>
ML-пайплайн недвижимости: парсер → PostgreSQL → CatBoost на цену →<br>
LLM-скоринг «люксовости» → просмотрщик. Данные под DVC, дампы в Parquet.

**[wordlist-design](https://github.com/NeverLucky-DS/wordlist-design)** &nbsp;·&nbsp; <samp>fastapi, postgres, mistral</samp><br>
NLP-тренажёр немецкого: LLM разбирает эссе, отдельный pipeline добирает<br>
тематический словарь. Alembic-миграции, pytest с визуальными снапшотами.

**[Closed_hub](https://github.com/NeverLucky-DS/Closed_hub)** &nbsp;·&nbsp; [hub-ml.ru](https://hub-ml.ru) &nbsp;·&nbsp; <samp>fastapi, postgres, telegram</samp><br>
Платформа ML-сообщества: LLM-роутинг намерений, саммари событий,<br>
HR-extract из резюме. Телеграм-бот и веб — на одном бэкенде.

**[jobapply](https://github.com/NeverLucky-DS/jobapply)** &nbsp;·&nbsp; <samp>fastapi, mistral, playwright</samp><br>
LLM-агент для откликов на ML/DS вакансии: поиск → фильтр → cover letter<br>
от Mistral → отправка через Playwright.

<details>
<summary>прочее</summary>

- **[wb_parser](https://github.com/NeverLucky-DS/wb_parser)** — парсер и аналитика скидок Wildberries
- **[Style-transfer](https://github.com/NeverLucky-DS/Style-transfer)** — нейтрализация авторского стиля, параллельный корпус по Достоевскому

</details>

<img src="./hd-stats.svg" width="620" alt="статистика"/>

<div align="center">

<img src="./streak.svg" width="620" alt="Текущая и самая длинная серия"/>

<img src="./langs.svg" width="620" alt="Языки по объёму кода и по репозиториям"/>

<img src="./year.svg" width="620" alt="Последний год, один символ на день"/>

</div>

<img src="./hd-how.svg" width="620" alt="как это сделано"/>

Вся графика на странице сгенерирована, а не подтянута с чужого сервера.<br>
`ascii.svg` — аватарка, прогнанная через символьный рамп; цифры и заголовки<br>
рисует [ежедневный action](.github/workflows/profile.yml) прямо из GitHub GraphQL API<br>
и коммитит только то, что изменилось.

Ничего не захардкожено: логин берётся из `github.repository_owner`, аватарка<br>
качается во время прогона — портрет обновится сам, если я её сменю. Токен<br>
заводить не нужно, хватает встроенного `GITHUB_TOKEN`.

Анимация — SMIL внутри SVG, потому что скрипты из README GitHub вырезает.<br>
Заголовки разделов — картинки по той же причине: CSS он тоже вырезает, а иначе<br>
свой шрифт и цвет на них не поставить. Там, где SMIL не проигрывается, каждая<br>
анимация показывает готовый кадр, а не пустоту.

Шрифт не вшит: у каждого символа портрета и `year.svg` проставлена своя<br>
координата `x`, а не один `textLength` на строку — сетка не поедет от того,<br>
какой моноширинный шрифт стоит у читателя.

Языки считаются только по публичным репозиториям. `year.svg` использует<br>
тот же рамп, что и портрет: `·` `:` `+` `#` `@`, от тишины к грохоту.

<img src="./hd-contacts.svg" width="620" alt="контакты"/>

<samp>почта</samp> &nbsp;·&nbsp; [kirill_silantev2@mail.ru](mailto:kirill_silantev2@mail.ru)<br>
<samp>github</samp> &nbsp;·&nbsp; [NeverLucky-DS](https://github.com/NeverLucky-DS)
