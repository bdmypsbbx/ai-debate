import streamlit as st
from openai import OpenAI
import time
from datetime import datetime

# ==================== 1. 页面配置 ====================
st.set_page_config(page_title="终身智囊团", layout="wide")
st.title("🧠 我的终身决策智囊团")

# ==================== 2. 你的终身档案 ====================
USER_PROFILE = {
    "name": "我（26岁）",
    "age": "26",
    "gender": "女",
    "height": "165cm",
    "education": "211本科 · 安全工程",
    "skills": "擅长从混乱中建立秩序、从0到1快速创造、逻辑思维",
    "current_status": "离职空窗期，存款有限，急需确定职业方向",
    "long_term_goal": "找到低社交消耗、有创造空间、收入可持续的工作",
    "core_traits": "高开放性、低外向性、厌恶高频社交。偏好短周期、高强度、自主性工作。厌恶重复枯燥。决策依赖逻辑，压力下易焦虑。"
}

# ==================== 3. 初始化状态 ====================
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
    st.session_state.current_session_id = None

if "phase" not in st.session_state:
    st.session_state.phase = "idle"  # idle | generating | answering | debating | done

if "current_question" not in st.session_state:
    st.session_state.current_question = ""

if "questions" not in st.session_state:
    st.session_state.questions = []

if "answers" not in st.session_state:
    st.session_state.answers = {}  # {question: answer}

# 新增：存储用户的回答列表（一次性回答所有追问）
if "answer_texts" not in st.session_state:
    st.session_state.answer_texts = []  # 与 questions 一一对应

if "renaming_session" not in st.session_state:
    st.session_state.renaming_session = None

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("⚙️ 设置")

    # API Key 获取
    try:
        api_key = st.secrets["SILICONFLOW_API_KEY"]
        st.success("✅ 已从 Secrets 读取 API Key")
    except:
        api_key = st.text_input("请输入硅基流动 API Key", type="password")
        if not api_key:
            st.warning("请输入 API Key")
            st.stop()

    client = OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1")
    st.divider()

    st.subheader("👤 我的档案")
    st.markdown(f"- 年龄：{USER_PROFILE['age']}岁\n- 学历：{USER_PROFILE['education']}\n- 状态：{USER_PROFILE['current_status']}")
    with st.expander("🧠 性格画像"):
        st.markdown(USER_PROFILE['core_traits'])
    st.divider()

    # -------- 会话管理（支持重命名） --------
    st.subheader("📂 话题管理")

    if not st.session_state.sessions:
        sid = f"session_{int(time.time())}"
        st.session_state.sessions[sid] = {"name": "我的第一个话题", "messages": []}
        st.session_state.current_session_id = sid

    # 新建话题
    new_name = st.text_input("新话题名称", placeholder="输入名称，再点 ➕")
    col_new, col_new_btn = st.columns([3, 1])
    with col_new_btn:
        if st.button("➕ 新建", use_container_width=True):
            if new_name and new_name.strip():
                sid = f"session_{int(time.time())}"
                st.session_state.sessions[sid] = {"name": new_name.strip(), "messages": []}
                st.session_state.current_session_id = sid
                st.session_state.phase = "idle"
                st.session_state.current_question = ""
                st.session_state.questions = []
                st.session_state.answers = {}
                st.session_state.answer_texts = []
                st.rerun()
            else:
                st.warning("请输入名称")

    st.divider()

    # 话题列表（每个话题带 切换 / 重命名 / 删除）
    st.subheader("📋 话题列表")
    for sid, sess in list(st.session_state.sessions.items())[::-1]:
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

        with col1:
            if sid == st.session_state.current_session_id:
                st.markdown(f"**👉 {sess['name']}**")
            else:
                st.markdown(sess['name'])

        with col2:
            if st.button("切换", key=f"sw_{sid}"):
                st.session_state.current_session_id = sid
                st.session_state.phase = "idle"
                st.session_state.current_question = ""
                st.session_state.questions = []
                st.session_state.answers = {}
                st.session_state.answer_texts = []
                st.rerun()

        with col3:
            if st.button("✏️", key=f"rename_{sid}", help="重命名"):
                st.session_state.renaming_session = sid
                st.rerun()

        with col4:
            if st.button("🗑️", key=f"del_{sid}", help="删除"):
                if len(st.session_state.sessions) <= 1:
                    st.warning("至少保留一个话题")
                else:
                    del st.session_state.sessions[sid]
                    if st.session_state.current_session_id == sid:
                        st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]
                    st.session_state.phase = "idle"
                    st.rerun()

        # 如果当前话题正在重命名，显示输入框
        if st.session_state.renaming_session == sid:
            new_name_input = st.text_input("新名称", value=sess['name'], key=f"rename_input_{sid}")
            col_rename_save, col_rename_cancel = st.columns(2)
            with col_rename_save:
                if st.button("✅ 保存", key=f"rename_save_{sid}"):
                    if new_name_input and new_name_input.strip():
                        st.session_state.sessions[sid]['name'] = new_name_input.strip()
                        st.session_state.renaming_session = None
                        st.rerun()
                    else:
                        st.warning("名称不能为空")
            with col_rename_cancel:
                if st.button("❌ 取消", key=f"rename_cancel_{sid}"):
                    st.session_state.renaming_session = None
                    st.rerun()

# ==================== 4. 获取当前会话 ====================
if not st.session_state.sessions:
    sid = f"session_{int(time.time())}"
    st.session_state.sessions[sid] = {"name": "我的第一个话题", "messages": []}
    st.session_state.current_session_id = sid
    st.session_state.phase = "idle"

current_session = st.session_state.sessions.get(st.session_state.current_session_id)
if not current_session:
    st.warning("请新建或切换话题")
    st.stop()

# ==================== 5. AI 函数 ====================
def generate_questions(question):
    if not question or not question.strip():
        return ["请先输入你的问题"]
    prompt = f"""
你是审问官。用户有问题但信息不够。
【档案】{USER_PROFILE['core_traits']}
【问题】{question}
生成5个关键追问，挖出资金、时间、恐惧、底限。
直接输出5个问题，数字1-5开头。
"""
    try:
        resp = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
        )
        raw = resp.choices[0].message.content
        qs = []
        for line in raw.split("\n"):
            line = line.strip()
            if line and any(line.startswith(str(i)) for i in range(1, 10)):
                clean = line[1:].strip()
                if clean.startswith(".") or clean.startswith("、"): 
                    clean = clean[1:].strip()
                qs.append(clean)
        while len(qs) < 5:
            qs.append("还有什么关键信息需要补充？")
        return qs[:5]
    except Exception as e:
        return [f"⚠️ 生成追问失败：{str(e)[:50]}...", "请检查 API Key 是否正确", "或稍后重试"]

def call_ai(question, answers_dict):
    if not question or not question.strip():
        return "❌ 问题不能为空"
    answers_text = ""
    for i, (q, a) in enumerate(answers_dict.items(), 1):
        answers_text += f"【追问{i}】{q}\n【回答】{a}\n\n"
    prompt = f"""
你是智囊团。已了解全部信息。
【档案】{USER_PROFILE['core_traits']}
【问题】{question}
【补充】{answers_text}
从三角度分析：激进扩张派、保守防御派、理性数据派。最后董秘给3条结论。标注置信度。不给情绪价值。
"""
    try:
        resp = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.65,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ 分析失败：{str(e)[:100]}"

# ==================== 6. 显示历史消息 ====================
st.subheader(f"💬 {current_session['name']}")

col1, col2 = st.columns(2)
with col1:
    if st.button("📥 导出 Markdown"):
        export = f"# {current_session['name']}\n导出时间：{datetime.now()}\n\n"
        for msg in current_session["messages"]:
            export += f"### {msg['role']} ({msg.get('timestamp','')})\n{msg['content']}\n\n"
        st.download_button("点击下载", data=export, file_name=f"{current_session['name']}.md")
with col2:
    if st.button("🗑️ 清空对话"):
        current_session["messages"] = []
        st.session_state.phase = "idle"
        st.session_state.current_question = ""
        st.session_state.questions = []
        st.session_state.answers = {}
        st.session_state.answer_texts = []
        st.rerun()

st.divider()

# 显示历史消息
for msg in current_session["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(f"**{msg['role']}**  `{msg.get('timestamp', '')}`")
        st.markdown(msg["content"])

# ==================== 7. 核心交互流程 ====================

# -------- 阶段1：空闲状态 -> 输入问题（回车即发送） --------
if st.session_state.phase == "idle":
    # 使用 st.chat_input，回车直接发送，文字大小默认舒适
    user_input = st.chat_input("💬 输入你的决策问题（回车发送）...")
    if user_input and user_input.strip():
        st.session_state.current_question = user_input.strip()
        st.session_state.phase = "generating"
        st.session_state.answers = {}
        st.session_state.questions = []
        st.session_state.answer_texts = []
        st.rerun()

# -------- 阶段2：生成追问（自动） --------
if st.session_state.phase == "generating":
    if not st.session_state.current_question:
        st.session_state.phase = "idle"
        st.warning("请先输入问题")
        st.rerun()
    else:
        with st.chat_message("审问官"):
            with st.spinner("正在生成5个关键追问..."):
                qs = generate_questions(st.session_state.current_question)
                if qs and qs[0].startswith("⚠️"):
                    st.error(qs[0])
                    st.session_state.phase = "idle"
                    st.rerun()
                st.session_state.questions = qs
                st.session_state.answer_texts = [""] * len(qs)  # 初始化空答案列表
                st.session_state.phase = "answering"
                q_text = "为了更深入了解，请回答以下5个问题：\n\n"
                for i, q in enumerate(qs, 1):
                    q_text += f"{i}. {q}\n"
                current_session["messages"].append({
                    "role": "审问官",
                    "content": q_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.rerun()

# -------- 阶段3：回答追问（一次性展示所有问题，一次性提交） --------
if st.session_state.phase == "answering":
    st.info(f"📌 请回答以下 {len(st.session_state.questions)} 个问题，回答完毕后点击底部按钮提交")

    # 使用 form 包裹所有输入框，一次提交全部答案
    with st.form(key="answer_form", clear_on_submit=False):
        # 动态生成每个问题的输入框
        for i, q in enumerate(st.session_state.questions):
            # 使用 text_area 让用户可以写长回答
            answer = st.text_area(
                f"**问题 {i+1}**：{q}",
                value=st.session_state.answer_texts[i] if i < len(st.session_state.answer_texts) else "",
                height=80,
                key=f"answer_{i}",
                placeholder=f"请回答第 {i+1} 个问题..."
            )
            # 实时保存到 session_state
            if i < len(st.session_state.answer_texts):
                st.session_state.answer_texts[i] = answer

        # 提交按钮
        submitted = st.form_submit_button("🚀 提交全部回答", use_container_width=True)

    if submitted:
        # 检查是否所有问题都已回答
        empty_indices = []
        for i, ans in enumerate(st.session_state.answer_texts):
            if not ans or not ans.strip():
                empty_indices.append(i + 1)
        if empty_indices:
            st.warning(f"⚠️ 以下问题还未回答：{', '.join(map(str, empty_indices))}")
        else:
            # 保存所有回答
            for i, q in enumerate(st.session_state.questions):
                st.session_state.answers[q] = st.session_state.answer_texts[i]
                # 逐条记录到消息历史
                current_session["messages"].append({
                    "role": "我",
                    "content": f"【回答追问】{q}\n{st.session_state.answer_texts[i]}",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
            # 进入辩论阶段
            st.session_state.phase = "debating"
            st.rerun()

# -------- 阶段4：辩论（自动） --------
if st.session_state.phase == "debating":
    if not st.session_state.current_question:
        st.session_state.phase = "idle"
        st.warning("问题丢失，请重新输入")
        st.rerun()
    else:
        with st.chat_message("智囊团"):
            with st.spinner("三位高管正在激烈讨论..."):
                reply = call_ai(st.session_state.current_question, st.session_state.answers)
                if reply.startswith("❌"):
                    st.error(reply)
                    st.session_state.phase = "idle"
                    st.rerun()
                st.markdown(reply)
                current_session["messages"].append({
                    "role": "智囊团",
                    "content": reply,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.session_state.phase = "done"
                st.rerun()

# -------- 阶段5：完成 --------
if st.session_state.phase == "done":
    st.success("✅ 分析完成！输入新问题即可继续讨论。")
    user_input = st.chat_input("💬 输入新问题（回车发送）...")
    if user_input and user_input.strip():
        st.session_state.current_question = user_input.strip()
        st.session_state.phase = "generating"
        st.session_state.answers = {}
        st.session_state.questions = []
        st.session_state.answer_texts = []
        st.rerun()
