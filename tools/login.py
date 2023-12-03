import streamlit as st
import streamlit_authenticator as stauth
from  tools.streamlit_tools import execute_query

def new_user(login, UserName, Password):
    execute_query(f"call p_add_user('{login}','{UserName}', '{Password}')", return_type="df")

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
    st.sidebar.markdown(f'<center><p style="background-color:#e9f7e1;color:#666963;font-size:14px;">Witaj <br>{name}</p>', unsafe_allow_html=True)


def db_change_pwd(UserName, Password):
    query = f"call p_modify_user('{UserName}', '{Password}')"
    # st.write(query)
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


def change_pwd(authenticator):
    
    with st.sidebar.expander(label="Zmień hasło", expanded=False) as f:
        new_password, x = reset_password(authenticator)
        if new_password != None and x == True:
            db_change_pwd(st.session_state["username"], new_password)
            st.success("Hasło zmienione", icon="✅")


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
        change_pwd(authenticator)
    
    # Admin part
        if st.session_state['role'] == 'Admin':
            with st.container() as c:
                col1, col2, col3 = st.columns([10, 10, 10])
                with col1.expander(label="Create New User") as cnu:
                    x = authenticator.register_user('Uzupełnij dane', preauthorization=False)
                    if x == True :
                        # userName = 
                        for names in authenticator.credentials['usernames']:
                            new_user(names, authenticator.credentials['usernames'][names]['name'], authenticator.credentials['usernames'][names]['password'])
                        st.success('User registered successfully')
                        st.cache_data.clear()
                        st.rerun()
        
                with col2.expander(label="Reset User Password") as rup:
                    
                    wybor_uzytkownika = st.selectbox(label="Wybierz użytkownika", options=users)
                    new_password = st.text_input(label="Nowe hasło", type='password')
                    rep_new_password = st.text_input(label="Powtórz nowe hasło", type='password')
                    if len(new_password) > 0:
                                if new_password == rep_new_password:
                                    hashed_password  = stauth.Hasher([new_password]).generate()
                                    db_change_pwd(wybor_uzytkownika, hashed_password)
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    raise 'Passwords do not match'
        if authenticator.logout('Logout', 'sidebar'):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun


