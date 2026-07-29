"""Данные профиля из GitHub GraphQL API: календарь, стрики, языки.

Токен заводить не нужно: Action отдаёт встроенный GITHUB_TOKEN.
Если его прав не хватит, скрипт подхватит секрет PROFILE_TOKEN.
Приватные репозитории и приватные коммиты сюда не попадают —
у встроенного токена нет доступа к профилю от лица владельца.
"""

from __future__ import annotations

import datetime as dt
import os
from collections import Counter

import requests

API = "https://api.github.com/graphql"
TIMEOUT = 30


def token() -> str:
    for name in ("PROFILE_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(name)
        if value:
            return value
    raise SystemExit("нет токена: задайте GITHUB_TOKEN или PROFILE_TOKEN")


def gql(query: str, **variables):
    response = requests.post(
        API,
        json={"query": query, "variables": variables},
        headers={
            "Authorization": f"bearer {token()}",
            "User-Agent": "profile-graphics",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if "errors" in payload:
        raise SystemExit(f"GraphQL: {payload['errors']}")
    return payload["data"]


PROFILE_Q = """
query($login:String!){
  user(login:$login){
    login name createdAt
    followers{totalCount}
    contributionsCollection{contributionYears}
  }
}
"""

YEAR_Q = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar{
        totalContributions
        weeks{contributionDays{date contributionCount weekday}}
      }
    }
  }
}
"""

REPOS_Q = """
query($login:String!,$cursor:String){
  user(login:$login){
    repositories(first:100,after:$cursor,ownerAffiliations:OWNER,
                 isFork:false,privacy:PUBLIC,
                 orderBy:{field:PUSHED_AT,direction:DESC}){
      pageInfo{hasNextPage endCursor}
      nodes{
        name isArchived stargazerCount
        primaryLanguage{name color}
        languages(first:12,orderBy:{field:SIZE,direction:DESC}){
          edges{size node{name color}}
        }
      }
    }
  }
}
"""


def _window(year: int, created: dt.date, today: dt.date):
    start = max(dt.date(year, 1, 1), created)
    end = min(dt.date(year, 12, 31), today)
    return (
        f"{start.isoformat()}T00:00:00Z",
        f"{end.isoformat()}T23:59:59Z",
    )


def collect(login: str) -> dict:
    head = gql(PROFILE_Q, login=login)["user"]
    if head is None:
        raise SystemExit(f"пользователь {login} не найден")

    today = dt.datetime.now(dt.timezone.utc).date()
    created = dt.datetime.fromisoformat(
        head["createdAt"].replace("Z", "+00:00")
    ).date()

    days: dict[str, int] = {}
    for year in sorted(head["contributionsCollection"]["contributionYears"]):
        start, end = _window(year, created, today)
        block = gql(YEAR_Q, login=login, **{"from": start, "to": end})["user"][
            "contributionsCollection"
        ]
        for week in block["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                days[day["date"]] = day["contributionCount"]

    since = today - dt.timedelta(days=364)
    last = gql(
        YEAR_Q,
        login=login,
        **{
            "from": f"{since.isoformat()}T00:00:00Z",
            "to": f"{today.isoformat()}T23:59:59Z",
        },
    )["user"]["contributionsCollection"]
    weeks = [
        [(d["date"], d["contributionCount"]) for d in w["contributionDays"]]
        for w in last["contributionCalendar"]["weeks"]
    ]
    for week in weeks:
        for date, count in week:
            days.setdefault(date, count)

    repos, cursor = [], None
    while True:
        page = gql(REPOS_Q, login=login, cursor=cursor)["user"]["repositories"]
        repos.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    by_bytes: Counter = Counter()
    by_repo: Counter = Counter()
    colours: dict[str, str] = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            node = edge["node"]
            by_bytes[node["name"]] += edge["size"]
            if node.get("color"):
                colours[node["name"]] = node["color"]
        primary = repo["primaryLanguage"]
        if primary:
            by_repo[primary["name"]] += 1
            if primary.get("color"):
                colours[primary["name"]] = primary["color"]

    return {
        "login": head["login"],
        "name": head["name"] or head["login"],
        "created": created.isoformat(),
        "today": today.isoformat(),
        "followers": head["followers"]["totalCount"],
        "days": days,
        "weeks": weeks,
        "year": {
            "total": last["contributionCalendar"]["totalContributions"],
            "commits": last["totalCommitContributions"],
            "prs": last["totalPullRequestContributions"],
            "issues": last["totalIssueContributions"],
            "reviews": last["totalPullRequestReviewContributions"],
        },
        "streak": streaks(days, today),
        "langs_bytes": by_bytes.most_common(),
        "langs_repos": by_repo.most_common(),
        "lang_colours": colours,
        "repos": len(repos),
        "stars": sum(r["stargazerCount"] for r in repos),
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def streaks(days: dict[str, int], today: dt.date) -> dict:
    """Текущий и самый длинный стрик по всей истории аккаунта."""
    if not days:
        return {
            "current": 0,
            "current_from": None,
            "longest": 0,
            "longest_from": None,
            "longest_to": None,
            "total": 0,
        }

    dates = sorted(dt.date.fromisoformat(d) for d in days)
    first, last = dates[0], min(dates[-1], today)

    best = best_from = best_to = None
    run = 0
    run_from = None
    cursor = first
    step = dt.timedelta(days=1)
    while cursor <= last:
        if days.get(cursor.isoformat(), 0) > 0:
            run_from = run_from or cursor
            run += 1
            if best is None or run > best:
                best, best_from, best_to = run, run_from, cursor
        else:
            run, run_from = 0, None
        cursor += step

    # незакрытый сегодняшний день стрик не рвёт
    cursor = today
    if days.get(today.isoformat(), 0) == 0:
        cursor = today - step
    current, current_from = 0, None
    while days.get(cursor.isoformat(), 0) > 0:
        current += 1
        current_from = cursor
        cursor -= step

    return {
        "current": current,
        "current_from": current_from.isoformat() if current_from else None,
        "current_to": (
            today.isoformat()
            if days.get(today.isoformat(), 0) > 0
            else (today - step).isoformat()
        )
        if current
        else None,
        "longest": best or 0,
        "longest_from": best_from.isoformat() if best_from else None,
        "longest_to": best_to.isoformat() if best_to else None,
        "total": sum(days.values()),
    }
