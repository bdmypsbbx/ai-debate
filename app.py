import streamlit as st
from openai import OpenAI
import time
from datetime import datetime

# ==================== 1. 页面配置 + 自定义样式 ====================
st.set_page_config(page_title="我的智囊团 · 叠加态决策", layout="wide")

# 注入自定义 CSS：调大 chat_input 和 text_area 的字体
st.markdown("""
<style>
    /* 让 chat_input 字体变大 */
    .stChatInput textarea {
        font-size: 18px !important;
        line-height: 1.6 !important;
    }
    /* 让所有 text_area 输入框字体变大 */
    .stTextArea textarea {
        font-size: 18px !important;
        line-height: 1.6 !important;
    }
    /* 让所有 text_input 也变大 */
    .stTextInput input {
        font-size: 16px !important;
    }
    /* 让聊天消息里的文字更清晰 */
    .stChatMessage {
        font-size: 15px !important;
    }
    /* 编辑模式的输入框更大 */
    .edit-textarea textarea {
        font-size: 16px !important;
        line-height: 1.5 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 我的智囊团 · 叠加态决策")

# ==================== 2. 你的终身档案 ====================
USER_PROFILE = {
    "name": "我（26岁）",
    "age": "26",
    "gender": "女",
    "height": "165cm",
    "education": "211本科 · 安全工程（已放弃本专业）",
    "skills": "逻辑思维、系统思维、快速学习、从混乱中建立秩序",
    "current_status": "离职空窗期，正在重新寻找方向",
    "location": "中国二/三线城市（具体可根据补充）",
    "core_traits": """
【性格画像】
- 高开放性：喜欢学新东西、探索新工具
- 低外向性：喜欢独处、厌恶高频社交
- 高神经质（部分）：容易焦虑、对评判敏感
- 高尽责性（选择性）：对感兴趣的事高度投入
- 独立型自我构念：追求自主、不依赖外部认可

【决策风格】
- 依赖逻辑和系统思维
- 压力下容易预期性焦虑
- 需要可视化成果来获得能量
"""
}

# ==================== 3. 初始化状态 ====================
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
    st.session_state.current_session_id = None

if "phase" not in st.session_state:
    st.session_state.phase = "idle"

if "current_question" not in st.session_state:
    st.session_state.current_question = ""

if "questions" not in st.session_state:
    st.session_state.questions = []

if "answers" not in st.session_state:
    st.session_state.answers = {}

if "answer_texts" not in st.session_state:
    st.session_state.answer_texts = []

if "renaming_session" not in st.session_state:
    st.session_state.renaming_session = None

if "debate_history" not in st.session_state:
    st.session_state.debate_history = []

if "editing_msg" not in st.session_state:
    st.session_state.editing_msg = None

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("⚙️ 设置")

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

    # -------- 会话管理 --------
    st.subheader("📂 话题管理")

    if not st.session_state.sessions:
        sid = f"session_{int(time.time())}"
        st.session_state.sessions[sid] = {"name": "我的第一个话题", "messages": []}
        st.session_state.current_session_id = sid

    new_name = st.text_input("新话题名称", placeholder="输入名称")
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
            st.session_state.debate_history = []
            st.session_state.editing_msg = None
            st.rerun()

    st.divider()
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
                st.session_state.editing_msg = None
                st.rerun()

        with col3:
            if st.button("✏️", key=f"rename_{sid}"):
                st.session_state.renaming_session = sid
                st.rerun()

        with col4:
            if st.button("🗑️", key=f"del_{sid}"):
                if len(st.session_state.sessions) <= 1:
                    st.warning("至少保留一个话题")
                else:
                    del st.session_state.sessions[sid]
                    if st.session_state.current_session_id == sid:
                        st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]
                    st.rerun()

        if st.session_state.renaming_session == sid:
            new_name_input = st.text_input("新名称", value=sess['name'], key=f"rename_input_{sid}")
            col_rename_save, col_rename_cancel = st.columns(2)
            with col_rename_save:
                if st.button("✅ 保存", key=f"rename_save_{sid}"):
                    if new_name_input and new_name_input.strip():
                        st.session_state.sessions[sid]['name'] = new_name_input.strip()
                        st.session_state.renaming_session = None
                        st.rerun()
            with col_rename_cancel:
                if st.button("❌ 取消", key=f"rename_cancel_{sid}"):
                    st.session_state.renaming_session = None
                    st.rerun()

# ==================== 4. 获取当前会话 ====================
if not st.session_state.sessions:
    sid = f"session_{int(time.time())}"
    st.session_state.sessions[sid] = {"name": "我的第一个话题", "messages": []}
    st.session_state.current_session_id = sid

current_session = st.session_state.sessions.get(st.session_state.current_session_id)
if not current_session:
    st.warning("请新建或切换话题")
    st.stop()

# ==================== 5. 核心：生成追问 ====================
def generate_questions(question):
    prompt = f"""
你是审问官。用户提出了一个问题，但你对他的具体情况还不够了解。

【用户档案】
{USER_PROFILE['core_traits']}

【用户的问题】
{question}

【你的任务】
生成5个追问，目的是把用户的问题从「抽象」拉回「具体」。

追问的方向（根据问题类型灵活调整，不要机械套用）：
1. 用户在这个问题上的「具体处境」是什么？
2. 用户「真正担心/恐惧」的是什么？
3. 用户手中「有什么资源/筹码」？
4. 用户「最不能接受」的后果是什么？
5. 用户「希望达成的理想状态」是什么？

【输出格式】
直接输出5个问题，数字1-5开头。
问题必须具体、围绕用户个人情况，不要问泛泛的问题。
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
        return [f"⚠️ 生成追问失败：{str(e)[:50]}"]

# ==================== 6. 核心：单个角色发言 ====================
def call_role(role_name, role_identity, role_task, question, answers_dict, previous_speeches=""):
    answers_text = ""
    for i, (q, a) in enumerate(answers_dict.items(), 1):
        answers_text += f"【追问{i}】{q}\n【回答】{a}\n\n"

    previous_text = ""
    if previous_speeches:
        previous_text = f"\n【前面已经发表的言论（你必须认真阅读并回应）】：\n{previous_speeches}\n"

    prompt = f"""
你是【{role_name}】。

【你的身份】
{role_identity}

【你的核心任务】
{role_task}

【你必须时刻记住的用户信息】
{USER_PROFILE['core_traits']}

【用户提出的问题】
{question}

【用户对追问的回答】
{answers_text}
{previous_text}

【核心方法论：叠加态决策】
你的每一次分析，必须同时考虑两个层面，然后把它们叠加在一起：
1. 「用户这个人」：性格、经历、恐惧、价值观、资源
2. 「用户身处的现实」：社会规则、经济环境、文化背景、所在城市的实际情况

【发言铁律】
1. 不要说「你应该怎么做」，要说「基于你的情况，我建议考虑什么」
2. 必须区分「我确定的」和「我不确定的」。不确定的明确说出来。
3. 不要编造数据。如果引用经验，说「根据普遍经验」。
4. 结尾必须给出「可执行的下一步」。

【‼️ 关键词加粗规则】
在你的回答中，必须用 **加粗** 来突出以下内容：
- 核心结论
- 具体数字、金额、时间节点
- 行动指令
- 关键建议
- 风险警告
- 置信度百分比

【发言结构】
1. 针对用户个人情况的分析
2. 结合社会现实的分析
3. 对前面发言的回应（如果有）
4. 可执行的下一步
5. 我的不确定清单

现在开始发言。
"""
    try:
        resp = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.8,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ {role_name} 发言失败：{str(e)[:80]}"

# ==================== 7. 显示历史消息（支持编辑） ====================
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
        st.session_state.debate_history = []
        st.session_state.editing_msg = None
        st.rerun()

st.divider()

# -------- 显示消息列表（带编辑功能） --------
messages = current_session["messages"]

# 处理编辑状态
editing_target = st.session_state.editing_msg
if editing_target is not None:
    edit_sid, edit_idx = editing_target
    if edit_sid == st.session_state.current_session_id and edit_idx < len(messages):
        msg = messages[edit_idx]
        with st.container(border=True):
            st.markdown(f"**✏️ 编辑消息 ( {msg['role']} )**")
            new_content = st.text_area(
                "修改内容",
                value=msg["content"],
                height=200,
                key=f"edit_area_{edit_idx}",
                label_visibility="collapsed"
            )
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("✅ 保存修改", key=f"save_edit_{edit_idx}"):
                    if new_content and new_content.strip():
                        messages[edit_idx]["content"] = new_content.strip()
                        messages[edit_idx]["timestamp"] = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} (已编辑)"
                        st.session_state.editing_msg = None
                        st.rerun()
                    else:
                        st.warning("内容不能为空")
            with col_cancel:
                if st.button("❌ 取消编辑", key=f"cancel_edit_{edit_idx}"):
                    st.session_state.editing_msg = None
                    st.rerun()
        st.divider()

# 显示所有消息（除了正在编辑的那条）
for idx, msg in enumerate(messages):
    if st.session_state.editing_msg is not None:
        edit_sid, edit_idx = st.session_state.editing_msg
        if edit_sid == st.session_state.current_session_id and edit_idx == idx:
            continue

    with st.chat_message(msg["role"]):
        col_header, col_edit, col_delete = st.columns([10, 1, 1])
        with col_header:
            st.markdown(f"**{msg['role']}**  `{msg.get('timestamp', '')}`")
        with col_edit:
            if st.button("✏️", key=f"edit_btn_{idx}", help="编辑此消息"):
                st.session_state.editing_msg = (st.session_state.current_session_id, idx)
                st.rerun()
        with col_delete:
            if st.button("🗑️", key=f"del_btn_{idx}", help="删除此消息"):
                del messages[idx]
                if st.session_state.editing_msg is not None:
                    edit_sid, edit_idx = st.session_state.editing_msg
                    if edit_sid == st.session_state.current_session_id and edit_idx == idx:
                        st.session_state.editing_msg = None
                    elif edit_sid == st.session_state.current_session_id and edit_idx > idx:
                        st.session_state.editing_msg = (edit_sid, edit_idx - 1)
                st.rerun()

        st.markdown(msg["content"])

# ==================== 8. 交互流程 ====================

# -------- 阶段1：空闲状态 -> 使用 st.chat_input（回车发送，大字体） --------
if st.session_state.phase == "idle":
    user_input = st.chat_input("💬 输入你的问题（回车直接发送）...")
    if user_input and user_input.strip():
        current_session["messages"].append({
            "role": "我",
            "content": user_input.strip(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        st.session_state.current_question = user_input.strip()
        st.session_state.phase = "generating"
        st.session_state.answers = {}
        st.session_state.questions = []
        st.session_state.answer_texts = []
        st.session_state.debate_history = []
        st.rerun()

# -------- 阶段2：生成追问 --------
if st.session_state.phase == "generating":
    if not st.session_state.current_question:
        st.session_state.phase = "idle"
        st.warning("请先输入问题")
        st.rerun()
    else:
        with st.chat_message("审问官"):
            with st.spinner("生成追问中..."):
                qs = generate_questions(st.session_state.current_question)
                if qs and qs[0].startswith("⚠️"):
                    st.error(qs[0])
                    st.session_state.phase = "idle"
                    st.rerun()
                st.session_state.questions = qs
                st.session_state.answer_texts = [""] * len(qs)
                st.session_state.phase = "answering"
                q_text = "为了更深入了解你的情况，请回答以下5个问题：\n\n"
                for i, q in enumerate(qs, 1):
                    q_text += f"{i}. {q}\n"
                current_session["messages"].append({
                    "role": "审问官",
                    "content": q_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.rerun()

# -------- 阶段3：回答追问（使用 st.form，大字体，点击按钮提交） --------
if st.session_state.phase == "answering":
    st.info(f"📌 请回答以下 {len(st.session_state.questions)} 个问题")

    with st.form(key="answer_form", clear_on_submit=False):
        for i, q in enumerate(st.session_state.questions):
            answer = st.text_area(
                f"**问题 {i+1}**：{q}",
                value=st.session_state.answer_texts[i] if i < len(st.session_state.answer_texts) else "",
                height=80,
                key=f"answer_{i}",
                label_visibility="collapsed"
            )
            if i < len(st.session_state.answer_texts):
                st.session_state.answer_texts[i] = answer

        submitted = st.form_submit_button("🚀 提交全部回答", use_container_width=True)

    if submitted:
        empty_indices = []
        for i, ans in enumerate(st.session_state.answer_texts):
            if not ans or not ans.strip():
                empty_indices.append(i + 1)
        if empty_indices:
            st.warning(f"⚠️ 以下问题还未回答：{', '.join(map(str, empty_indices))}")
        else:
            for i, q in enumerate(st.session_state.questions):
                st.session_state.answers[q] = st.session_state.answer_texts[i]
                current_session["messages"].append({
                    "role": "我",
                    "content": f"【回答追问】{q}\n{st.session_state.answer_texts[i]}",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
            st.session_state.phase = "debating"
            st.session_state.debate_history = []
            st.rerun()

# -------- 阶段4：智囊团讨论 --------
if st.session_state.phase == "debating":
    roles = [
        {
            "name": "务实派·生存智者",
            "identity": "50岁，在人间摸爬滚打了一辈子的长辈。开过店、打过工、赔过钱、养过家。擅长把任何问题拆解成成本、收益、风险、时间。",
            "task": "用最实际的方式分析问题，告诉用户这件事在现实中具体怎么操作，最现实的限制条件是什么。不谈梦想，只谈现实。"
        },
        {
            "name": "远见派·系统构建者",
            "identity": "38岁，经历过多次人生转折的战略顾问。擅长把复杂问题拆解成阶段和节点，看5年后的发展轨迹。",
            "task": "画出这件事的发展时间线——1个月后、3个月后、1年后分别是什么状态。帮用户看到方向，而不是只盯着眼前。"
        },
        {
            "name": "风险派·现实审计师",
            "identity": "45岁，做过尽调、经历过暴雷的风险控制专家。不相信任何美好的可能性，只关心用户能否承受最坏的结果。",
            "task": "推演最坏情况，识别建议中的致命漏洞，给出止损红线。告诉用户：如果全搞砸了，你还能不能爬起来。"
        }
    ]

    max_rounds = 2
    total_speeches = len(roles) * max_rounds

    if len(st.session_state.debate_history) < total_speeches:
        current_index = len(st.session_state.debate_history)
        role_idx = current_index % len(roles)
        role = roles[role_idx]

        previous_speeches = ""
        if st.session_state.debate_history:
            recent = st.session_state.debate_history[-2:]
            for r in recent:
                previous_speeches += f"【{r['role']}】{r['content'][:300]}...\n\n"

        with st.chat_message(role["name"]):
            with st.spinner(f"{role['name']} 正在思考..."):
                reply = call_role(
                    role["name"],
                    role["identity"],
                    role["task"],
                    st.session_state.current_question,
                    st.session_state.answers,
                    previous_speeches
                )
                st.markdown(f"**{role['name']}**")
                st.markdown(reply)

                st.session_state.debate_history.append({
                    "role": role["name"],
                    "content": reply,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                current_session["messages"].append({
                    "role": role["name"],
                    "content": reply,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })

        if len(st.session_state.debate_history) >= total_speeches:
            st.session_state.phase = "summarizing"
        st.rerun()

    else:
        st.session_state.phase = "summarizing"
        st.rerun()

# -------- 阶段5：董秘总结 --------
if st.session_state.phase == "summarizing":
    all_speeches = ""
    for entry in st.session_state.debate_history:
        all_speeches += f"【{entry['role']}】{entry['content']}\n\n"

    with st.chat_message("董秘"):
        with st.spinner("董秘正在整理..."):
            prompt = f"""
你是董秘，负责把三位智囊的讨论总结成一份「老板能直接看」的决策清单。

【用户的问题】
{st.session_state.current_question}

【三位的完整讨论】
{all_speeches}

【你的任务】
1. 提炼共识：三位智囊在哪些问题上达成了一致？
2. 指出分歧：分歧点在哪里？你倾向于哪一边？
3. 给出3条明确的、可执行的建议
4. 标注每条建议的置信度
5. 列出「需要用户自己去验证的事情」

【‼️ 关键词加粗规则】
必须用 **加粗** 突出：三条核心建议、具体数字/时间、置信度、关键行动指令、风险警告。

【输出格式】
## 📋 决策清单

### 三位智囊的共识

### 分歧点

### 三条建议
1. **建议一**：（内容）（置信度：XX%）
2. **建议二**：（内容）（置信度：XX%）
3. **建议三**：（内容）（置信度：XX%）

### 你需要自己去验证的事情
1. 
2. 
3. 
"""
            try:
                resp = client.chat.completions.create(
                    model="deepseek-ai/DeepSeek-V3",
                    messages=[{"role": "system", "content": prompt}],
                    temperature=0.6,
                )
                summary = resp.choices[0].message.content
                st.markdown(summary)
                current_session["messages"].append({
                    "role": "董秘",
                    "content": summary,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.session_state.phase = "done"
                st.rerun()
            except Exception as e:
                st.error(f"总结失败：{str(e)[:80]}")
                st.session_state.phase = "done"
                st.rerun()

# -------- 阶段6：完成（使用 st.chat_input，回车发送） --------
if st.session_state.phase == "done":
    st.success("✅ 讨论完成！可以问下一个问题。")
    user_input = st.chat_input("💬 输入下一个问题（回车发送）...")
    if user_input and user_input.strip():
        current_session["messages"].append({
            "role": "我",
            "content": user_input.strip(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        st.session_state.current_question = user_input.strip()
        st.session_state.phase = "generating"
        st.session_state.answers = {}
        st.session_state.questions = []
        st.session_state.answer_texts = []
        st.session_state.debate_history = []
        st.rerun()
