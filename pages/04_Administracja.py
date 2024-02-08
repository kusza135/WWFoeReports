import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from PIL import Image
from tools.streamlit_tools import execute_query, page_header, get_world_id, get_guild_id
from tools.login import login, get_user_role_from_db, reset_password, db_change_pwd
import os
import streamlit_authenticator as stauth

path = os.path.dirname(__file__)

def new_user(login, UserName, Password):
    execute_query(f"call p_add_user('{login}','{UserName}', '{Password}')", return_type="df")

    
def main():
    st.set_page_config(
        page_title="WW Stats",
        page_icon=".streamlit//logo.png",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'http://www.google_com/',
            'Report a Bug' : 'mailto:adamus01@gmail.com', 
            'About': "# This apps may help to monitor guild health."
        }
    )    
    page_header()
    authenticator, users, username  = login()
    if username:
        role = get_user_role_from_db(username)
        
        if role == 'Admin':
            tab1, tab2, tab3 = st.tabs(["Konto", "Rekrutacja", "Parametry"])
        elif role == 'User':
              tab1 = st.tabs(["Konto", "Rekrutacja", "Parametry"])
        
        with tab2.container() as x:
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
                # else:
                #     st.form_submit_button(label="Zapisz", type="primary",disabled = True)


            col2.dataframe(get_all_recruters, column_config={"Aktywny": st.column_config.CheckboxColumn(default=True)}, hide_index=True, use_container_width=True)
            
        with tab1.container() as c:
            
            col1, col2, col3 = st.columns([50, 50, 10])
            if role == 'Admin':
                options = col1.radio(label="Wybierz opcję",options=["Change your Password", "Create New User", "Reset User Password"], horizontal=False)
            elif role == 'User':
                options = col1.radio(label="Wybierz opcję",options=["Zmień hasło"], horizontal=False)
            
            if options == "Change your Password" or options == "Zmień hasło":
                with col2.container():
                    new_password, x = reset_password(authenticator)
                    if new_password != None and x == True:
                        db_change_pwd(username, new_password)
                        st.success("Hasło zmienione", icon="✅")
            if options == "Create New User":
                with col2.container():
            # with col1.expander(label="Create New User") as cnu:
                    x = authenticator.register_user('Uzupełnij dane', preauthorization=False)
                    if x == True :
                        # userName = 
                        for names in authenticator.credentials['usernames']:
                            new_user(names, authenticator.credentials['usernames'][names]['name'], authenticator.credentials['usernames'][names]['password'])
                        st.success('User registered successfully')
                        st.cache_data.clear()
                        st.rerun()

            # with col2.expander(label="Reset User Password") as rup:
            if options == "Reset User Password":
                with col2.container():
                    wybor_uzytkownika = st.selectbox(label="Wybierz użytkownika", options=users)
                    new_password = st.text_input(label="Nowe hasło", type='password')
                    rep_new_password = st.text_input(label="Powtórz nowe hasło", type='password')
                    st.session_state['button_disable'] =True
                    if len(new_password) > 0:
                                if new_password == rep_new_password:
                                    hashed_password  = stauth.Hasher([new_password]).generate()
                                    st.session_state['button_disable'] = False
                                    st.button(label="Zresetuj", type='primary', on_click=db_change_pwd, args=(wybor_uzytkownika, hashed_password[0]), disabled=st.session_state['button_disable'])
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.markdown('<div style="text-align: center;">Hasła do siebie nie pasują!</div>', unsafe_allow_html=True)
        


main()
