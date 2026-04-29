# ResearchPipe 部署 Guide

本项目走 **muye-laptop（192.168.1.23 Ubuntu）+ frp + 阿里云 nginx 反代** 模式，跟 jiwa.zgen.xin / chaoview.zgen.xin 一致。

## 拓扑

```
internet ──https──> 阿里云 (39.105.141.168, 北京)
                       │ nginx 443 → 127.0.0.1:7786
                       │
                       └ frps server :7000  ◄── frpc client
                                                    │
                                                    │ (TCP tunnel)
                                                    ▼
                                                  192.168.1.23 (laptop)
                                                    │
                                                    ├── frontend Next.js :3726
                                                    │      ↳ proxy /v1/* + /downloads → :3725
                                                    │      ↳ /agent ✅
                                                    │      ↳ /admin (rpadmin via nginx rewrite)
                                                    └── backend gunicorn :3725
                                                           │
                                                           └── researchpipe_postgres :5433
                                                                  pgvector + pg_trgm
                                                                  14,928 files / 917,808 chunks
```

## 域名分配

| 域名 | 用途 | 路径 |
|---|---|---|
| **rp.zgen.xin** | 公开 Landing / Agent / API / Docs | 全部 |
| **rpadmin.zgen.xin** | 内部控制台（需 RP_ADMIN_KEY） | 自动重写到 /admin/* |

阿里云 nginx 都指到同一个 frp 端口 `:7786`（前端），用 nginx rewrite 区分行为。

## 端口表

| 角色 | 笔记本本地 | frp 远端 (aliyun) | 公网域名 |
|---|---|---|---|
| Backend (gunicorn) | 3725 | — (通过 frontend 代理) | — |
| Frontend (Next.js) | 3726 | 7786 | rp.zgen.xin / rpadmin.zgen.xin |
| PG corpus | 5433 (docker) | — (内部) | — |
| PG qmp_data | 5432 (docker) | — (内部，只读) | — |

---

## 一次性 setup（你睡醒第一次部署做这些）

### 1. 笔记本（muye@192.168.1.23）

```bash
ssh muye@192.168.1.23

# 1.1 拉代码
cd ~
git clone https://github.com/miaomiaoxu999-cell/researchpipe.git
cd researchpipe

# 1.2 配置 .env
cp .env.example backend/.env
nano backend/.env
# 填入：TAVILY_API_KEY / BAILIAN_API_KEY / SILICONFLOW_API_KEY 等
# 重要：RP_ADMIN_KEY 必须设置，否则 /v1/admin/* 返 503
# 也要设置 RP_ALLOWED_ORIGINS 包括公网域名：
#   RP_ALLOWED_ORIGINS=https://rp.zgen.xin,https://rpadmin.zgen.xin

# 1.3 frontend env
cat > frontend/.env.production <<'EOF'
NEXT_PUBLIC_RP_BACKEND_URL=https://rp.zgen.xin
NEXT_PUBLIC_RP_API_KEY=rp-demo-public
EOF

# 1.4 backend deps
cd backend && uv sync --no-dev

# 1.5 frontend build
cd ../frontend && npm ci && npm run build

# 1.6 systemd 服务（一次配置）
sudo cp ../deploy/researchpipe-backend.service /etc/systemd/system/
sudo cp ../deploy/researchpipe-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now researchpipe-backend researchpipe-frontend

# 1.7 frp tunnel — 加 frontend 转发
sudo nano /etc/frp/frpc.toml
# 把 deploy/frp-additions.toml 里的 [[proxies]] 块贴到末尾
sudo systemctl restart frpc

# 1.8 验证本地
curl http://127.0.0.1:3725/healthz   # backend
curl http://127.0.0.1:3726/          # frontend
```

### 2. 阿里云 (39.105.141.168)

```bash
ssh root@39.105.141.168   # 或你常用的入口

# 2.1 nginx 配置
sudo cp /path/to/researchpipe/deploy/nginx-aliyun.conf \
   /etc/nginx/sites-available/rp.zgen.xin
sudo ln -sf /etc/nginx/sites-available/rp.zgen.xin /etc/nginx/sites-enabled/

# 2.2 SSL 证书（首次申请）
sudo certbot --nginx -d rp.zgen.xin -d www.rp.zgen.xin -d rpadmin.zgen.xin

# 2.3 测试 + reload
sudo nginx -t
sudo systemctl reload nginx

# 2.4 验证
curl -I https://rp.zgen.xin/
curl -I https://rp.zgen.xin/healthz
curl -I https://rp.zgen.xin/v1/corpus/stats -H "Authorization: Bearer rp-demo-public"
```

### 3. DNS（如果还没配）

| 记录 | 类型 | 值 |
|---|---|---|
| `rp.zgen.xin` | A | 39.105.141.168 |
| `www.rp.zgen.xin` | A | 39.105.141.168 |
| `rpadmin.zgen.xin` | A | 39.105.141.168 |

---

## 日常更新（一行命令）

```bash
# 从 WSL dev 机器：
cd ~/projects/ResearchPipe
git push origin main      # 推改动
./deploy/deploy.sh        # 拉到笔记本 + 重启 systemd
```

deploy.sh 做的事：
1. SSH 到笔记本拉最新 GitHub 代码
2. backend `uv sync` + 跑 migrations（idempotent）
3. frontend `npm ci` + `next build`
4. 重启 systemd 服务
5. healthcheck 验证

---

## 故障排查

| 症状 | 看哪 |
|---|---|
| `502 Bad Gateway` 在 rp.zgen.xin | 笔记本服务挂了：`ssh muye@192.168.1.23 'systemctl status researchpipe-frontend'` |
| `502` 但服务运行 | frp tunnel 断了：`ssh muye@192.168.1.23 'systemctl status frpc'` |
| Agent SSE 卡住 | 阿里云 nginx 没设 `proxy_buffering off`（已在 conf 里）|
| 跨域错误 | `RP_ALLOWED_ORIGINS` 没加公网域名 |
| `/v1/admin/*` 返 503 | 笔记本 `.env` 没设 `RP_ADMIN_KEY` |
| Frontend cold-start 很慢 | systemd 重启后第一次访问要编译；保持 `next start` 进程别 kill |

## 日志

```bash
# 后端
ssh muye@192.168.1.23 'journalctl -fu researchpipe-backend --no-pager'
# 前端
ssh muye@192.168.1.23 'journalctl -fu researchpipe-frontend --no-pager'
# frp
ssh muye@192.168.1.23 'journalctl -fu frpc --no-pager | tail -50'
# 阿里云 nginx
ssh root@39.105.141.168 'tail -f /var/log/nginx/access.log'
```

## 备份

PG corpus 重要资产，每周备份：

```bash
# 在笔记本 crontab：
0 4 * * 1 docker exec researchpipe_postgres pg_dump -U postgres -Fc researchpipe \
  > /home/muye/researchpipe_backup_$(date +\%Y\%m\%d).dump && \
  find /home/muye/researchpipe_backup_*.dump -mtime +28 -delete
```

恢复：

```bash
docker exec -i researchpipe_postgres pg_restore -U postgres -d researchpipe -c \
  < researchpipe_backup_<date>.dump
```

---

## 该改的安全配置（上线前）

- [ ] `.env`: `RP_ADMIN_KEY` 用 `openssl rand -hex 16` 重新生成
- [ ] `RP_ALLOWED_ORIGINS=https://rp.zgen.xin,https://rpadmin.zgen.xin`（防其他域名滥用）
- [ ] nginx 给 `rpadmin.zgen.xin` 加 IP allowlist（你家 IP / 公司 VPN IP）
- [ ] `RP_DEMO_API_KEY` 想换成更不可猜的值（demo 是共享的，所以本身就要假设公开）
- [ ] PG 别人不能直连 5433（默认只本地+frp，OK）
- [ ] Aliyun 安全组：只开 80 / 443 / 7000(frp) / SSH
