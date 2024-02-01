import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from tools.streamlit_tools import execute_query, get_guild_id, get_world_id, page_header
from tools.login import login
import pandas as pd

dump_value = "-1z"
st.session_state['textmsg']= dump_value



# if 'df_editable' not in st.session_state:
#     st.session_state["df_editable"] = None

# def assign_session_p():
#     st.markdown(f"*{st.session_state['textmsg']}*")
#     st.write(st.session_state['2_key'])
#     change_text(st.session_state['textmsg'], st.session_state['2_key'])
def first_report():
    
    def exl_guids() -> list:
        modification_container = st.container()
        with modification_container:
            filters = []
            df= execute_query(f'''SELECT clanId, name AS Gildia  FROM V_all_guilds WHERE world = '{get_world_id()}'  and clanId <> {get_guild_id()} ''',return_type="df",
                    )
            to_filter_columns = st.multiselect("Wybierz gildie", df.Gildia.sort_values().unique(),  placeholder="Rozwiń lub zacznij wpisywać")
            for row in to_filter_columns:
                df2=df.loc[df['Gildia'] == row, 'clanId'].iloc[0]
                filters.append(df2)
        return filters
    
    all_players = execute_query(
            f'''SELECT 
                    playerId
                    , Player_rank
                    , name
                    , ClanId
                    , clanName
                    , points
                    , battles
                    , Age_PL
                    , pointsDif
                    , battlesDif
                    , prospect
                    , STATUS
                    , notes
                FROM V_all_players
                WHERE world = '{get_world_id()}'  and (ClanId <> {get_guild_id()} or ClanId IS NULL)
                ''',
                        return_type="df",
                    )

    with st.expander(label="Filtuj ...", expanded=True):
        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        with col1.container():
            exl_guilds = st.checkbox(label="Wyklucz wybrane gildie", value=False)
            if exl_guilds:
                f_exl_guilds = exl_guids()
                all_players = all_players[~all_players['ClanId'].isin(f_exl_guilds)]
        with col2.container():
            homeless = st.radio(label="Gracze", options=['bez Gildii', 'w Gildii', 'Wszyscy'], index=2)
            if homeless == 'bez Gildii':
                all_players = all_players[all_players['ClanId'].isna()]
            elif homeless == 'w Gildii':
                all_players = all_players[~all_players['ClanId'].isna()]
            elif homeless == 'bez Gildii':
                None



    def dataframe_with_selections(df):
        df_with_selections = df.copy()
        df_with_selections.insert(0, "Select", False)

        # Get dataframe row-selections from user with st.data_editor
        edited_df = st.data_editor(
            df_with_selections,
            hide_index=True,
            column_config={
                            "Select": st.column_config.CheckboxColumn(required=True), 
                           "prospect": st.column_config.CheckboxColumn(default=False)
                           },
            disabled=("playerId", "Player_rank", "name", "ClanId", "clanName", "points", "battles", "Age_PL", "pointsDif", "battlesDif")
        )
        selected_player= ""
        # Filter the dataframe using the temporary column, then drop the column
        selected_rows = edited_df[edited_df.Select]
        if not selected_rows.empty:
            selected_player = selected_rows["playerId"].iloc[0]
            # st.write(selected_rows["playerId"].iloc[0])
        return selected_player


    selection = dataframe_with_selections(all_players)
    st.write("Your selection:")
    st.write(selection)


def run_reports():
    st.subheader(" ##  Panel rekrutacyjny  ## ", anchor='Rekrutacja')  
    first_report()

        
if __name__ == '__main__':
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
    if 'authenticator_status' not in st.session_state:
        st.session_state.authenticator_status = None
    login()
    if st.session_state['authenticator_status']:
        run_reports()

