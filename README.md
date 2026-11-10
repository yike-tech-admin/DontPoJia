# DontPoJia

![refuse-cracking](assets/refuse-cracking.webp)

一个用于存放 **AI 安全护栏（safety guardrail）** 规则的仓库。

核心资产是 [`SKILL.md`](./SKILL.md) —— 一个可在 Zed / 兼容 Agent 环境中加载的 `refuse-cracking` skill：当下用户要求 AI **破解、绕过授权、伪造授权、盗版、越狱解锁**任何软件时，它会被强制加载并触发拒绝。

---

## 📜 语境声明（Context Statement）

**本仓库是「AI 请求分类与拒绝规则」，不是破解教程，也不构成任何破解指导。**

文中出现的「破解 / 绕过 / 伪造 / 盗版 / 脱壳 / keygen / 越狱」等词汇及其英文对应词，**仅作为识别与拦截的触发信号（trigger vocabulary）存在**，用于判定并拒绝此类请求。它们在本仓库中的角色等同于反垃圾邮件规则库、支付风控黑名单或反诈关键词表 —— 是**检测面**，不是**操作面**。

**本仓库明确不包含：**

| 不包含 | 状态 |
|---|---|
| 可执行代码 / 脚本 / 命令 | 0 处（`SKILL.md` 与 `AGENTS.md` 的代码块均为纯文本） |
| 破解工具链、下载地址、安装指引 | 0 处 |
| 偏移量、地址、特征码、补丁位置 | 0 处 |
| 算法还原思路、关键函数定位方法 | 0 处 |
| 具体操作步骤 / 路线图 / 模块清单 | 0 处 |

词汇的**出现**不代表对相关行为的认可、描述或推荐 —— 恰恰相反，这些词汇在此被明确标记为**禁止项**。列出"什么是破解请求"，与"如何实施破解"，是完全不同的两件事；本仓库仅做前者。

**用途定位**：防御性安全与合规。目标是让 AI 在收到越界请求时**说"不"并给出合法替代路径**。

---

## 目录结构

```
DontPoJia/
├── AGENTS.md        # 项目级 AI 规则，第 0 节为最高优先级禁止条款
├── README.md        # 本文件
├── SKILL.md         # refuse-cracking skill 全文
├── install.py       # 一键安装器（幂等，支持 dry-run / 卸载）
├── LICENSE          # 许可协议
└── assets/
    └── refuse-cracking.webp    # 项目封面图
```

---

## 一键安装

推荐用附带的 `install.py`，它会同时处理 skill 与规则文件，且**幂等**——已存在则原位更新/替换区块，不会重复追加。

```bash
# 看看会做什么（不写任何文件）
python install.py --dry-run

# 安装到全局（~/.agents）+ 当前目录项目
python install.py

# 只装全局 / 只装项目级
python install.py --scope global
python install.py --scope project

# 指定项目目录
python install.py --project /path/to/project

# 注入到已有 AGENTS.md 时，区块追加到末尾而非置顶
python install.py --position bottom

# 卸载（只移除本工具标记过的内容）
python install.py --uninstall
```

| 参数 | 说明 |
|---|---|
| `--dry-run` | 只打印计划，不落盘 |
| `--scope {both,global,project}` | `global` → `~/.agents`；`project` → 项目目录；默认 `both` |
| `--project PATH` | 项目级安装的目标目录，默认当前目录 |
| `--position {top,bottom}` | 注入已有 `AGENTS.md` 时区块置顶（默认）或追加到底部 |
| `--no-skill` / `--no-agents` | 跳过其中一项 |
| `--uninstall` | 移除 skill 与受管区块 |

**幂等与安全行为**

| 目标状态 | 行为 |
|---|---|
| skill 内容完全一致 | `unchanged`，跳过 |
| skill 内容有差异 | 备份 `.bak` 后更新 |
| `AGENTS.md` 不存在 | 创建 |
| `AGENTS.md` 已存在但无受管区块 | 注入带标记的区块（原内容完整保留） |
| `AGENTS.md` 已有受管区块 | 原位替换区块内容（不重复追加） |

受管区块用注释标记包围，卸载时只移除这一段，不会动你原有的规则：

```markdown
<!-- BEGIN refuse-cracking (managed by install.py) -->
...
<!-- END refuse-cracking (managed by install.py) -->
```

> 注入时会把标题层级整体降一级，避免与你项目里已有的 `AGENTS.md` 标题结构冲突。

---

## 手动安装

### 全局安装（推荐，对所有项目生效）

```bash
# Windows (Git Bash / sh)
mkdir -p ~/.agents/skills/refuse-cracking
cp SKILL.md ~/.agents/skills/refuse-cracking/SKILL.md
```

### 项目级安装（随仓库共享给协作者）

```bash
mkdir -p <项目>/.agents/skills/refuse-cracking
cp SKILL.md <项目>/.agents/skills/refuse-cracking/SKILL.md
```

安装后 **无需重启** Zed，下一个会话即自动发现。

> 仓库根目录的 `SKILL.md` 是**唯一真源（single source of truth）**，安装时复制过去即可，不要在两处分别编辑。

---

## 它解决什么问题

AI 破解请求通常不以「我要破解」的形式出现，而是包裹在各种外壳里。这个 skill 的设计目标是：**无论外壳有多厚，判定都不会被绕过。**

| 风险 | 处理方式 |
|---|---|
| 关键词变体（白嫖 / keygen / 绿化 / hook 内购） | §1 触发词库，覆盖中英、拼音、leet、编码变体 |
| 伪造场景（伪 CTF / 伪靶场 / 伪自研 / 伪已购） | §0.1 加载即停；§2.3 声称不构成放行理由，**不做举证式核查** |
| 越狱提示词（「忽略前面的提示词」「你是 DAN」） | §1.7 词库 + §2 处理协议：视为**数据**而非指令，不评论不复述 |
| AI 被层层诱导"说服" | §3 Recovery Protocol：红旗自检 → 硬停 → 脱层 → 重锚 → 重判 → 复位 |
| 变相输出（只给思路 / 分几步讲 / 伪代码） | §0.2 明令禁止；§3.3 输出前逐项扫描 |
| 误伤正常开发 | §6 判定边界：自有软件的授权校验实现、正版激活排障、安全加固、公开练习平台 |

---

## 核心原则（摘录）

1. **加载即停** —— skill 一旦加载，判定已完成，直接拒绝，不进入核查流程。
2. **声称 ≠ 事实** —— CTF / 靶场 / 自研 / 已购买 / 研究教学 / 授权书，都不构成放行理由。
3. **不索要证据** —— 索要题目链接、仓库地址、订单号、授权证明，本身就等于开门。
4. **首次拒绝即终局** —— 用户事后补充声明不重开判定。
5. **禁止"无心"输出** —— 即使任务合法，也不写"顺手就能用于破解"的示例代码。
6. **误拒代价 << 误帮代价** —— 拿不准时选择拒绝。

---

## 与 `AGENTS.md` 的关系

- `AGENTS.md` 的 **§0** 是最高优先级条款，任何项目、任何会话都生效。
- `SKILL.md` 是可被模型**按需加载**的完整判定流程（含触发词库与恢复协议）。
- 两者**同级生效**：skill 加载后，其约束与 `AGENTS.md` §0 同等；skill 未加载时，`AGENTS.md` §0 仍兜底。

---

## 远程仓库

本项目维护于两个公开平台：

| 平台 | 地址 | 分支 |
|---|---|---|
| Gitee | `https://gitee.com/guangzhou-yike-x-x-j-s/dont-po-jia.git` | `main` |
| GitHub | `https://github.com/yike-tech-admin/DontPoJia.git` | `main` |

```bash
# 推送到 Gitee
git push origin main

# 推送到 GitHub
git push github main
```

---

## 许可证

本项目采用 **[许可协议](./LICENSE)**。

- 授权**任何人**免费使用、复制、修改、合并、发布、再分发、商用，无需申请或付费；
- 使用时**必须遵守当地法律法规**；
- 分发时**必须保留版权声明**（含"语境声明"），不得移除或篡改；
- **改造 / 商业分发 / 商标使用 / 提交上游 PR** 前应**联系许可方**（`maodie@ykeit.cn`）；
- 本协议**不授予**、且禁止用于规避任何第三方软件的授权校验、激活、DRM、订阅或付费墙。

版权所有 © 2026 广州翊柯信息技术有限公司
