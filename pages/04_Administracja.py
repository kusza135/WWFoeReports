import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from PIL import Image
from tools.streamlit_tools import execute_query, page_header, get_world_id, get_guild_id, create_engine
import tools.login
import os
import streamlit_authenticator as stauth
import time

path = os.path.dirname(__file__)

def get_index_func(LOV, current_value):
    for (index, item) in enumerate(LOV):
        if item == current_value:
            return index
    return None
 
@st.cache_data(ttl=0, experimental_allow_widgets=True)
def all_logs_2_df():
    df = execute_query('SELECT CAST(load_date as CHAR(10)) LOAD_DATE, SP_NAME, START_DATE, END_DATE, TIME_ELAPSED FROM t_sp_load_procedures_log', return_type="df")
    return df
  
def exec_sp(sp_name, p_roleid, p_role_name, p_is_active ):
    con = create_engine()
    try:
        conn = con.raw_connection()
        cur = conn.cursor()
        cur.callproc(sp_name, args=[get_world_id(), get_guild_id(), p_roleid, p_role_name, p_is_active])
        cur.close() 
    except Exception as e:
        st.error(e)
        time.sleep(20)
    finally:
        conn.close() 
        
def get_roles():
    roles = execute_query(f''' SELECT y.roleid , y.role_name, y.LAST_CHANGE_DATE, y.is_active 
    FROM (SELECT world, guildid, roleid, max(LAST_CHANGE_DATE) as LAST_CHANGE_DATE from t_roles group by world, guildid, roleid)  x
    INNER JOIN t_roles y
    on x.world = y.world
    and x.guildid = y.guildid
    and x.roleid = y.roleid
    and x.LAST_CHANGE_DATE = y.LAST_CHANGE_DATE
    WHERE IS_ACTIVE = TRUE 
    AND y.world = '{get_world_id()}'
    and y.guildid = {get_guild_id()} ''', return_type="df")
    return roles


def main():
    
    page_header()
    authenticator, users, username  = tools.login.login()
    if username:
        # role = get_user_role_from_db(username)
        
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Konto", "Role", "Rekrutacja", "Parametry", "Logs"])
        

        with tab1.container():
            col1, col2, col3 = st.columns([50, 50, 10])
            if tools.login.check_user_role_permissions(username, 'ADMINISTRATION') == True:
                options = col1.radio(label="Wybierz opcję",options=["Zmień swoje hasło", "Nowy Użytkownik", "Zresetuj hasło użytkownika", "Przypisz rolę"], horizontal=False)
            else:
                options = col1.radio(label="Wybierz opcję",options=["Zmień swoje hasło"], horizontal=False)
            
            if options == "Zmień swoje hasło":
                with col2.container():
                    new_password, x = tools.login.reset_password(authenticator)
                    if new_password != None and x == True:
                        tools.login.db_change_pwd(username, new_password)
                        st.success("Hasło zmienione", icon="✅")
            if options == "Nowy Użytkownik":
                with col2.container():
            # with col1.expander(label="Create New User") as cnu:
                    x = authenticator.register_user('Uzupełnij dane', preauthorization=False)
                    if x == True :
                        # userName = 
                        for names in authenticator.credentials['usernames']:
                            tools.login.new_user(names, authenticator.credentials['usernames'][names]['name'], authenticator.credentials['usernames'][names]['password'])
                        st.success('User registered successfully')
                        st.cache_data.clear()
                        st.rerun()

            # with col2.expander(label="Reset User Password") as rup:
            if options == "Zresetuj hasło użytkownika":
                with col2.container():
                    wybor_uzytkownika = st.selectbox(label="Wybierz użytkownika", options=users)
                    new_password = st.text_input(label="Nowe hasło", type='password')
                    rep_new_password = st.text_input(label="Powtórz nowe hasło", type='password')
                    st.session_state['button_disable'] =True
                    if len(new_password) > 0:
                                if new_password == rep_new_password:
                                    hashed_password  = stauth.Hasher([new_password]).generate()
                                    st.session_state['button_disable'] = False
                                    st.button(label="Zresetuj", type='primary', on_click=tools.login.db_change_pwd, args=(wybor_uzytkownika, hashed_password[0]), disabled=st.session_state['button_disable'])
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.markdown('<div style="text-align: center;">Hasła do siebie nie pasują!</div>', unsafe_allow_html=True)
            if options == "Przypisz rolę":
                user_permissions = execute_query(f'''SELECT 
                                                        name, UserName, role_name, module_name, is_active
                                                    FROM 
                                                        v_user_permissions
                                                    WHERE 
                                                        world= '{get_world_id()}'
                                                        and guildid = {get_guild_id()}
                                                    ''', return_type="df")
                
                roles_permissions = get_roles()
                
                with col2.container():
                    col88, col99 = st.columns(2)
                    with col88:
                        if user_permissions['name'].empty:
                            user_permissions_index = None
                        else:
                            user_permissions_index=get_index_func(user_permissions.UserName.sort_index().unique().tolist(), user_permissions['name'].iloc[0])
                        
                        selected_user_permissions = st.selectbox(label="Wybierz Użytkownika", options=user_permissions.UserName.sort_index().unique(), index=user_permissions_index)
                    with col99:
                        if roles_permissions['roleid'].empty:
                            user_role_permissions_index = None
                        else:
                            user_role_permissions_index=get_index_func(roles_permissions.role_name.sort_index().unique().tolist(), roles_permissions['roleid'].iloc[0])
                        
                        selected_role_permissions = st.selectbox(label="Wybierz rolę ", options=roles_permissions.role_name.sort_index().unique(), index=user_role_permissions_index)
                    
                    status_is_active = col88.checkbox(label="## Aktywny", value=True)

                    if selected_user_permissions != None and selected_role_permissions != None :
                        role_permissions_id = roles_permissions[roles_permissions['role_name'] == selected_role_permissions].roleid.iloc[0]
                        if col88.button(label="Przypisz uprawnienia", on_click=exec_sp, args=('p_assign_role',  role_permissions_id,  selected_user_permissions, status_is_active), type="primary"):
                            st.success("Zapisano")
                st.dataframe(user_permissions[user_permissions['is_active'] == True], use_container_width=True, hide_index=True)
                

        with tab2.container() as x:
            if tools.login.check_user_role_permissions(username, 'ADMINISTRATION') == True:    
                col1, col2, col3 = st.columns([30, 60, 10])   
                
                roles = get_roles()
                
                modules = execute_query(f''' SELECT module_name FROM t_modules ''', return_type="df")
                
                permissions = execute_query(f''' SELECT y.role_name, r.module_name 
                                                FROM (SELECT world, guildid, roleid, max(LAST_CHANGE_DATE) as LAST_CHANGE_DATE from t_roles group by world, guildid, roleid)  x
                                                INNER JOIN t_roles y
                                                    on x.world = y.world
                                                    and x.guildid = y.guildid
                                                    and x.roleid = y.roleid
                                                    and x.LAST_CHANGE_DATE = y.LAST_CHANGE_DATE
                                                INNER JOIN 
                                                (SELECT world, guildid, roleid, module_name, max(LAST_CHANGE_DATE) as LAST_CHANGE_DATE from t_permissions  group by world, guildid, roleid, module_name)  p
                                                    on p.world = y.world
                                                    and p.guildid = y.guildid
                                                    and p.roleid = y.roleid
                                                inner join t_permissions r
                                                    on p.world = r.world
                                                    and p.guildid = r.guildid
                                                    and p.roleid = r.roleid
                                                    and p.LAST_CHANGE_DATE = r.LAST_CHANGE_DATE
                                                WHERE y.IS_ACTIVE = TRUE 
                                                    and r.is_active = TRUE
                                                    AND y.world = '{get_world_id()}'
                                                    and y.guildid = {get_guild_id()}
                                                ''', return_type="df")
                
                with col1:
                    radio_butn = st.radio(label="Wybierz opcję", options=["Dodaj/Modyfikuj rolę", "Przypisz moduł do roli"])
                    if st.button(label="Refresh"):
                        st.cache_data.clear()
                        st.rerun()
                with col2:
                    if radio_butn == "Dodaj/Modyfikuj rolę":
                     
                        col11, col22 = st.columns(2)

                        with col11.expander(label="Zmień"):
                                if roles['roleid'].empty:
                                    role_index = None
                                else:
                                    role_index=get_index_func(roles.role_name.sort_index().unique().tolist(), roles['roleid'].iloc[0])
                                
                                selected_role = st.selectbox(label="Wybierz rolę", options=roles.role_name.sort_index().unique(), index=role_index)
                                if selected_role:
                                    selected_role_id = roles[roles['role_name'] == selected_role].roleid.iloc[0]
                                    status_is_active = st.checkbox(label="## Aktywny  ", value=True)
                                    
                                    if st.button(label="Zapisz zmiany", on_click=exec_sp, args=('p_modify_role',  selected_role_id,  selected_role, status_is_active), type="primary"):
                                        st.success("Zapisano")
                        with col22.expander(label="Nowa"):
                                input_text = st.text_input(label="Wpisz nazwę roli")
                                status_is_active = st.checkbox(label="# Aktywny", value=True)
                                if input_text is not None:
                                    if st.button(label="Zapisz Nowy", on_click=exec_sp, args=('p_modify_role',  roles.roleid.max()+1,  input_text, status_is_active), type="primary"):
                                        st.success("Zapisano")
                            
                        st.dataframe(roles, use_container_width=True, hide_index=True)
                    elif radio_butn == "Przypisz moduł do roli":
                        
                        if roles['roleid'].empty:
                            role_index = None
                        else:
                            role_index=get_index_func(roles.role_name.sort_index().unique().tolist(), roles['roleid'].iloc[0])
                        col321, col322 = st.columns(2)
                        selected_role = col321.selectbox(label="Wybierz rolę", options=roles.role_name.sort_index().unique(), index=role_index)
                        selected_module = col322.selectbox(label="Wybierz moduł", options=modules.module_name.sort_index().unique(), index=0)
                        status_is_active = col321.checkbox(label="### Aktywny", value=True)
                        if selected_role !=  None and selected_module !=  None:
                            permissions = permissions[permissions['role_name'] == selected_role]
                            selected_role_id = roles[roles['role_name'] == selected_role].roleid.iloc[0]
                            if col321.button(label="Zapisz zmiany!", on_click=exec_sp, args=('p_permissions',  selected_role_id,  selected_module, status_is_active), type="primary"):
                                st.success("Zapisano")
                        
                        st.dataframe(permissions, use_container_width=True, hide_index=True)     
                        
                        
        with tab3.container() as x:
            if tools.login.check_user_role_permissions(username, 'ADMINISTRATION') == True:
                def modify_prospect_users(player_id, is_active):
                    query = f"call p_modify_prospect_users('{get_world_id()}',{get_guild_id()}, {player_id}, {is_active})"
                    execute_query(query, return_type="df")
                
                all_guild_users = execute_query(f''' 
                                                SELECT x.playerId, name
                                                FROM 
                                                (
                                                    SELECT world, playerId FROM V_all_players WHERE VALID_TO  = '3000-12-31' AND world = '{get_world_id()}' AND ClanId = {get_guild_id()}
                                                    UNION 
                                                    SELECT world, playerId FROM t_recruters WHERE world = '{get_world_id()}' AND guildid = {get_guild_id()}
                                                ) as x 
                                                LEFT JOIN 
                                                    (SELECT world, playerId, name from V_all_players WHERE VALID_TO  = '3000-12-31' AND world = '{get_world_id()}') w
                                                        ON w.world = x.world
                                                        and w.playerId = x.playerId  ''', return_type="df")
                
                
                get_all_recruters = execute_query(f''' 
                                                SELECT name as "Gracz", clanName "Gildia", LAST_CHANGE_DATE "Data ostatniej modyfikacji", is_active Aktywny
                                                FROM 
                                                    t_recruters x
                                                LEFT JOIN 
                                                    (SELECT world, playerId, name, clanName from V_all_players WHERE VALID_TO  = '3000-12-31' AND world = '{get_world_id()}') w
                                                        ON w.world = x.world
                                                        and w.playerId = x.playerId  
                                                WHERE 
                                                    x.world = '{get_world_id()}'
                                                    AND x.guildid = {get_guild_id()} 
                                                ''', return_type="df")
                col1, col2, col3 = st.columns([20,60,20])
                with col2:
                    selected_player = col2.selectbox("Wybierz nazwę gracza", all_guild_users.name.sort_values().unique(),  placeholder="Rozwiń lub zacznij wpisywać", index=None)
                    with col2.container(border=True):
                        if selected_player is not None:
                            df2=all_guild_users.loc[all_guild_users['name'] == selected_player, 'playerId'].iloc[0]
                            col1, col2, col3 = col2.columns([15,10, 40])
                            col1.text_input(label="Gracz", value=selected_player, disabled=True)
                            col2.write("\n\n\n")
                            is_active = col2.checkbox(label="Aktywny?", value=True)
                            if col2.button(label="Zapisz", type="primary", on_click=modify_prospect_users, args=(df2, is_active)):
                                col2.cache_data.clear()
                                col2.rerun()

                col2.dataframe(get_all_recruters, column_config={"Aktywny": st.column_config.CheckboxColumn(default=True)}, hide_index=True, use_container_width=True)
            
        with tab5.container() as x:
            
            st.cache_data.clear()
            all_logs= all_logs_2_df()
            Report_Date_list = [ 
                                row[0]
                                for row in execute_query(
                                    f'''select distinct 
                        CAST(load_date as CHAR(10))|| CASE 
                            WEEKDAY(load_date) 
                            when 0 then '  (Poniedziałek)'
                            when 1 then '  (Wtorek)'
                            when 2 then '  (Środa)'
                            when 3 then '  (Czwartek)'
                            when 4 then '  (Piątek)'
                            when 5 then '  (Sobota)'
                            when 6 then '  (Niedziela)'
                        END report_date
                        from t_sp_load_procedures_log 
                        order by 1''', return_type="list"
                                )
                            ]
            while  len(Report_Date_list)<2:
                Report_Date_list.append("_empty")
            date_filter = st.select_slider(label="Select a report date", options=Report_Date_list, value=max(Report_Date_list), label_visibility="hidden")
            st.dataframe(all_logs[all_logs['LOAD_DATE'] == date_filter[:10]].sort_values(by='START_DATE', ascending=True), use_container_width= True, hide_index=True)
main()
