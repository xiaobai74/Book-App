#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
#  小说管理App · 一键部署脚本（Ubuntu 22.04 / 24.04）
#
#  上传方式（本地执行）：
#    scp -r backend frontend deploy root@你的服务器IP:/opt/novel-src
#    （frontend 只需含 dist 目录即可，可先删掉 node_modules）
#
#  服务器执行：
#    cd /opt/novel-src/deploy
#    bash deploy.sh 你的域名或公网IP
#
#  示例：
#    bash deploy.sh 47.100.xx.xx        # IP 直连（HTTP，免备案）
#    bash deploy.sh api.example.com     # 域名（之后可一键上 HTTPS）
# ═══════════════════════════════════════════════════════
set -euo pipefail

DOMAIN_OR_IP="${1:-_}"
APP_DIR=/opt/novel-backend
SRC_DIR=$(cd "$(dirname "$0")/.." && pwd)

[ "$(id -u)" -eq 0 ] || { echo "请使用 root 或 sudo 运行"; exit 1; }
[ -d "$SRC_DIR/backend" ] || { echo "找不到 $SRC_DIR/backend，请确认上传目录结构"; exit 1; }

echo "== [1/6] 安装系统依赖 =="
apt update -y
apt install -y python3 python3-venv nginx

echo "== [2/6] 部署代码到 $APP_DIR =="
id novel >/dev/null 2>&1 || useradd -r -M -d "$APP_DIR" -s /usr/sbin/nologin novel
mkdir -p "$APP_DIR"
rm -rf "$APP_DIR/backend"
mkdir -p "$APP_DIR/backend"
# 排除 .venv / __pycache__ / 本地 .env，避免把开发环境带上服务器
tar -C "$SRC_DIR/backend" \
    --exclude=.venv --exclude=__pycache__ --exclude='*.pyc' --exclude=.env \
    --exclude=epub_output --exclude=txt_output \
    -cf - . | tar -C "$APP_DIR/backend" -xf -

if [ -d "$SRC_DIR/frontend/dist" ]; then
    rm -rf "$APP_DIR/frontend-dist"
    cp -r "$SRC_DIR/frontend/dist" "$APP_DIR/frontend-dist"
    echo "   已部署 Web 前端（浏览器可直接访问 http://$DOMAIN_OR_IP）"
else
    echo "   未找到 frontend/dist，跳过 Web 前端（仅 API 可用）"
fi

echo "== [3/6] 创建 Python 虚拟环境并安装依赖（清华镜像） =="
python3 -m venv "$APP_DIR/.venv"
grep -vi pyinstaller "$APP_DIR/backend/requirements.txt" > /tmp/req-server.txt
"$APP_DIR/.venv/bin/pip" install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r /tmp/req-server.txt --quiet

echo "== [4/6] 生成 .env（SQLite 默认，JWT 随机密钥） =="
if [ ! -f "$APP_DIR/backend/.env" ]; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > "$APP_DIR/backend/.env" <<EOF
JWT_SECRET=$SECRET
CORS_ORIGINS=["https://localhost","capacitor://localhost","http://$DOMAIN_OR_IP","https://$DOMAIN_OR_IP"]
EOF
    echo "   已生成随机 JWT_SECRET"
else
    echo "   .env 已存在，跳过"
fi

chown -R novel:novel "$APP_DIR"

echo "== [5/6] 注册 systemd 服务并启动 =="
cp "$SRC_DIR/deploy/novel-backend.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable novel-backend >/dev/null 2>&1
systemctl restart novel-backend
sleep 2
if curl -sf http://127.0.0.1:8000/health >/dev/null; then
    echo "   后端健康检查通过"
else
    echo "   [警告] 后端未响应，查看日志: journalctl -u novel-backend -n 50"
fi

echo "== [6/6] 配置 Nginx 反向代理 =="
sed "s/__DOMAIN__/$DOMAIN_OR_IP/" "$SRC_DIR/deploy/nginx-novel.conf" \
    > /etc/nginx/sites-available/novel
ln -sf /etc/nginx/sites-available/novel /etc/nginx/sites-enabled/novel
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo ""
echo "════════════ 部署完成 ════════════"
echo "  API 地址:  http://$DOMAIN_OR_IP/api/v1"
echo "  健康检查:  http://$DOMAIN_OR_IP/health"
echo ""
echo "  移动端启用：把 frontend/src/config.ts 的 MOBILE_API_BASE"
echo "  改为 http://$DOMAIN_OR_IP 后重新构建 APK"
echo ""
echo "  提醒 1：阿里云控制台【安全组】需放行 80/443 端口"
if [ "$DOMAIN_OR_IP" != "_" ] && [[ ! "$DOMAIN_OR_IP" =~ ^[0-9.]+$ ]]; then
    echo "  提醒 2：域名启用 HTTPS 执行："
    echo "    apt install -y certbot python3-certbot-nginx"
    echo "    certbot --nginx -d $DOMAIN_OR_IP --non-interactive --agree-tos --register-unsafely-without-email"
    echo "  （HTTPS 后 MOBILE_API_BASE 需改为 https://$DOMAIN_OR_IP）"
fi
echo "══════════════════════════════════"
