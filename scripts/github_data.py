"""Данные профиля из GitHub GraphQL API: календарь контрибуций за год.

Токен заводить не нужно: Action отдаёт встроенный GITHUB_TOKEN.
Если его прав не хватит, скрипт подхватит секрет PROFILE_TOKEN.
Приватные коммиты сюда не попадают — у встроенного токена нет доступа
к профилю от лица владельца.
"""

from __future__ import annotations

import datetime as dt
import os

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
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    login name createdAt
    followers{totalCount}
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


def collect(login: str) -> dict:
    today = dt.datetime.now(dt.timezone.utc).date()
    since = today - dt.timedelta(days=364)

    user = gql(
        PROFILE_Q,
        login=login,
        **{
            "from": f"{since.isoformat()}T00:00:00Z",
            "to": f"{today.isoformat()}T23:59:59Z",
        },
    )["user"]
    if user is None:
        raise SystemExit(f"пользователь {login} не найден")

    block = user["contributionsCollection"]
    weeks = [
        [(d["date"], d["contributionCount"]) for d in w["contributionDays"]]
        for w in block["contributionCalendar"]["weeks"]
    ]

    return {
        "login": user["login"],
        "name": user["name"] or user["login"],
        "created": dt.datetime.fromisoformat(
            user["createdAt"].replace("Z", "+00:00")
        )
        .date()
        .isoformat(),
        "today": today.isoformat(),
        "followers": user["followers"]["totalCount"],
        "weeks": weeks,
        "year": {
            "total": block["contributionCalendar"]["totalContributions"],
            "commits": block["totalCommitContributions"],
            "prs": block["totalPullRequestContributions"],
            "issues": block["totalIssueContributions"],
            "reviews": block["totalPullRequestReviewContributions"],
        },
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
