import streamlit as st
import streamlit_authenticator as stauth
from  tools.streamlit_tools import execute_query, get_world_id, get_guild_id


def get_users_credentials_from_db():
    query = f'''SELECT 
                    Name
                    , `role`
                    , UserName
                    , UserPassword
                FROM   
                    V_users'''
    all_users_db=execute_query(query=query, return_type='list')
    return all_users_db

def check_user_role_permissions(name, module_name):
    query = f'''SELECT 
                    name
                    , UserName
                    , `role`
                    , role_name
                    , CASE WHEN role_name = 'Admin' or module_name is not null then True
                      else false end access
                FROM v_user_permissions
                WHERE NAME =  '{name}' 
                and world = '{get_world_id()}'
                and guildid = {get_guild_id()}
                and ( module_name = '{module_name}' or role_name = 'Admin')
                '''
    all_users_db=execute_query(query=query, return_type='df')
    if all_users_db.empty:
        access = False
    else:
        access = all_users_db['access'].iloc[0]

    return access

def get_user_role_from_db(name):
    query = f'''SELECT 
                    `role`
                FROM   
                    V_users
                WHERE NAME =  '{name}' '''
    all_users_db=execute_query(query=query, return_type='list')
    role = all_users_db[0][0]
    return role

def display_logged_user(name):
    # col1, col2 = st.columns([10,25])
    st.sidebar.markdown(f'<center><p style="background-color:#e9f7e1;color:#666963;font-size:14px;">Zalogowano jako <br>{name}</p>', unsafe_allow_html=True)

def new_user(login, UserName, Password):
    execute_query(f"call p_add_user('{get_world_id()}', {get_guild_id()},'{login}','{UserName}', '{Password}')", return_type="df")
    
def db_change_pwd(UserName, Password):
    query = f"call p_modify_user('{get_world_id()}', {get_guild_id()}, '{UserName}', '{Password}')"
    execute_query(query, return_type="df")


def reset_password(authenticator):
    try:
        x = authenticator.reset_password(st.session_state["username"], 'Zresetuj hasło')
        if x == True:
            new_password = authenticator.credentials['usernames'][st.session_state["username"]]['password']
            return new_password, x
        else :
            return None, False
    except Exception as e:
        st.error(e)
        return None, False


# def change_pwd(authenticator):
    
#     with st.sidebar.expander(label="Zmień hasło", expanded=False) as f:
#         new_password, x = reset_password(authenticator)
#         if new_password != None and x == True:
#             db_change_pwd(st.session_state["username"], new_password)
#             st.success("Hasło zmienione", icon="✅")


def login():
    all_users_db = get_users_credentials_from_db()
    users = [user[0] for user in all_users_db]
    UserNames = [user[2] for user in all_users_db]
    passwords = [user[3] for user in all_users_db]

    credentials = {"usernames":{}}

    
    for name,uname,pwd in zip(UserNames,users,passwords):
        user_dict = {"name": name, "password": pwd}
        credentials["usernames"].update({uname: user_dict})
    
    authenticator = stauth.Authenticate(credentials, "foeWW", "WzgFoeWWtheKing", cookie_expiry_days=30, preauthorized=['adamus01@gmail.com'])


    name, authenticator_status, username = authenticator.login("Logowanie", "main")


    if authenticator_status == False:
        st.error("Nieprawidłowy Login/hasło")
    if authenticator_status == None:
        st.warning("Wprowadź Login/hasło")
    if authenticator_status == True:
        st.session_state.authenticator_status = authenticator_status
        if 'role' not in st.session_state:
            st.session_state['role'] = get_user_role_from_db(username)
        display_logged_user(name)
        # change_pwd(authenticator)
    

    if authenticator.logout('Logout', 'sidebar'):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun
    return authenticator, users, username



