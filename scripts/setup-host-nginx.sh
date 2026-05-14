#!/usr/bin/env bash
#
# setup-host-nginx.sh - 配置宿主机 Nginx 反向代理（由 Jenkins 调用，在目标服务器上执行）
#
# 用法:
#   dev:  setup-host-nginx.sh dev <port>
#   prod: setup-host-nginx.sh prod <port> <server_ip> <domain> <ssl_cert_path> <ssl_key_path>
#

set -e

ENVIRONMENT="${1:?缺少参数: environment (dev|prod)}"
PORT="${2:-2026}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── 检查 nginx ──
if ! command -v nginx &>/dev/null; then
    log_error "宿主机未安装 nginx，跳过反向代理配置"
    exit 0
fi

# ── 首次部署: 清理 nginx.conf 中的默认 server 块 ──
# 服务器默认的 nginx.conf 通常包含 80/443 default_server 块和
# sites-enabled include，这些会与我们 conf.d/ 下的配置冲突。
# 参考 lumax-agent: 所有站点配置都放 conf.d/，nginx.conf 只做全局设置。
NGINX_CONF="/etc/nginx/nginx.conf"
if [ -f "$NGINX_CONF" ] && ! grep -q "# cleaned-by-lumax" "$NGINX_CONF" 2>/dev/null; then
    cp "$NGINX_CONF" "${NGINX_CONF}.bak.$(date +%Y%m%d%H%M%S)"
    log_info "备份 nginx.conf → nginx.conf.bak.*"

    NGINX_USER=$(grep -oP '^\s*user\s+\K\S+' "$NGINX_CONF" | tr -d ';' || echo "nginx")

    cat > "$NGINX_CONF" <<CONF
# cleaned-by-lumax
user ${NGINX_USER};
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" "\$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    sendfile        on;
    tcp_nopush      on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    include /etc/nginx/conf.d/*.conf;
}
CONF
    log_ok "nginx.conf 已清理（移除默认 server 块和 sites-enabled include）"
fi

# ── 部署配置 ──
case "$ENVIRONMENT" in
    dev)
        CONF_SOURCE="dev-lumax.conf"
        CONF_TARGET="/etc/nginx/conf.d/dev-lumax.conf"
        DOMAIN="dev.lumaxai.cn"

        log_info "部署 dev 环境: $DOMAIN → 127.0.0.1:$PORT"

        if [ ! -f "$REPO_ROOT/docker/nginx/$CONF_SOURCE" ]; then
            log_error "配置文件不存在: $REPO_ROOT/docker/nginx/$CONF_SOURCE"
            exit 1
        fi

        cp "$REPO_ROOT/docker/nginx/$CONF_SOURCE" "$CONF_TARGET"
        sed -i "s|proxy_pass http://127\.0\.0\.1:[0-9]*|proxy_pass http://127.0.0.1:${PORT}|g" "$CONF_TARGET"
        log_ok "配置已部署: $CONF_TARGET"
        ;;

    prod)
        SERVER_IP="${3:?缺少参数: server_ip}"
        DOMAIN="${4:?缺少参数: domain}"
        SSL_CERT_PATH="${5:?缺少参数: ssl_cert_path}"
        SSL_KEY_PATH="${6:?缺少参数: ssl_key_path}"

        log_info "部署 prod 环境: $DOMAIN ($SERVER_IP) → 127.0.0.1:$PORT"
        log_info "  SSL: $SSL_CERT_PATH / $SSL_KEY_PATH"

        # HTTP 配置
        HTTP_TEMPLATE="$REPO_ROOT/docker/nginx/prod-http.conf.template"
        HTTP_TARGET="/etc/nginx/conf.d/prod-http.conf"
        if [ ! -f "$HTTP_TEMPLATE" ]; then
            log_error "HTTP 模板不存在: $HTTP_TEMPLATE"
            exit 1
        fi
        cp "$HTTP_TEMPLATE" "$HTTP_TARGET"
        sed -i "s|{{SERVER_IP}}|${SERVER_IP}|g;s|{{DOMAIN}}|${DOMAIN}|g;s|{{PORT}}|${PORT}|g" "$HTTP_TARGET"
        log_ok "HTTP 配置已部署: $HTTP_TARGET"

        # SSL 配置
        SSL_TEMPLATE="$REPO_ROOT/docker/nginx/prod-ssl.conf.template"
        SSL_TARGET="/etc/nginx/conf.d/prod-ssl.conf"
        if [ -f "$SSL_TEMPLATE" ]; then
            cp "$SSL_TEMPLATE" "$SSL_TARGET"
            sed -i "s|{{DOMAIN}}|${DOMAIN}|g;s|{{PORT}}|${PORT}|g;s|{{SSL_CERT_PATH}}|${SSL_CERT_PATH}|g;s|{{SSL_KEY_PATH}}|${SSL_KEY_PATH}|g" "$SSL_TARGET"
            log_ok "SSL 配置已部署: $SSL_TARGET"

            if [ -f "$SSL_CERT_PATH" ] && [ -f "$SSL_KEY_PATH" ]; then
                log_ok "SSL 证书文件已就绪"
            else
                log_warn "SSL 证书文件未找到，HTTPS 可能无法正常工作"
            fi
        else
            log_warn "SSL 模板不存在，跳过 HTTPS 配置"
        fi

        # 清理旧配置
        for old in lumaxai.conf lumaxai-ssl.conf lumaxai-jialugroup.conf lumaxai-jialugroup-ssl.conf; do
            [ -f "/etc/nginx/conf.d/$old" ] && rm -f "/etc/nginx/conf.d/$old" && log_ok "已清理: $old"
        done
        ;;

    *)
        log_error "未知环境: $ENVIRONMENT (支持: dev, prod)"
        exit 1
        ;;
esac

# ── 检查并重载 ──
if nginx -t 2>/dev/null; then
    log_ok "Nginx 配置语法检查通过"
else
    log_error "Nginx 配置语法检查失败:"
    nginx -t
    exit 1
fi

nginx -s reload
log_ok "Nginx 已重载"

echo ""
if [ "$ENVIRONMENT" = "dev" ]; then
    log_ok "访问地址: http://$DOMAIN"
elif [ "$ENVIRONMENT" = "prod" ]; then
    log_ok "HTTP:  http://$SERVER_IP"
    log_ok "HTTPS: https://$DOMAIN"
fi
