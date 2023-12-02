import streamlit as st
import altair as alt
# from streamlit_extras.stylable_container import stylable_container
from PIL import Image
from tools.streamlit_tools import execute_query
from tools.login import login



 
 


def get_text(type):
    res = execute_query(f"SELECT msg_text FROM t_tips WHERE msg_type = '{type}' AND valid_to ='3000-12-31'", return_type="df")
    return res.iloc[0]['msg_text']
    
def change_text(type, msg):
    execute_query(f"call p_change_tips('{type}','{msg}')", return_type="df")


def run_reports():
   
    # st.empty
    colx, coly, colz = st.columns([5, 10, 3])
    image = Image.open('.streamlit//logo.png')
    colx.image(image, width=150)
    coly.title('Wzgórze Wisielców  \n\n', anchor='main')
    with colz as x:
        last_refresh_date()
    
    check_nick_name_change()
    
    st.subheader("  ##  Filtr (suwak) po dacie  ## ")
    Report_Date_list = [ 
         row[0]
        for row in execute_query(
            f'''select distinct 
CAST(report_date as CHAR(10))|| CASE 
	WEEKDAY(report_date) 
	when 0 then '  (Poniedziałek)'
	when 1 then '  (Wtorek)'
	when 2 then '  (Środa)'
	when 3 then '  (Czwartek)'
	when 4 then '  (Piątek)'
	when 5 then '  (Sobota)'
	when 6 then '  (Niedziela)'
END report_date
from V_WG 
order by 1''', return_type="list"
        )
    ]
    while  len(Report_Date_list)<2:
        Report_Date_list.append("_empty")
    date_filter = st.select_slider(label="Select a report date", options=Report_Date_list, value=max(Report_Date_list), label_visibility="hidden")


    if date_filter != "--":
        st.text("\n\n\n")
        wg_reports(date_filter)
        st.text("\n\n\n")
        gpch_reports(date_filter)
        st.text("\n\n\n")
        guild_stats(date_filter)


def last_refresh_date():
    query = f'SELECT MAX(last_update_date) AS last_update_date FROM t_log'
    text_var = execute_query(query=query, return_type="df")
    st.markdown(f"<h7 style='text-align: center; color: grey;'><center>Data ostatniego odświeżenia raportu:<br><b>{str(text_var['last_update_date'].iloc[0])}</b></center></h7>", unsafe_allow_html=True) 
    
  

def wg_reports(date_filter):
    st.subheader('Wyprawy Gildyjne  \n  \n',anchor='wg',  divider='rainbow')
    wg_result_all = execute_query(
        f'''select 
                report_date
                , name as "Player_name"
                , Age_PL as "Epoka"
                , wg_date_of_day as "WG_day"
                , expeditionPoints
                , solvedEncounters AS "Wygrane_bitwy"
                ,  "WG_LEVEL"
                , "forecast"
from V_WG where report_date = '{date_filter}' 
''',
        return_type="df",
    )
    wg_result_catch = execute_query(
        f'''select 
                report_date
                , name as "Player_name"
                , Age_PL as "Epoka"
                , wg_date_of_day as "WG_day"
                , expeditionPoints
                , solvedEncounters AS "Wygrane_bitwy"
                ,  WG_LEVEL
                , "forecast"
from V_WG where report_date = '{date_filter}' 
AND solvedEncounters < "forecast" ''',
        return_type="df",
    )

    
    if (wg_result_all.iloc[0]['WG_day'] <7 and wg_result_all.iloc[0]['WG_day'] >0): 
        st.markdown(f"*Wyprawy Gildyjne* są :large_green_circle::large_green_circle: :green[w trakcie] :large_green_circle::large_green_circle: day({wg_result_all.iloc[0]['WG_day']}).")
    else:  
        st.markdown("*Wyprawy Gildyjne* są :red_circle: :red[zakończone] :red_circle:.")
        
    col1, col2 = st.columns([1, 1])

    bar1 = alt.Chart(wg_result_all).mark_bar().encode(
    x=alt.X("Player_name", title='Nick Gracza'),
    y=alt.Y("Wygrane_bitwy", title='Wygrane bitwy'),
    color="WG_LEVEL",
    tooltip=["Player_name", "Epoka", "WG_LEVEL", "Wygrane_bitwy"]
    ).properties(
        title='Statystyka edycji WG',
        width=alt.Step(40)  # controls width of bar.
    ).interactive()
    
    tick1 = alt.Chart(wg_result_all).mark_tick(
        color='red',
        thickness=2,
        size=40 * 0.45,  # controls width of tick.
    ).encode(
        x="Player_name",
        y="forecast"
    )
 
    ## drugi wykres
    
    bar2 = alt.Chart(wg_result_catch).mark_bar(color='#e8513a').encode(
    x=alt.X("Player_name", title='Nick Gracza'),
    y=alt.Y("Wygrane_bitwy", title='Wygrane bitwy'),
    tooltip=["Player_name", "Epoka", "WG_LEVEL", "Wygrane_bitwy"]
    ).properties(
        title='Warto skontaktować się z',
        width=alt.Step(40)  # controls width of bar.
    ).interactive()

    tick2 = alt.Chart(wg_result_catch).mark_tick(
        color='#47b552',
        thickness=2,
        size=40 * 0.45,  # controls width of tick.
    ).encode(
        x="Player_name",
        y="forecast"
    )
    col1.altair_chart(bar1 + tick1, use_container_width=True)
    col2.altair_chart(bar2 + tick2, theme="streamlit", use_container_width=True)
    # col1.bar_chart(wg_result_all, x="Player_name", y= "Wygrane_bitwy" )
    #col2.bar_chart(wg_result_catch, x="Player_name", y= "Wygrane_bitwy", color="#f24951" )

def gpch_reports(date_filter):
    st.subheader('Pola Chwały  \n  \n', anchor='gpch', divider='rainbow')
    gpch_result_all = execute_query(
        f'''select 
                report_date
                , name as "Player_name"
                , Age_PL as "Epoka"
                , GPCH_DATE_OF_DAY as "GPCH_day"
                , "RANK"
                , battlesWon
                , negotiationsWon
                , score AS "Wygrane_bitwy"
                , "Forecast"
from V_GPCH where report_date = '{date_filter}' 
''',
        return_type="df",
    )
    gpch_result_catch = execute_query(
        f'''select 
                report_date
                , name as "Player_name"
                , Age_PL as "Epoka"
                , GPCH_DATE_OF_DAY as "GPCH_day"
                , "RANK"
                , battlesWon
                , negotiationsWon
                , score AS "Wygrane_bitwy"
                , forecast
from V_GPCH 
where 
report_date = '{date_filter}' 
AND score < forecast
''',
        return_type="df",
    )
    if (gpch_result_all.iloc[0]['GPCH_day'] <12 and gpch_result_all.iloc[0]['GPCH_day']>0): 
        st.markdown(f"*Pola Chwały* są :large_green_circle::large_green_circle: :green[w trakcie] :large_green_circle::large_green_circle: day({gpch_result_all.iloc[0]['GPCH_day']}).")
    else:  
        st.markdown("*Pola Chwały* są :red_circle: :red[zakończone] :red_circle:.")
    col1, col2 = st.columns([1, 1])
    
    bar1 = alt.Chart(gpch_result_all).mark_bar().encode(
    x=alt.X("Player_name", title='Nick Gracza'),
    y=alt.Y("Wygrane_bitwy", title='Wygrane bitwy'),
    tooltip=["Player_name", "Epoka", "battlesWon", "negotiationsWon"]
    ).properties(
        title='Statystyka edycji GPCh',
        width=alt.Step(40)  # controls width of bar.
    ).interactive()
    
    tick1 = alt.Chart(gpch_result_all).mark_tick(
        color='red',
        thickness=2,
        size=40 * 0.45,  # controls width of tick.
    ).encode(
        x="Player_name",
        y="forecast"
    )
    
    bar2 = alt.Chart(gpch_result_catch).mark_bar(color='#e8513a').encode(
    x=alt.X("Player_name", title='Nick Gracza'),
    y=alt.Y("Wygrane_bitwy", title='Wygrane bitwy'),
    tooltip=["Player_name", "Epoka", "battlesWon", "negotiationsWon"]
    ).properties(
        title='Warto skontaktować się z',
        width=alt.Step(40)  # controls width of bar.
    ).interactive()
    
    tick2 = alt.Chart(gpch_result_catch).mark_tick(
        color='#47b552',
        thickness=2,
        size=40 * 0.45,  # controls width of tick.
    ).encode(
        x="Player_name",
        y="forecast"
    )
    
    col1.altair_chart(bar1 + tick1, use_container_width=True)
    col2.altair_chart(bar2 + tick2, theme="streamlit", use_container_width=True)
    # col1.bar_chart(gpch_result_all, x="Player_name", y= "Wygrane_bitwy" )
    # col2.bar_chart(gpch_result_catch, x="Player_name", y= "Wygrane_bitwy" , color="#f24951" )

def guild_stats(date_filter):
    st.subheader('Statystyki Gildii', anchor='guild', divider='rainbow')

    guild_stats_sql = execute_query(
        f'''SELECT 
	"RANK" AS "Rank"
	, NAME AS "Nick gracza"
	, Age_PL "Epoka"
	, won_battles "Wygrane bitwy"
	, SCORE "Punkty"
	, TITLE "Tytuł"
	, JOIN_DATE "Data przyłączenia"
	, leave_date AS  "Data opuszczenia"
FROM 
	V_GUILD_PLAYERS
WHERE 
	'{date_filter}'  BETWEEN valid_from  AND valid_to
ORDER BY "RANK"
''',
        return_type="df"
    )

    st.dataframe(guild_stats_sql, use_container_width=True, hide_index=True)

def check_nick_name_change():
    qry = execute_query(f'''SELECT 
                        old_name AS "Poprzedni nick"
                        , name as "Obecny nick"
                        , valid_to
                        FROM 
                        (
                            SELECT 
                                name  
                                , lag(name) OVER (partition by player_id ORDER BY player_id) old_name
                                , valid_to
                            from 
                                V_GUILD_PLAYERS
                            where 
                                player_id in (select player_id FROM V_GUILD_PLAYERS WHERE valid_to = '3000-12-31')
                                
                        ) x 
                        WHERE name <> old_name and old_name is not null
                        ''', return_type="df")
    if not qry.empty:
        st.warning('Poniżej gracze którzy zmienili nick', icon="⚠️")
        st.dataframe(qry, hide_index=True, use_container_width=True)

        
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
    if 'authenticator_status' not in st.session_state:
        st.session_state.authenticator_status = None
    login()
    if st.session_state['authenticator_status']:
        run_reports()


    
    
    