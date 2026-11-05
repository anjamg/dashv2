import json
import re
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from sqlalchemy import text
from sqlalchemy.orm import Session


SQL_DIR = Path(__file__).resolve().parents[1] / "sql" / "meteo"
LINE_GROUPS = {
    "SVI 1 & 2": ["SVI 1 Astreinte & Urgence", "SVI 2 Admin"],
    "SVI 3 & HP": ["SVI 3 Commercial", "Num HP Vitalliance", "Vitalliance SEA"],
}


def _effective_team_joins(alias: str, date_expression: str) -> str:
    return f"""
        LEFT JOIN users {alias}_u ON {alias}_u.username = {alias}.user
        LEFT JOIN (
            SELECT user_id, MIN(from_date) AS first_from_date
            FROM team_memberships
            GROUP BY user_id
        ) {alias}_tm_first ON {alias}_tm_first.user_id = {alias}_u.id
        LEFT JOIN team_memberships {alias}_tm
            ON {alias}_tm.user_id = {alias}_u.id
           AND {alias}_tm.from_date <= {date_expression}
           AND ({alias}_tm.to_date IS NULL OR {alias}_tm.to_date >= {date_expression})
    """


def _effective_team_expression(alias: str, date_expression: str) -> str:
    return (
        f"CASE WHEN {alias}_tm_first.first_from_date IS NOT NULL "
        f"AND {date_expression} >= {alias}_tm_first.first_from_date "
        f"THEN {alias}_tm.team_name ELSE {alias}.team_name END"
    )


def _apply_effective_team_sql(sql: str) -> str:
    def replace_match(match: re.Match[str]) -> str:
        alias, team_name = match.group(1), match.group(2)
        return (
            f"FROM data {alias}\n"
            f"{_effective_team_joins(alias, f'{alias}.date_only')}\n"
            f"WHERE {_effective_team_expression(alias, f'{alias}.date_only')} = '{team_name}'"
        )

    return re.sub(
        r"FROM data (d|agent|busy)\s+WHERE \1\.team_name = '(N2|Suivi Qualité)'",
        replace_match,
        sql,
    )


def _read_sql(filename: str) -> str:
    return _apply_effective_team_sql((SQL_DIR / filename).read_text(encoding="utf-8"))


def _execute(db: Session, filename: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    result = db.execute(text(_read_sql(filename)), params).mappings()
    return [dict(row) for row in result]


def _bind_values(values: list[str], prefix: str) -> tuple[str, dict[str, str]]:
    params = {f"{prefix}_{index}": value for index, value in enumerate(values)}
    placeholders = ", ".join(f":{key}" for key in params)
    return placeholders, params


def _int(value: Any) -> int:
    return int(value or 0)


def _safe_name(value: Any) -> str:
    if not value:
        return "—"
    name = re.sub(r"^Niveau\s*2\s*-\s*", "", str(value).strip(), flags=re.IGNORECASE)
    name = re.sub(r"^Vitalliance\s*-\s*", "", name, flags=re.IGNORECASE)
    return name.strip() or "—"


def _percentage_comment(label: str, rate: float) -> str:
    percent = rate * 100
    formatted = f"{percent:,.1f}".replace(",", " ").replace(".", ",") + " %"
    if percent >= 85:
        return f"{label} : excellent taux de décro à {formatted}."
    if percent >= 75:
        return f"{label} : taux de décro correct mais à surveiller à {formatted}."
    return f"{label} : taux de décro faible à {formatted}, point de vigilance."


def _recap(db: Session, date_from: date, date_to: date) -> dict[str, Any]:
    result: dict[str, Any] = {"by_team": [], "by_agent": {}}
    for label, lines in LINE_GROUPS.items():
        line_placeholders_1, params_1 = _bind_values(lines, "line1")
        line_placeholders_2, params_2 = _bind_values(lines, "line2")
        team_sql = _read_sql("meteo_recap_team.sql")
        team_sql = team_sql.replace(":lines1", line_placeholders_1).replace(":lines2", line_placeholders_2)
        team_sql = re.sub(r"GROUP BY d\.line\s*ORDER BY d\.line", "", team_sql)
        team_params = {
            **params_1,
            **params_2,
            "df1": date_from,
            "dt1": date_to,
            "df2": date_from,
            "dt2": date_to,
        }
        team_row = db.execute(text(team_sql), team_params).mappings().first() or {}
        prises = _int(team_row.get("pris"))
        sortants = _int(team_row.get("sortants"))
        rebasculees = _int(team_row.get("rebascules"))
        total = prises + sortants
        effectifs = float(team_row.get("effectifs") or 0)
        denominator = prises + rebasculees
        result["by_team"].append({
            "equipe": label,
            "abandonnes": _int(team_row.get("abandonnes")),
            "rebascules": rebasculees,
            "pris": prises,
            "sortants": sortants,
            "total_traites": total,
            "effectifs": effectifs,
            "calls_effectif": round(total / effectifs, 2) if effectifs else 0,
            "taux_decro": round(prises / denominator, 4) if denominator else 0,
        })

        agent_placeholders, agent_params = _bind_values(lines, "line")
        agent_sql = _read_sql("meteo_recap_agents.sql").replace(":lines", agent_placeholders)
        result["by_agent"][label] = [
            dict(row) for row in db.execute(
                text(agent_sql), {**agent_params, "df": date_from, "dt": date_to}
            ).mappings()
        ]
    return result


def _n2_report(db: Session, date_from: date, date_to: date) -> dict[str, Any]:
    params = {"df": date_from, "dt": date_to}
    global_rows = _execute(db, "meteo_n2_global.sql", params)
    agents = _execute(db, "meteo_n2_agents.sql", params)
    global_stats = global_rows[0] if global_rows else {}
    return {
        "global": {
            **global_stats,
            **{
                key: _int(global_stats.get(key))
                for key in (
                    "total_appels", "pris", "sortants", "rebascules", "abandonnes",
                    "hors_horaires", "nb_agents", "devis_ok", "devis_ko",
                )
            },
            "taux_reponse": float(global_stats.get("taux_reponse") or 0),
        },
        "agents": agents,
    }


SQ_FIELD_MAP = {
    "appeles": "appeles",
    "appels_entrants": "appels_entrants",
    "decroches": "decroches",
    "client_total": "nb_client",
    "adv_total": "nb_adv",
    "client_inj": "client_inj",
    "client_decro": "client_decro",
    "client_entrants": "client_entrants",
    "adv_entrants": "adv_entrants",
    "adv_inj": "adv_inj",
    "adv_decro": "adv_decro",
    "injoignable": "nb_injoignable",
    "questions_ok": "nb_questions_ok",
    "bilan_positif": "nb_bilan_positif",
    "bilan_mitige": "nb_bilan_mitige",
    "bilan_negatif": "nb_bilan_negatif",
    "sm_client_positif": "sm_client_positif",
    "sm_client_inj2": "sm_client_inj2",
    "sm_client_mitige": "sm_client_mitige",
    "sm_client_negatif": "sm_client_negatif",
    "qs_client_positif": "qs_client_positif",
    "qs_client_inj2": "qs_client_inj2",
    "qs_client_mitige": "qs_client_mitige",
    "qs_client_negatif": "qs_client_negatif",
    "sm_adv_positif": "sm_adv_positif",
    "sm_adv_inj2": "sm_adv_inj2",
    "sm_adv_mitige": "sm_adv_mitige",
    "sm_adv_negatif": "sm_adv_negatif",
    "a_rappeler": "nb_a_rappeler",
    "interrompu": "nb_interrompu",
    "autre": "nb_autres",
    "ras": "nb_ras",
    "prime_participation": "nb_prime_participation",
}


def _sq_report(db: Session, date_from: date, date_to: date) -> dict[str, Any]:
    params = {"df": date_from, "dt": date_to}
    global_rows = _execute(db, "meteo_sq_global.sql", params)
    agents = _execute(db, "meteo_sq_agents.sql", params)
    stats = global_rows[0] if global_rows else {}
    totals = {key: _int(stats.get(source)) for key, source in SQ_FIELD_MAP.items()}
    client_adv = totals["client_total"] + totals["adv_total"]
    totals["joignabilite"] = (
        round((client_adv - totals["injoignable"]) / client_adv, 4) if client_adv else 0
    )
    return {"global": stats, "agents": agents, "totaux": totals}


def _business_comments(
    db: Session,
    date_from: date,
    date_to: date,
    recap: dict[str, Any],
    n2_report: dict[str, Any],
) -> dict[str, Any]:
    params = {
        "df_busy": date_from, "dt_busy": date_to,
        "df_agents": date_from, "dt_agents": date_to,
        "df_missed": date_from, "dt_missed": date_to,
        "df_tags": date_from, "dt_tags": date_to,
        "df_rebasc": date_from, "dt_rebasc": date_to,
    }
    rows = _execute(db, "meteo_n2_business_comments.sql", params)
    stats = rows[0] if rows else {}
    rebascules = _int(stats.get("rebascules"))
    pause = _int(stats.get("rebascules_pause"))
    agent_busy = _int(stats.get("rebascules_agent_en_appel"))
    could_answer = _int(stats.get("rebascules_auraient_pu_etre_pris"))
    pris = _int(n2_report["global"].get("pris"))
    prospects_ok = _int(stats.get("prospects_ok_tag")) or _int(stats.get("devis_ok"))
    incoming = _int(stats.get("appels_entrants"))
    tag_lines = []
    for key, label in (
        ("cdn", "chez CDN"), ("harisoa", "chez Harisoa"), ("tchats", "tchats"),
        ("as_rappel", "AS avec rappel agence"), ("transfert_n1", "transferts N1"),
        ("deb_n2", "DEB-N2"), ("non_deb", "non DEB"),
    ):
        value = _int(stats.get(key))
        if value > 0:
            tag_lines.append(f"{value} {label}")

    potential_calls = stats.get("potential_calls") or "[]"
    if isinstance(potential_calls, str):
        potential_calls = json.loads(potential_calls)
    potential_calls = [
        call for call in potential_calls or []
        if isinstance(call, dict) and call.get("id")
    ]

    return {
        "n2": {
            "metrics": {
                "appels_entrants": incoming,
                "prospects_ok": prospects_ok,
                "rebascules": rebascules,
                "rebascules_agent_en_appel": agent_busy,
                "rebascules_auraient_pu_etre_pris": could_answer,
                "rebascules_pause": pause,
            },
            "lines": [
                f"{incoming + rebascules} appels entrants dont {could_answer + pris} auraient pu être pris.",
                f"{pris} décrochés : {_int(stats.get('devis_ok'))} DEVIS OK et {_int(stats.get('devis_ko'))} DEVIS KO.",
                f"{rebascules} rebasculés dont:",
                f"{agent_busy} pendant que l’agent était en appel.",
                f"{could_answer} que l’agent aurait pu prendre.",
                f"{pause} pendant la pause déjeuner N2 (12h-13h).",
            ],
            "tag_lines": tag_lines,
            "potential_calls": potential_calls,
        },
        "svi": {
            "lines": [
                _percentage_comment(team["equipe"], float(team.get("taux_decro") or 0))
                for team in recap.get("by_team", [])
            ],
        },
    }


def build_report(db: Session, date_from: date, date_to: date) -> dict[str, Any]:
    next_date = date_to + timedelta(days=1)
    recap = _recap(db, date_from, date_to)
    n2 = _n2_report(db, date_from, date_to)
    sq = _sq_report(db, date_from, date_to)
    comments = _business_comments(db, date_from, date_to, recap, n2)

    absences = [
        dict(row) for row in db.execute(text("""
            SELECT lr.user_id, COALESCE(u.agent_name, u.username) AS agent_name,
                   lt.code,
                   CASE WHEN lt.code = 'sick'
                        THEN 'Arrêt maladie/Assistance maternelle' ELSE lt.name END AS type_name,
                   lr.start_period, lr.end_period, lr.reason
            FROM leave_requests lr
            JOIN users u ON u.id = lr.user_id
            JOIN leave_types lt ON lt.id = lr.leave_type_id
            WHERE lr.status = 'approved'
              AND lr.start_date <= :report_date
              AND lr.end_date >= :report_date
            ORDER BY COALESCE(u.agent_name, u.username)
        """), {"report_date": next_date}).mappings()
    ]
    absent_user_ids = {int(row["user_id"]) for row in absences}
    members = db.execute(text("""
        SELECT tm.user_id, tm.team_name, u.username, u.username AS agent_name
        FROM team_memberships tm
        JOIN users u ON u.id = tm.user_id
        WHERE tm.from_date <= :report_date
          AND (tm.to_date IS NULL OR tm.to_date >= :report_date)
        ORDER BY tm.team_name, agent_name, u.username
    """), {"report_date": next_date}).mappings()
    organization: dict[str, list[str]] = {}
    for member in members:
        if int(member["user_id"]) in absent_user_ids:
            continue
        name = _safe_name(member.get("agent_name") or member.get("username"))
        if name == "—":
            continue
        first_name = name.split()[0].capitalize()
        organization.setdefault(member.get("team_name") or "Sans équipe", []).append(first_name)

    note_row = db.execute(text(
        "SELECT organization_text FROM meteo_daily_notes WHERE report_date = :report_date LIMIT 1"
    ), {"report_date": next_date}).mappings().first()
    return {
        "date_from": date_from,
        "date_to": date_to,
        "note_date": next_date,
        "recap": recap,
        "n2": n2,
        "sq": sq,
        "comments": comments,
        "absences": absences,
        "organization": organization,
        "organization_note": (note_row or {}).get("organization_text") or "",
    }


def create_excel_report(report: dict[str, Any]) -> bytes:
    workbook = Workbook()
    overview = workbook.active
    overview.title = "Météo"
    overview.append(["Rapport Météo", report["date_from"], report["date_to"]])
    overview.append(["N2", "Indicateur", "Valeur"])
    overview.append(["N2", "Total appels", report["n2"]["global"]["total_appels"]])
    overview.append(["N2", "Pris", report["n2"]["global"]["pris"]])
    overview.append(["N2", "Sortants", report["n2"]["global"]["sortants"]])
    overview.append(["N2", "Rebasculés", report["n2"]["global"]["rebascules"]])
    overview.append(["N2", "Abandonnés", report["n2"]["global"]["abandonnes"]])
    overview.append(["N2", "Taux réponse (%)", report["n2"]["global"]["taux_reponse"]])
    overview.append([])
    overview.append(["SVI", "Équipe", "Abandonnés", "Rebasculés", "Pris", "Sortants", "Total traités", "ETP", "Calls/agent", "Taux décro"])
    for team in report["recap"]["by_team"]:
        overview.append([
            "SVI", team["equipe"], team["abandonnes"], team["rebascules"], team["pris"],
            team["sortants"], team["total_traites"], team["effectifs"],
            team["calls_effectif"], team["taux_decro"],
        ])

    _append_excel_table(
        workbook, "Agents N2", ["Agent", "Total", "Pris", "Sortants", "Rebasculés", "Durée totale", "Durée moyenne"],
        [[
            _safe_name(row.get("user")), row.get("total"), row.get("pris"), row.get("sortants"),
            row.get("rebascules"), row.get("total_incall"), row.get("avg_incall"),
        ] for row in report["n2"]["agents"]],
    )
    for label, agents in report["recap"]["by_agent"].items():
        safe_label = "SVI " + ("1-2" if label == "SVI 1 & 2" else "3-HP")
        _append_excel_table(
            workbook, safe_label, ["Agent", "Pris", "Sortants", "Total", "Temps total appel"],
            [[_safe_name(row.get("user")), row.get("pris"), row.get("sortants"), row.get("total"), row.get("total_incall")]
             for row in agents],
        )
    _append_excel_table(
        workbook, "SQ conseillers",
        ["Conseiller", "Appelés", "Entrants", "Clients", "ADV", "Autres", "RAS", "Injoignables", "Questions OK", "Temps total", "Joignabilité"],
        [[
            _safe_name(row.get("user")), row.get("appeles"), row.get("appels_entrants"),
            row.get("nb_client"), row.get("nb_adv"), row.get("nb_autres"), row.get("nb_ras"),
            row.get("nb_injoignable"), row.get("nb_questions_ok"), row.get("total_incall"),
            row.get("joignabilite"),
        ] for row in report["sq"]["agents"]],
    )
    _append_excel_table(
        workbook, "Absences",
        ["Agent", "Type", "Début", "Fin", "Motif"],
        [[row.get("agent_name"), row.get("type_name"), row.get("start_period"), row.get("end_period"), row.get("reason")]
         for row in report["absences"]],
    )
    sq_totals = report["sq"]["totaux"]
    _append_excel_table(
        workbook, "SQ synthèse", ["Indicateur", "Valeur"],
        [[key.replace("_", " "), value] for key, value in sq_totals.items()],
    )
    comment_rows = [
        ["Commentaires N2", line] for line in report["comments"]["n2"]["lines"]
    ] + [
        ["Tags N2", line] for line in report["comments"]["n2"]["tag_lines"]
    ] + [
        ["Commentaires SVI", line] for line in report["comments"]["svi"]["lines"]
    ]
    _append_excel_table(workbook, "Commentaires", ["Section", "Commentaire"], comment_rows)
    _append_excel_table(
        workbook, "Appels à prendre",
        ["Date / heure", "Ligne", "N° client", "Motif", "Agents présents", "Agents occupés"],
        [[
            row.get("datetime"), row.get("line"), row.get("customer_number"),
            row.get("missed_call_reason"), row.get("agents_present"), row.get("agents_busy"),
        ] for row in report["comments"]["n2"]["potential_calls"]],
    )
    organization_rows = [
        [team, " + ".join(members)] for team, members in report["organization"].items()
    ]
    organization_rows.append(["Note complémentaire", report["organization_note"]])
    _append_excel_table(workbook, "Organisation", ["Équipe", "Organisation"], organization_rows)
    for worksheet in workbook.worksheets:
        for row in worksheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith(("=", "+", "-", "@")):
                    cell.value = "'" + cell.value
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _append_excel_table(
    workbook: Workbook,
    title: str,
    headers: list[str],
    rows: list[list[Any]],
) -> None:
    worksheet = workbook.create_sheet(title=title)
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
