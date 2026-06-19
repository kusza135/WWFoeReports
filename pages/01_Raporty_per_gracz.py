import streamlit as st
import altair as alt
from tools.streamlit_tools import execute_query, page_header, get_world_id, get_guild_id
from tools.login import login, check_user_role_permissions

# ---------------------------------------------------------------------------
# WARSTWA DANYCH — cache, zero UI, parametryzowane zapytania
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_player_list() -> list:
    """Lista graczy do filtra — cache 1h, zmienia sie rzadko."""
    df = execute_query(
        """SELECT DISTINCT player_id, name AS Player_name
           FROM V_GUILD_PLAYERS
           ORDER BY Player_name
        """,
        return_type="df",
    )
    return df


@st.cache_data(ttl=1800)
def get_player_activity() -> object:
    """Aktywnosc wszystkich graczy gildii z 30 dni — filtrowanie po playerId w pamięci."""
    return execute_query(
        """SELECT
                world, playerId, name,
                points AS `Punty rankingowe`,
                battles AS `Liczba bitew`,
                pointsDif AS `Roznica punktow rankingowych`,
                battlesDif AS `Roznica bitew`,
                CAST(DATE_ADD(valid_from, INTERVAL -1 DAY) AS CHAR) AS Data_danych,
                CASE WHEN f_gpch_day(DATE_ADD(valid_from, INTERVAL -1 DAY)) > 0
                     THEN 500 ELSE 0 END AS GPCh
            FROM V_ALL_PLAYERS
            WHERE world = :world
              AND valid_from > DATE_ADD(CURRENT_DATE(), INTERVAL -30 DAY)
              AND ClanId = :guild_id
        """,
        params={"world": get_world_id(), "guild_id": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=1800)
def get_wg_stats() -> object:
    """Statystyki WG — tylko zakonczone edycje + pierwsza edycja."""
    return execute_query(
        """SELECT
                player_id, CAST(report_date AS CHAR) AS Report_date,
                name AS Player_name, Age_PL AS Epoka,
                wg_date_of_day AS WG_day, expeditionPoints,
                solvedEncounters AS Wygrane_bitwy,
                WG_LEVEL, currentTrial AS Proba, forecast
            FROM V_WG
            WHERE wg_date_of_day = 0
              AND world = :world AND guild_id = :guild_id
            UNION ALL
            SELECT
                player_id, CAST(a.report_date AS CHAR) AS Report_date,
                name AS Player_name, Age_PL AS Epoka,
                wg_date_of_day AS WG_day, expeditionPoints,
                solvedEncounters AS Wygrane_bitwy,
                WG_LEVEL, currentTrial AS Proba, forecast
            FROM V_WG a
            INNER JOIN (
                SELECT MIN(report_date) AS report_date
                FROM V_WG WHERE world = :world AND guild_id = :guild_id
            ) c ON a.report_date = c.report_date
            WHERE a.world = :world AND a.guild_id = :guild_id
        """,
        params={"world": get_world_id(), "guild_id": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=1800)
def get_gpch_stats() -> object:
    """Statystyki GPCh — tylko zakonczone edycje + pierwsza edycja."""
    return execute_query(
        """SELECT
                player_id, CAST(report_date AS CHAR) AS Report_date,
                name AS Player_name, Age_PL AS Epoka,
                GPCH_DATE_OF_DAY AS GPCH_day, `RANK`,
                battlesWon AS Wygrane_bitwy,
                negotiationsWon AS Wygrane_negocjacje,
                score, Forecast
            FROM V_GPCH
            WHERE GPCH_DATE_OF_DAY = 0
              AND world = :world AND guild_id = :guild_id
            UNION ALL
            SELECT
                player_id, CAST(a.report_date AS CHAR) AS Report_date,
                name AS Player_name, Age_PL AS Epoka,
                GPCH_DATE_OF_DAY AS GPCH_day, `RANK`,
                battlesWon AS Wygrane_bitwy,
                negotiationsWon AS Wygrane_negocjacje,
                score, Forecast
            FROM V_GPCH a
            INNER JOIN (
                SELECT MIN(report_date) AS report_date
                FROM V_GPCH WHERE world = :world AND guild_id = :guild_id
            ) c ON a.report_date = c.report_date
            WHERE a.world = :world AND a.guild_id = :guild_id
        """,
        params={"world": get_world_id(), "guild_id": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=1800)
def get_nk_stats() -> object:
    """Statystyki NK — tylko zakonczone edycje + pierwsza edycja."""
    return execute_query(
        """SELECT DISTINCT player_id,
                CAST(report_date AS CHAR) AS Report_date,
                name AS Player_name, Age_PL AS Epoka,
                NK_DATE_OF_DAY AS NK_day,
                progressContribution AS Postep,
                actionPoints AS Dzialania
            FROM V_NK
            WHERE NK_DATE_OF_DAY = 0
              AND world = :world AND guild_id = :guild_id
            UNION ALL
            SELECT DISTINCT player_id,
                CAST(a.report_date AS CHAR) AS Report_date,
                name AS Player_name, Age_PL AS Epoka,
                NK_DATE_OF_DAY AS NK_day,
                progressContribution AS Postep,
                actionPoints AS Dzialania
            FROM V_NK a
            INNER JOIN (
                SELECT MIN(report_date) AS report_date
                FROM V_NK WHERE world = :world AND guild_id = :guild_id
            ) c ON a.report_date = c.report_date
            WHERE a.world = :world AND a.guild_id = :guild_id
        """,
        params={"world": get_world_id(), "guild_id": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=1800)
def get_guild_player_history() -> object:
    return execute_query(
        """SELECT
                a.player_id, a.`rank`, a.name AS Player_name,
                a.score, a.won_battles, a.Age_PL AS Epoka,
                title,
                CASE permissions
                    WHEN 126 THEN 'Zarzadzanie GPCh'
                    WHEN 127 THEN 'Zarzadzanie Gildia'
                END AS Uprawnienia,
                Join_date, leave_date, valid_from, valid_to
            FROM V_GUILD_PLAYERS a
            ORDER BY Valid_from
        """,
        return_type="df",
    )


@st.cache_data(ttl=1800)
def get_notes() -> object:
    return execute_query(
        """SELECT player_id, Player_name, notka
           FROM (
               SELECT a.player_id, a.name AS Player_name, notka,
                      ROW_NUMBER() OVER (PARTITION BY a.player_id ORDER BY VALID_TO DESC) AS RN
               FROM V_GUILD_PLAYERS a
               WHERE notka IS NOT NULL
           ) x
           WHERE RN = 1
        """,
        return_type="df",
    )


@st.cache_data(ttl=1800)
def get_nick_changes() -> object:
    return execute_query(
        """SELECT GP.player_id, GP.name AS OLD_NAME, VAP.name AS CURRENT_NAME
           FROM (
               SELECT player_id, name,
                      ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY valid_to DESC) AS rn
               FROM V_GUILD_PLAYERS
           ) GP
           INNER JOIN V_ALL_PLAYERS VAP
               ON GP.player_id = VAP.PLAYERID AND rn = 1
           WHERE VAP.VALID_TO = '3000-12-31'
             AND VAP.WORLD = :world
             AND GP.name <> VAP.name
        """,
        params={"world": get_world_id()},
        return_type="df",
    )


# ---------------------------------------------------------------------------
# HELPERY
# ---------------------------------------------------------------------------

def add_note(player_id: int, note: str) -> None:
    execute_query(
        "CALL p_notes(:player_id, :note)",
        params={"player_id": player_id, "note": note},
        return_type="df",
    )
    get_notes.clear()
    get_guild_player_history.clear()
    st.toast("Dane zapisane", icon="✅")


# ---------------------------------------------------------------------------
# FILTR GRACZY
# ---------------------------------------------------------------------------

def filter_setup() -> list:
    df = get_player_list()
    selected = st.multiselect(
        "Wybierz nick gracza",
        df.Player_name.sort_values().unique(),
        max_selections=4,
        placeholder="Rozwij lub zacznij wpisywac",
    )
    if not selected:
        return []
    return df.loc[df["Player_name"].isin(selected), "player_id"].tolist()


# ---------------------------------------------------------------------------
# SEKCJE UI — kazda jako @st.fragment
# ---------------------------------------------------------------------------

@st.fragment
def section_nick_changes(filters: list) -> None:
    if not filters:
        return
    df = get_nick_changes()
    changed = df[df["player_id"].isin(filters)]
    for _, row in changed.iterrows():
        st.info(
            f"Gracz **{row['OLD_NAME']}** zmienil nick na **{row['CURRENT_NAME']}**",
            icon="ℹ️",
        )


@st.fragment
def section_notes(filters: list) -> None:
    if not filters:
        return
    df = get_notes()
    player_notes = df[df["player_id"].isin(filters)]
    for _, row in player_notes.iterrows():
        st.warning(
            f"Gracz **{row['Player_name']}** ma zapisana notatke:\n\n{row['notka']}\n",
            icon="⚠️",
        )


def _activity_chart(df, metric: str) -> alt.Chart:
    line = (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=25))
        .encode(
            x=alt.X("Data_danych", title="Data danych"),
            y=alt.Y(metric, title=metric),
            color=alt.Color("name:N", legend=alt.Legend(orient="none", legendX=450, legendY=-47, direction="horizontal", titleAnchor="middle")),
            tooltip=metric,
        )
        .properties(title="Historia gry z ostatnich 30 dni", height=450)
    )
    ticks = alt.Chart(df).mark_tick(color="purple", thickness=2, size=18).encode(x="Data_danych", y="GPCh").properties(title="dzien GPCh")
    labels = line.mark_text(align="center", baseline="top", color="black", fontSize=13, dy=-30).encode(text=f"{metric}:Q")
    return (line + ticks + labels).interactive()


@st.fragment
def section_activity(filters: list) -> None:
    if not filters:
        st.info("Wybierz gracza w filtrze powyzej.")
        return
    df_all = get_player_activity()
    df = df_all[df_all["playerId"].isin(filters)]
    if df.empty:
        st.warning("Brak danych aktywnosci dla wybranych graczy.")
        return
    metric = st.radio("Wybierz metryki:", options=["Punty rankingowe", "Liczba bitew", "Roznica punktow rankingowych", "Roznica bitew"], horizontal=True, index=3)
    st.altair_chart(_activity_chart(df, metric), width="stretch")


def _wg_chart(df) -> alt.Chart:
    base = (
        alt.Chart(df).mark_bar(strokeWidth=1)
        .encode(x=alt.X("Report_date:N", axis=alt.Axis(title="Data zakonczenia WG", labelAngle=5)),
                y="Wygrane_bitwy:Q", xOffset="Player_name:N", color="Player_name:N",
                tooltip=["Player_name:N", "Report_date", "Epoka", "WG_LEVEL", "Wygrane_bitwy", "Proba"])
        .properties(title="Statystyka wszystkich edycji WG gracza/y", width=alt.Step(10))
        .interactive()
    )
    return base + base.mark_text(align="center", baseline="top", color="black", dy=-30).encode(text="Player_name:N")


@st.fragment
def section_wg(filters: list) -> None:
    if not filters:
        return
    df_all = get_wg_stats()
    df = df_all[df_all["player_id"].isin(filters)]
    if df.empty:
        st.warning("Brak danych WG dla wybranych graczy.")
        return
    st.altair_chart(_wg_chart(df), theme=None, width="stretch")


def _gpch_chart(df) -> alt.Chart:
    base = (
        alt.Chart(df).mark_bar(strokeWidth=1)
        .encode(x=alt.X("Report_date:N", axis=alt.Axis(title="Data zakonczenia GPCh", labelAngle=5)),
                y=alt.Y("score:Q", axis=alt.Axis(title="Wynik walk i nego", labelAngle=5)),
                xOffset="Player_name:N", color="Player_name:N",
                tooltip=["Player_name:N", "Report_date", "Epoka", "Wygrane_bitwy:Q", "Wygrane_negocjacje:Q"])
        .properties(title="Statystyka wszystkich edycji GPCh gracza/y", height=300, width=alt.Step(3))
        .interactive()
    )
    return base + base.mark_text(align="center", baseline="top", color="black", dy=-30).encode(text="Player_name:N")


@st.fragment
def section_gpch(filters: list) -> None:
    if not filters:
        return
    df_all = get_gpch_stats()
    df = df_all[df_all["player_id"].isin(filters)]
    if df.empty:
        st.warning("Brak danych GPCh dla wybranych graczy.")
        return
    st.altair_chart(_gpch_chart(df), theme=None, width="stretch")


def _nk_chart(df) -> alt.Chart:
    base = (
        alt.Chart(df).mark_bar(strokeWidth=1)
        .encode(x=alt.X("Report_date:N", axis=alt.Axis(title="Data zakonczenia Najazdow Kwantowych", labelAngle=5)),
                y=alt.Y("Postep:Q", axis=alt.Axis(title="Postep", labelAngle=5)),
                xOffset="Player_name:N", color="Player_name:N",
                tooltip=["Player_name:N", "Report_date", "Epoka", "Postep:Q", "Dzialania:Q"])
        .properties(title="Statystyka wszystkich edycji Najazdow Kwantowych gracza/y", height=300, width=alt.Step(3))
        .interactive()
    )
    return base + base.mark_text(align="center", baseline="top", color="black", dy=-30).encode(text="Player_name:N")


@st.fragment
def section_nk(filters: list) -> None:
    if not filters:
        return
    df_all = get_nk_stats()
    df = df_all[df_all["player_id"].isin(filters)]
    if df.empty:
        st.warning("Brak danych NK dla wybranych graczy.")
        return
    st.altair_chart(_nk_chart(df), theme=None, width="stretch")


def _add_note_form(df_all) -> None:
    col1, col2, _ = st.columns([5, 10, 5])
    nickname = col1.selectbox("Wyznacz gracza", index=None, options=df_all["Player_name"].sort_values().unique(), label_visibility="hidden")
    if not nickname:
        return
    pid = df_all.loc[df_all["Player_name"] == nickname, "player_id"].values[0]
    notka = col2.text_input("Wpisz krotka notke", placeholder="Wpisz krotka notke", label_visibility="hidden")
    st.button("Zapisz", on_click=add_note, args=(pid, notka), disabled=not notka, type="primary")


@st.fragment
def section_guild_history(filters: list) -> None:
    df_all = get_guild_player_history()
    with st.expander("Dodaj notatke graczowi", expanded=True):
        _add_note_form(df_all)
    if filters:
        st.dataframe(df_all[df_all["player_id"].isin(filters)], width="stretch", hide_index=True)
    else:
        st.info("Wybierz gracza w filtrze powyzej aby zobaczyc jego historie.")


# ---------------------------------------------------------------------------
# GLOWNA FUNKCJA
# ---------------------------------------------------------------------------

def run_reports() -> None:
    st.subheader("Postepy Graczy", anchor="PostepyGraczy")

    # Filtr — multiselect, nie trafia do bazy przy kazdym rerenderze
    filters = filter_setup()

    # Kazdna sekcja to osobny @st.fragment —
    # zmiana filtra rerenderuje cala strone ale kazda sekcja
    # pobiera dane z cache, wiec tylko renderowanie jest kosztem
    section_nick_changes(filters)
    section_notes(filters)

    st.subheader("Historia aktywnosci z ostatnich 30 dni", anchor="activity", divider="rainbow")
    section_activity(filters)

    st.subheader("Wyprawy Gildyjne", anchor="wg", divider="rainbow")
    section_wg(filters)

    st.subheader("Gildyjne Pola Chwaly", anchor="gpch", divider="rainbow")
    section_gpch(filters)

    st.subheader("Najazdy Kwantowe", anchor="nk", divider="rainbow")
    section_nk(filters)

    st.subheader("Historia zmian w Gildii", anchor="history", divider="rainbow")
    section_guild_history(filters)


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    page_header()

    if "authentication_status" not in st.session_state:
        st.session_state.authentication_status = None

    authenticator, users, username = login()

    if username and st.session_state.get("authentication_status"):
        if check_user_role_permissions(username, "GUILD_PLAYER_STATS"):
            run_reports()
        else:
            st.warning("Nie masz dostepu do tej zawartosci.")