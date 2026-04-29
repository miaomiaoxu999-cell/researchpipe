# Payment Integration Plan — ResearchPipe

**TL;DR**：你主要面向中国 B2B 客户，**Stripe 不好用**——它在国内不收人民币、出海需要海外公司+海外银行账户、客户也不愿走美元结算。**短期用「微信/支付宝个人收款 + 手动颁 key」最务实，规模化再选 Lemon Squeezy（海外）或 Pingxx / 易支付（国内聚合器）**。

---

## 你的真实约束

| 项 | 现实 |
|---|---|
| 客户主体 | 中国一二级市场分析师 / VC 助理 / 个人开发者 |
| 客户付款偏好 | 微信支付（85%+） / 支付宝（次之） / 公司打款（B2B 大客户）|
| 你的主体 | 自然人（lifestyle business） |
| 是否有海外公司 | 没有 |
| 月流水规模目标 | ¥3-10 万 MRR |
| 客户单价 | 估计 ¥99-1999/月 区间 |

---

## 选型矩阵

| 方案 | 国内客户体验 | 你的接入成本 | 月流水适用 | 主要痛点 |
|---|---|---|---|---|
| **Stripe（海外）** | 🔴 差，需国际信用卡（多数客户没有）| 🔴 必须海外公司 + 海外银行账户（注册 Stripe Atlas ~$500 + 美国 EIN + 美国地址） | $5K+ | **完全不适合 China B2C/B2B 主战场** |
| **Stripe + Alipay/WeChat Pay** | 🟡 OK，但需 Stripe 主体，仍要海外公司 | 🔴 同上 | $5K+ | 同上 |
| **Lemon Squeezy / Paddle** | 🟡 接受国内卡但费率高 (~5%) | 🟢 自然人即可（merchant of record）| $1K-50K | 入账延迟 / 海外汇款 / 仍不友好微信 |
| **Creem.io** | 🟡 类似 LS，对个人友好 | 🟢 简单注册 | $0-10K | 较新，国内信任度低 |
| **微信个人收款码 + 手动** | 🟢 完美 | 🟢 几乎零成本 | ¥0-3万/月 | **不能开发票**，每笔手动确认，不可持续 ¥3万+ |
| **微信支付商户号（小微）** | 🟢 完美 | 🟡 个体户营业执照（几百元搞定）| ¥1万-100万/月 | 需结算账户、需对接 SDK |
| **支付宝当面付 / Pay.js** | 🟢 完美 | 🟡 个体户即可 | 同上 | 同上 |
| **Pingxx 智能路由** | 🟢 一站式接微信 + 支付宝 + 国际卡 | 🟢 SaaS 级，~1.5% 抽成 | ¥1万-1000万/月 | 收 1-2% 渠道费 |
| **YiPay / 易支付**（国内聚合）| 🟢 客户体验好 | 🟢 5 min 接入 | ¥1万-100万/月 | 部分平台合规模糊，慎选可信的 |

---

## 我的具体建议（按月流水阶段）

### 阶段 1（¥0-3万/月）— 上线第 1-3 个月：**手动收款，一切都是手动的**

```
用户在网站点 "Get API key" → 提交联系方式 + 选套餐
   ↓
你看到飞书通知 / 邮件
   ↓
微信扫码收款（你的个人微信收款码）
   ↓
确认到账后，手动在 rpadmin /admin/accounts 创建 key + 标 plan
   ↓
邮件 / 微信发回 API key
```

**为什么这个阶段**：
- 确认产品有人付钱，**比"完美的支付流程"重要 100 倍**
- 月流水 < ¥3 万时，每天 1-3 个新客户手动颁 key 完全应付得过来
- 不需要执照 / 商户号 / 备案审批
- 反馈循环最短（客户问问题 → 你直接微信回复）

**操作清单**：
- Landing 「Get API key」按钮链接到一个 Google Form / 飞书表单
- 表单字段：邮箱 / 微信号 / 公司 / 计划用途 / 选哪个套餐
- 你的微信收款码 PNG 嵌入「Pricing」页面
- 用 rpadmin 颁 key 后微信发回（30 秒一次）
- 用一个简陋的 Notion / Excel 跟单

### 阶段 2（¥3-10万/月）— 月流水持续 → **接 Lemon Squeezy**

理由：
- LS 接受微信支付（通过他们的 Alipay+ 通道）
- merchant-of-record 模式，**不需要营业执照**
- 自动续费、退款、发票全自动
- 抽成 5% + $0.50/单，对 ¥3-10 万 MRR 是 ~¥3-8K/月手续费，**值**
- 接入 1-2 天

**接入参考**：
```typescript
// pricing 页加 LS checkout 链接
<a href="https://researchpipe.lemonsqueezy.com/checkout/buy/<variant-id>?embed=1">
  订阅 Pro 套餐
</a>
```

LS 入账后 webhook 你的后端 → 自动创建 account，邮件发 key。

### 阶段 3（¥10万+/月）—  开个体户 → 接微信支付商户

- 营业执照（几百元，3-7 天）
- 开微信支付商户号（小微商户即可）
- 接 wechatpay-axios-plugin 或腾讯云 SDK
- **抽成降到 0.6% — 1%**，每月省 ¥3-8K
- 可以开正经发票，B 端客户买单率上升

**Pingxx / Beecloud 替代方案**：如果懒得自接微信 + 支付宝两条渠道，Pingxx 帮你聚合，多收 ~0.5%，少 1-2 周对接时间。

---

## ResearchPipe 后端要做的事（无论哪个阶段）

```python
# 核心：唯一一个 endpoint：手动 + 自动都能用
POST /v1/admin/accounts
{
  "plan": "Pro",
  "credits_limit": 80000,
  "label": "客户邮箱 / 备注"
}
→ {"api_key": "rp-..."}
```

这个端点 **rpadmin 已经实现了**（NIGHT-3 完成）。无论是手动颁还是 LS webhook 自动调，逻辑一样。

阶段 2 加 LS 时，只需写一个：

```python
@router.post("/v1/webhook/lemon_squeezy")
async def ls_webhook(body: dict, x_signature: str = Header(...)):
    verify_sig(body, x_signature)
    if body["event"] == "subscription_created":
        plan = body["data"]["variant_name"]
        credits = PLAN_CREDITS[plan]
        # call admin/accounts logic
        new_key = await create_account(plan=plan, credits_limit=credits)
        # email new_key to body["data"]["customer_email"]
        send_email(...)
```

---

## 不推荐的方案

| 方案 | 为什么不推荐 |
|---|---|
| **Stripe 直连** | 国内客户不会用美元卡 |
| **PayPal** | 国内大量客户没账户，体验差 |
| **个人公众号 H5 支付** | 需要服务号 + 备案，比开商户号还累 |
| **加密货币** | 合规模糊，B2B 客户拒收 |

---

## 你睡醒可以决定

1. **现在阶段（0 客户）**：直接用「微信收款码 + rpadmin 手动颁 key」开 puffer 卖。我可以在 Landing 加个 Google Form 链接 + 微信收款码区块。
2. **如果你看到第一周 5+ 单**：去开 Lemon Squeezy 账号（免费注册，1-2 天审），接 webhook。
3. **达到 ¥10 万/月**：开个体户。

**我的强烈推荐**：阶段 1 不要花一分钟做 Stripe / LS 集成，**先验证有人愿意付钱**。
