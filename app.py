import streamlit as st
from openai import OpenAI
import time
from datetime import datetime

# ==================== 1. 页面配置 ====================
st.set_page_config(page_title="终身智囊团", layout="wide")
st.title("🧠 我的终身决策智囊团")

# ==================== 2. 你的终身档案（写死） ====================
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

# ==================== 3. 初始化状态（全部从 session_state 读取） ====================
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
    st.session_state.answers = {}

if "answer_index" not in st.session_state:
    st.session_state.answer_index = 0

if "last_user_input" not in st.session_state:
    st.session_state.last_user_input = ""  # 记录上一次用户提交的内容，防止重复触发

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("⚙️ 设置")
    try:
        api_key = st.secrets["SILICONFLOW_API_KEY"]
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

    # 会话管理
    st.subheader("📂 话题")
    if not st.session_state.sessions:
        sid = f"session_{int(time.time())}"
        st.session_state.sessions[sid] = {"name": "我的第一个话题", "messages": []}
        st.session_state.current_session_id = sid

    new_name = st.text_input("新话题名称")
    if st.button("➕ 新建话题"):
        sid = f"session_{int(time.time())}"
        st.session_state.sessions[sid] = {"name": new_name or f"未命名{len(st.session_state.sessions)+1}", "messages": []}
        st.session_state.current_session_id = sid
        # 【关键修复】新建话题时，强制重置所有状态为 idle
        st.session_state.phase = "idle"
        st.session_state.current_question = ""
        st.session_state.questions = []
        st.session_state.answers = {}
        st.session_state.answer_index = 0
        st.session_state.last_user_input = ""
        st.rerun()

    st.divider()
    for sid, sess in list(st.session_state.sessions.items())[::-1]:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            if sid == st.session_state.current_session_id:
                st.markdown(f"**👉 {sess['name']}**")
            else:
                st.markdown(sess['name'])
        with col2:
            if st.button("切换", key=f"sw_{sid}"):
                st.session_state.current_session_id = sid
                # 【关键修复】切换话题时，强制重置为 idle
                st.session_state.phase = "idle"
                st.session_state.current_question = ""
                st.session_state.questions = []
                st.session_state.answers = {}
                st.session_state.answer_index = 0
                st.session_state.last_user_input = ""
                st.rerun()
        with col3:
            if st.button("删", key=f"del_{sid}"):
                del st.session_state.sessions[sid]
                if st.session_state.current_session_id == sid:
                    st.session_state.current_session_id = list(st.session_state.sessions.keys())[0] if st.session_state.sessions else None
                st.session_state.phase = "idle"
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

# ==================== 5. AI 函数（加了错误友好提示） ====================
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
            qs.append("还有什么关键信息？")
        return qs[:5]
    except Exception as e:
        # 【关键修复】返回友好提示，而不是乱码
        return [f"⚠️ 生成追问失败：{str(e)[:50]}...", "请检查 API Key 是否正确", "或者稍后重试"]

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
    if st.button("📥 导出"):
        export = f"# {current_session['name']}\n"
        for msg in current_session["messages"]:
            export += f"### {msg['role']} ({msg.get('timestamp','')})\n{msg['content']}\n\n"
        st.download_button("下载", data=export, file_name=f"{current_session['name']}.md")
with col2:
    if st.button("🗑️ 清空"):
        current_session["messages"] = []
        st.session_state.phase = "idle"
        st.session_state.current_question = ""
        st.session_state.questions = []
        st.session_state.answers = {}
        st.session_state.answer_index = 0
        st.session_state.last_user_input = ""
        st.rerun()

st.divider()

for msg in current_session["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(f"**{msg['role']}**  `{msg.get('timestamp', '')}`")
        st.markdown(msg["content"])

# ==================== 7. 输入与处理 ====================
def get_placeholder():
    if st.session_state.phase == "idle":
        return "💬 输入你的决策问题（例：我该不该转行？）"
    elif st.session_state.phase == "answering":
        if st.session_state.answer_index < len(st.session_state.questions):
            q = st.session_state.questions[st.session_state.answer_index]
            return f"📌 回答追问 {st.session_state.answer_index+1}/{len(st.session_state.questions)}：{q}"
        return "⏳ 请稍候..."
    elif st.session_state.phase == "done":
        return "✅ 分析完成，输入新问题"
    return "⏳ 处理中..."

with st.form(key="main_form", clear_on_submit=True):
    user_input = st.text_area(
        label="输入框",
        placeholder=get_placeholder(),
        height=80,
        label_visibility="collapsed"
    )
    submitted = st.form_submit_button("🚀 发送")

# ---------- 【关键修复】处理提交时，增加防护 ----------
if submitted and user_input and user_input.strip():
    text = user_input.strip()
    
    # 防止重复提交同样的内容
    if text == st.session_state.last_user_input and st.session_state.phase != "idle":
        st.info("⏳ 已收到，请稍候...")
    else:
        st.session_state.last_user_input = text
        
        # 情况1：空闲状态 -> 开始审问
        if st.session_state.phase == "idle":
            st.session_state.current_question = text
            st.session_state.phase = "generating"
            st.rerun()
        
        # 情况2：回答追问阶段
        elif st.session_state.phase == "answering":
            if st.session_state.answer_index < len(st.session_state.questions):
                q = st.session_state.questions[st.session_state.answer_index]
                st.session_state.answers[q] = text
                st.session_state.answer_index += 1
                current_session["messages"].append({
                    "role": "我",
                    "content": f"【回答追问】{q}\n{text}",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                if st.session_state.answer_index >= len(st.session_state.questions):
                    st.session_state.phase = "debating"
                st.rerun()
            else:
                st.warning("所有问题已回答完毕，正在生成分析...")
                st.session_state.phase = "debating"
                st.rerun()
        
        # 情况3：完成状态 -> 新问题
        elif st.session_state.phase == "done":
            st.session_state.current_question = text
            st.session_state.phase = "generating"
            st.session_state.answers = {}
            st.session_state.questions = []
            st.session_state.answer_index = 0
            st.rerun()

# ---------- 【关键修复】自动流程：加上前置条件守卫 ----------
# 只有在 phase 为 generating 且 current_question 不为空时，才执行生成
if st.session_state.phase == "generating":
    if not st.session_state.current_question or not st.session_state.current_question.strip():
        # 如果 current_question 为空，说明是异常状态，强制回到 idle
        st.session_state.phase = "idle"
        st.warning("请先输入问题再开始分析")
        st.rerun()
    else:
        with st.chat_message("审问官"):
            with st.spinner("正在生成5个关键追问..."):
                qs = generate_questions(st.session_state.current_question)
                # 检查是否生成失败（返回了错误信息）
                if qs and qs[0].startswith("⚠️"):
                    st.error(qs[0])
                    st.session_state.phase = "idle"
                    st.rerun()
                st.session_state.questions = qs
                st.session_state.answers = {}
                st.session_state.answer_index = 0
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

# ---------- debating 阶段：也加上守卫 ----------
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

# ---------- done 状态 ----------
if st.session_state.phase == "done":
    st.success("✅ 分析完成，可以输入新问题继续讨论。")