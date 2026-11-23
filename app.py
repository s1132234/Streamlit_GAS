import streamlit as st

st.set_page_config(page_title="附近揪團", page_icon="🍲")
st.title("附近揪團｜第 1 步：顯示活動")
st.write("先讓網頁顯示資料，還沒有連上雲端資料庫。")

# 活動資料：只存在這份程式裡，所以不會是多人共同資料
activities = [
    {"name": "社團迎新羽球團", "kind": "運動", "date": "週三 19:00", "host": "小明",
     "place": "學校體育館", "joined": 3, "capacity": 8},
    {"name": "宵夜吃鹹酥雞", "kind": "美食", "date": "週五 21:00", "host": "小美",
     "place": "夜市入口", "joined": 4, "capacity": 4},
]

# 搜尋與篩選
keyword = st.text_input("搜尋活動名稱")
kind_filter = st.selectbox("類別", ["全部", "美食", "桌遊", "運動", "其他"])
only_open = st.checkbox("只看還有名額的")

shown = 0
for activity in activities:
    if keyword and keyword not in activity["name"]:
        continue
    if kind_filter != "全部" and activity["kind"] != kind_filter:
        continue
    is_full = activity["joined"] >= activity["capacity"]
    if only_open and is_full:
        continue

    shown += 1
    with st.container(border=True):
        st.subheader(activity["name"])
        st.write(f"類別：{activity['kind']}　時間：{activity['date']}")
        st.write(f" 地點：{activity['place']}")
        st.write(f"主揪：{activity['host']}　名額：{activity['joined']} / {activity['capacity']}")
        if is_full:
            st.warning("已額滿")

if shown == 0:
    st.info("沒有符合條件的活動。")