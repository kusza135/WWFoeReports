import streamlit as st
import streamlit_authenticator as stauth
from tools.streamlit_tools import (
    execute_query, page_header, get_world_id, get_guild_id,
    create_engine, convert_string_to_bool,
)
import tools.login
import time

# ---------------------------------------------------------------------------
# WARSTWA DANYCH
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_roles() -> object:
    return execute_query(
        """SELECT y.roleid, y.role_name, y.LAST_CHANGE_DATE, y.is_active
           FROM (
               SELECT world, guildid, roleid, MAX(LAST_CHANGE_DATE) AS LAST_CHANGE_DATE
               FROM t_roles GROUP BY world, guildid, roleid
           ) x
           INNER JOIN t_roles y
               ON x.world = y.world AND x.guildid = y.guildid
               AND x.roleid = y.roleid AND x.LAST_CHANGE_DATE = y.LAST_CHANGE_DATE
           WHERE y.IS_ACTIVE = TRUE
             AND y.world = :world AND y.guildid = :guildid
        """,
        params={"world": get_world_id(), "guildid": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=300)
def get_modules() -> object:
    return execute_query("SELECT module_name FROM t_modules", return_type="df")


@st.cache_data(ttl=300)
def get_permissions() -> object:
    return execute_query(
        """SELECT y.role_name, r.module_name
           FROM (
               SELECT world, guildid, roleid, MAX(LAST_CHANGE_DATE) AS LAST_CHANGE_DATE
               FROM t_roles GROUP BY world, guildid, roleid
           ) x
           INNER JOIN t_roles y
               ON x.world = y.world AND x.guildid = y.guildid
               AND x.roleid = y.roleid AND x.LAST_CHANGE_DATE = y.LAST_CHANGE_DATE
           INNER JOIN (
               SELECT world, guildid, roleid, module_name, MAX(LAST_CHANGE_DATE) AS LAST_CHANGE_DATE
               FROM t_permissions GROUP BY world, guildid, roleid, module_name
           ) p
               ON p.world = y.world AND p.guildid = y.guildid AND p.roleid = y.roleid
           INNER JOIN t_permissions r
               ON p.world = r.world AND p.guildid = r.guildid AND p.roleid = r.roleid
               AND p.LAST_CHANGE_DATE = r.LAST_CHANGE_DATE
           WHERE y.IS_ACTIVE = TRUE AND r.is_active = TRUE
             AND y.world = :world AND y.guildid = :guildid
        """,
        params={"world": get_world_id(), "guildid": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=300)
def get_user_permissions() -> object:
    return execute_query(
        """SELECT name, UserName, role_name, module_name, is_active
           FROM v_user_permissions
           WHERE world = :world AND guildid = :guildid
        """,
        params={"world": get_world_id(), "guildid": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=300)
def get_params_list() -> object:
    return execute_query(
        """SELECT
                id_key, world, ClanId,
                json_extract(`Params`, '$.key') AS Param_Name,
                json_extract(`Params`, '$.value') AS Param_Value,
                Param_Desc,
                last_update_date AS Last_Update_date
            FROM t_params
            WHERE world = :world AND ClanId = :guildid
        """,
        params={"world": get_world_id(), "guildid": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=300)
def get_all_guild_users() -> object:
    return execute_query(
        """SELECT x.playerId, name
           FROM (
               SELECT world, playerId FROM V_ALL_PLAYERS
               WHERE VALID_TO = '3000-12-31' AND world = :world AND ClanId = :guildid
               UNION
               SELECT world, playerId FROM t_recruters
               WHERE world = :world AND guildid = :guildid
           ) x
           LEFT JOIN (
               SELECT world, playerId, name FROM V_ALL_PLAYERS
               WHERE VALID_TO = '3000-12-31' AND world = :world
           ) w ON w.world = x.world AND w.playerId = x.playerId
        """,
        params={"world": get_world_id(), "guildid": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=300)
def get_all_recruters() -> object:
    return execute_query(
        """SELECT name AS Gracz, clanName AS Gildia,
                  LAST_CHANGE_DATE AS `Data ostatniej modyfikacji`, is_active AS Aktywny
           FROM t_recruters x
           LEFT JOIN (
               SELECT world, playerId, name, clanName FROM V_ALL_PLAYERS
               WHERE VALID_TO = '3000-12-31' AND world = :world
           ) w ON w.world = x.world AND w.playerId = x.playerId
           WHERE x.world = :world AND x.guildid = :guildid
        """,
        params={"world": get_world_id(), "guildid": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=300)
def get_lottery_users() -> object:
    return execute_query(
        """SELECT x.playerId, name
           FROM (
               SELECT world, playerId FROM V_ALL_PLAYERS
               WHERE VALID_TO = '3000-12-31' AND world = :world AND ClanId = :guildid
               UNION
               SELECT world, player_Id FROM t_gpc_lottery_exceptions
               WHERE world = :world AND ClanId = :guildid
           ) x
           LEFT JOIN (
               SELECT world, playerId, name FROM V_ALL_PLAYERS
               WHERE VALID_TO = '3000-12-31' AND world = :world
           ) w ON w.world = x.world AND w.playerId = x.playerId
        """,
        params={"world": get_world_id(), "guildid": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=300)
def get_lottery_exceptions() -> object:
    return execute_query(
        """SELECT ex.player_id, ap.name AS player_name
           FROM t_gpc_lottery_exceptions ex
           INNER JOIN V_ALL_PLAYERS ap
               ON ap.world = ex.world AND ap.ClanId = ex.ClanId
               AND ex.Player_id = ap.playerId
           WHERE ex.world = :world AND ex.ClanId = :guildid
             AND ap.valid_to = '3000-12-31'
        """,
        params={"world": get_world_id(), "guildid": get_guild_id()},
        return_type="df",
    )


@st.cache_data(ttl=60)
def get_log_dates() -> list:
    rows = execute_query(
        """SELECT DISTINCT
               CAST(load_date AS CHAR(10)) || CASE WEEKDAY(load_date)
                   WHEN 0 THEN '  (Poniedzialek)'
                   WHEN 1 THEN '  (Wtorek)'
                   WHEN 2 THEN '  (Sroda)'
                   WHEN 3 THEN '  (Czwartek)'
                   WHEN 4 THEN '  (Piatek)'
                   WHEN 5 THEN '  (Sobota)'
                   WHEN 6 THEN '  (Niedziela)'
               END AS report_date
           FROM t_sp_load_procedures_log
           ORDER BY 1
        """,
        return_type="list",
    )
    dates = [r[0] for r in rows]
    while len(dates) < 2:
        dates.append("_empty")
    return dates


@st.cache_data(ttl=60)
def get_all_logs() -> object:
    return execute_query(
        """SELECT CAST(load_date AS CHAR(10)) AS LOAD_DATE,
                  SP_NAME, START_DATE, END_DATE, TIME_ELAPSED
           FROM t_sp_load_procedures_log
        """,
        return_type="df",
    )


# ---------------------------------------------------------------------------
# HELPERY
# ---------------------------------------------------------------------------

def get_index_func(lov: list, current_value) -> int | None:
    try:
        return lov.index(current_value)
    except ValueError:
        return None


def role_selectbox(label: str, roles, key: str | None = None) -> tuple:
    """Helper: selectbox ról z automatycznym indeksem. Zwraca (selected_name, role_id)."""
    options = roles.role_name.sort_index().unique()
    idx = get_index_func(
        options.tolist(),
        roles["roleid"].iloc[0] if not roles["roleid"].empty else None,
    )
    selected = st.selectbox(label, options=options, index=idx, key=key)
    role_id = roles[roles["role_name"] == selected].roleid.iloc[0] if selected else None
    return selected, role_id


def clear_roles_cache() -> None:
    """Czyści cache po mutacjach na rolach/uprawnieniach."""
    get_roles.clear()
    get_modules.clear()
    get_permissions.clear()
    get_user_permissions.clear()


def exec_sp(sp_name: str, p_roleid, p_role_name, p_is_active) -> None:
    con = create_engine()
    try:
        conn = con.raw_connection()
        cur = conn.cursor()
        cur.callproc(sp_name, args=[get_world_id(), get_guild_id(), p_roleid, p_role_name, p_is_active])
        conn.commit()
        cur.close()
    except Exception as e:
        st.error(e)
        time.sleep(5)
    finally:
        conn.close()
    clear_roles_cache()


def modify_prospect_users(player_id: int, is_active: bool) -> None:
    execute_query(
        "CALL p_modify_prospect_users(:world, :guildid, :player_id, :is_active)",
        params={
            "world": get_world_id(), "guildid": get_guild_id(),
            "player_id": player_id, "is_active": is_active,
        },
        return_type="df",
    )
    get_all_guild_users.clear()
    get_all_recruters.clear()


def lottery_exception_add(player_id: int) -> None:
    execute_query(
        "CALL p_gpc_lottery_exception_add(:world, :guildid, :player_id)",
        params={"world": get_world_id(), "guildid": get_guild_id(), "player_id": player_id},
        return_type="df",
    )
    get_lottery_exceptions.clear()
    get_lottery_users.clear()


def lottery_exception_delete(player_id: int) -> None:
    execute_query(
        "CALL p_gpc_lottery_exception_delete(:world, :guildid, :player_id)",
        params={"world": get_world_id(), "guildid": get_guild_id(), "player_id": player_id},
        return_type="df",
    )
    get_lottery_exceptions.clear()
    get_lottery_users.clear()


# ---------------------------------------------------------------------------
# DIALOG
# ---------------------------------------------------------------------------

@st.dialog(title="Zmien parametry", width="large")
def change_params(df, edited_df) -> None:
    c1, c2, c3 = st.columns([20, 60, 20])
    row_idx = edited_df.selection["rows"][0]
    id_key = df.iloc[row_idx]["id_key"]
    old_value = df[df["id_key"] == id_key]["Param_Value"].iloc[0]

    if convert_string_to_bool(old_value) is not None:
        new_value = c2.selectbox("Nowa wartosc", options=[True, False], label_visibility="hidden")
    elif str(old_value).isdigit():
        new_value = c2.number_input("Nowa wartosc", value=old_value, label_visibility="hidden")
    else:
        new_value = c2.text_input("Nowa wartosc", value=old_value, label_visibility="hidden")

    if c2.button("Zmien", type="primary"):
        param_name = df.iloc[row_idx]["Param_Name"]
        execute_query(
            "CALL p_change_param(:id_key, :new_value)",
            params={"id_key": id_key, "new_value": new_value},
            return_type="df",
        )
        get_params_list.clear()
        st.toast("Zapisano", icon="✅")
        st.rerun()

    if df.iloc[row_idx]["Param_Name"] == '"GPC Lottery module"':
        tab_lottery_exceptions()


# ---------------------------------------------------------------------------
# TABY
# ---------------------------------------------------------------------------

def _account_change_password(authenticator, username: str) -> None:
    new_password, changed = tools.login.reset_password(authenticator)
    if new_password and changed:
        tools.login.db_change_pwd(username, new_password)
        st.success("Haslo zmienione", icon="✅")


def _account_new_user(authenticator) -> None:
    result = authenticator.register_user(
        location="main",
        fields={
            "Form name": "Register user", "Email": "Email",
            "Username": "Username", "Password": "Password",
            "Repeat password": "Repeat password", "Register": "Register",
        },
        captcha=False,
        password_hint=False,
    )
    # register_user() zwraca (email, username, full_name) lub (None, None, None)
    # W 0.4.x Authenticate nie ma atrybutu .credentials — dostęp przez model
    if result and result[1]:
        _, uname, name = result
        creds = authenticator.authentication_controller.authentication_model.credentials
        pwd_hash = creds['usernames'][uname]['password']
        tools.login.new_user(uname, name, pwd_hash)
        st.success("Uzytkownik zarejestrowany")
        st.cache_data.clear()
        st.rerun()


def _account_reset_password(users: list) -> None:
    selected_user = st.selectbox("Wybierz uzytkownika", options=users)
    new_pwd = st.text_input("Nowe haslo", type="password")
    rep_pwd = st.text_input("Powtorz nowe haslo", type="password")
    if new_pwd:
        if new_pwd == rep_pwd:
            # W 0.4.x Hasher jest klasą statyczną: .hash() zwraca string (nie listę)
            hashed = stauth.Hasher.hash(new_pwd)
            st.button(
                "Zresetuj", type="primary",
                on_click=tools.login.db_change_pwd,
                args=(selected_user, hashed),
            )
        else:
            st.error("Hasla do siebie nie pasuja!")


def _user_selector(user_permissions, col88) -> str:
    idx = get_index_func(
        user_permissions.UserName.sort_index().unique().tolist(),
        user_permissions["name"].iloc[0] if not user_permissions["name"].empty else None,
    )
    return col88.selectbox("Wybierz Uzytkownika", options=user_permissions.UserName.sort_index().unique(), index=idx)


def _role_assign_button(col88, selected_user, selected_role, role_id_sel, is_active) -> None:
    if not (selected_user and selected_role and role_id_sel is not None):
        return
    if col88.button("Przypisz uprawnienia", on_click=exec_sp,
                    args=("p_assign_role", role_id_sel, selected_user, is_active), type="primary"):
        st.success("Zapisano")


def _account_assign_role() -> None:
    user_permissions = get_user_permissions()
    roles = get_roles()
    col88, col99 = st.columns(2)
    selected_user = _user_selector(user_permissions, col88)
    with col99:
        _, role_id_sel = role_selectbox("Wybierz role", roles)
        selected_role = roles[roles["roleid"] == role_id_sel].role_name.iloc[0] if role_id_sel is not None else None
    is_active = col88.checkbox("Aktywny", value=True)
    _role_assign_button(col88, selected_user, selected_role, role_id_sel, is_active)
    st.dataframe(user_permissions[user_permissions["is_active"] == True], width="stretch", hide_index=True)


@st.fragment
def tab_account(authenticator, users: list, username: str, is_admin: bool) -> None:
    col1, col2, _ = st.columns([50, 50, 10])

    account_options = (
        ["Zmien swoje haslo", "Nowy Uzytkownik", "Zresetuj haslo uzytkownika", "Przypisz role"]
        if is_admin else
        ["Zmien swoje haslo"]
    )
    option = col1.radio("Wybierz opcje", options=account_options, horizontal=False)

    with col2:
        if option == "Zmien swoje haslo":
            _account_change_password(authenticator, username)
        elif option == "Nowy Uzytkownik":
            _account_new_user(authenticator)
        elif option == "Zresetuj haslo uzytkownika":
            _account_reset_password(users)
        elif option == "Przypisz role":
            _account_assign_role()


def _roles_edit_or_create(roles) -> None:
    col11, col22 = st.columns(2)

    with col11.expander("Zmien"):
        selected_role, role_id = role_selectbox("Wybierz role", roles, key="edit_role_sel")
        if selected_role and role_id is not None:
            is_active = st.checkbox("Aktywny", value=True, key="edit_role_active")
            if st.button("Zapisz zmiany", on_click=exec_sp,
                         args=("p_modify_role", role_id, selected_role, is_active), type="primary"):
                st.success("Zapisano")

    with col22.expander("Nowa"):
        new_role_name = st.text_input("Wpisz nazwe roli")
        is_active_new = st.checkbox("Aktywny", value=True, key="new_role_active")
        if new_role_name:
            new_id = int(roles.roleid.max()) + 1 if not roles.empty else 1
            if st.button("Zapisz Nowy", on_click=exec_sp,
                         args=("p_modify_role", new_id, new_role_name, is_active_new), type="primary"):
                st.success("Zapisano")

    st.dataframe(roles, width="stretch", hide_index=True)


def _roles_assign_module(roles, modules, permissions) -> None:
    col321, col322 = st.columns(2)
    selected_role, role_id = role_selectbox("Wybierz role", roles, key="assign_role_sel")
    selected_module = col322.selectbox("Wybierz modul", options=modules.module_name.sort_index().unique(), index=0)
    is_active = col321.checkbox("Aktywny", value=True, key="assign_module_active")

    if selected_role and selected_module and role_id is not None:
        filtered = permissions[permissions["role_name"] == selected_role]
        if col321.button("Zapisz zmiany!", on_click=exec_sp,
                         args=("p_permissions", role_id, selected_module, is_active), type="primary"):
            st.success("Zapisano")
        st.dataframe(filtered, width="stretch", hide_index=True)


@st.fragment
def tab_roles(is_admin: bool) -> None:
    if not is_admin:
        st.warning("Brak uprawnien do tej sekcji.")
        return

    roles = get_roles()
    modules = get_modules()
    permissions = get_permissions()

    col1, col2, _ = st.columns([30, 60, 10])
    with col1:
        mode = st.radio("Wybierz opcje", options=["Dodaj/Modyfikuj role", "Przypisz modul do roli"])
        if st.button("Refresh"):
            clear_roles_cache()
            st.rerun()

    with col2:
        if mode == "Dodaj/Modyfikuj role":
            _roles_edit_or_create(roles)
        elif mode == "Przypisz modul do roli":
            _roles_assign_module(roles, modules, permissions)


def _player_recruiter_form(col2, guild_users) -> None:
    selected_player = col2.selectbox("Wybierz nazwe gracza", guild_users.name.sort_values().unique(),
                                     placeholder="Rozwij lub zacznij wpisywac", index=None)
    with col2.container(border=True):
        if selected_player:
            player_id = guild_users.loc[guild_users["name"] == selected_player, "playerId"].iloc[0]
            c1, c2, _ = st.columns([15, 10, 40])
            c1.text_input("Gracz", value=selected_player, disabled=True)
            is_active = c2.checkbox("Aktywny?", value=True)
            c2.button("Zapisz", type="primary", on_click=modify_prospect_users, args=(player_id, is_active))
    col2.dataframe(get_all_recruters(), column_config={"Aktywny": st.column_config.CheckboxColumn(default=True)},
                   hide_index=True, width="stretch")


@st.fragment
def tab_recruitment(is_admin: bool) -> None:
    if not is_admin:
        st.warning("Brak uprawnien do tej sekcji.")
        return
    col1, col2, _ = st.columns([20, 60, 20])
    _player_recruiter_form(col2, get_all_guild_users())


@st.fragment
def tab_params(is_admin: bool) -> None:
    if not is_admin:
        st.warning("Brak uprawnien do tej sekcji.")
        return

    df = get_params_list()
    result = st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Last_Update_date": st.column_config.DatetimeColumn(label="Last_update_date"),
            "Param_Name": st.column_config.TextColumn(label="Param_Name"),
            "world": None, "id_key": None, "ClanId": None,
        },
    )
    if result.selection["rows"]:
        change_params(df, result)


def _add_lottery_exception_form(col2, lottery_users) -> None:
    selected = col2.selectbox("Wybierz gracza", key="lottery_selectbox",
                              options=lottery_users.name.sort_values().unique(),
                              placeholder="Rozwij lub zacznij wpisywac", index=None)
    with col2.container(border=True):
        if selected:
            pid = lottery_users.loc[lottery_users["name"] == selected, "playerId"].iloc[0]
            col2.button("Dodaj", key="lottery_add", type="primary", on_click=lottery_exception_add, args=(pid,))


def _remove_lottery_exception(col2, exceptions) -> None:
    result = col2.dataframe(exceptions, hide_index=True, on_select="rerun", selection_mode="single-row", width="stretch")
    if result.selection["rows"]:
        pid = exceptions.iloc[result.selection["rows"][0]]["player_id"]
        col2.button("Usun", key="lottery_delete", type="primary", on_click=lottery_exception_delete, args=(pid,))


@st.fragment
def tab_lottery_exceptions() -> None:
    """Zarzadzanie wyjatkami od loterii GPCh."""
    lottery_users = get_lottery_users()
    exceptions = get_lottery_exceptions()
    col1, col2, col3 = st.columns([20, 60, 20])
    _add_lottery_exception_form(col2, lottery_users)
    _remove_lottery_exception(col2, exceptions)


@st.fragment
def tab_logs() -> None:
    dates = get_log_dates()
    all_logs = get_all_logs()

    date_filter = st.select_slider(
        "Wybierz date",
        options=dates,
        value=max(d for d in dates if d != "_empty"),
        label_visibility="hidden",
    )
    st.dataframe(
        all_logs[all_logs["LOAD_DATE"] == date_filter[:10]].sort_values("START_DATE"),
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------------------------
# GLOWNA FUNKCJA
# ---------------------------------------------------------------------------

def main() -> None:
    page_header()

    if "authentication_status" not in st.session_state:
        st.session_state.authentication_status = None

    authenticator, users, username = tools.login.login()

    if not username or not st.session_state.get("authentication_status"):
        return

    is_admin = tools.login.check_user_role_permissions(username, "ADMINISTRATION")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Konto", "Role", "Rekrutacja", "Parametry", "Logs"])

    with tab1:
        tab_account(authenticator, users, username, is_admin)
    with tab2:
        tab_roles(is_admin)
    with tab3:
        tab_recruitment(is_admin)
    with tab4:
        tab_params(is_admin)
    with tab5:
        tab_logs()


main()