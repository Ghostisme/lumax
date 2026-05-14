pipeline {
    agent any

    environment {
        PROJECT_NAME = 'lumax'
        REMOTE_DIR   = "/opt/${PROJECT_NAME}"
    }

    parameters {
        choice(name: 'ENVIRONMENT', choices: ['dev', 'prod'], description: '部署环境: dev=测试环境, prod=生产环境')
        choice(name: 'ACTION', choices: ['deploy', 'restart', 'stop'], description: '操作类型: deploy=智能构建并部署, restart=重启服务, stop=停止服务')
        booleanParam(name: 'FORCE_BUILD', defaultValue: false, description: '强制重建所有镜像（忽略依赖变化检测）')

        // ── 生产环境 Nginx 参数（dev 环境自动使用内置默认值）──
        string(name: 'PROD_SERVER_IP', defaultValue: '47.103.46.79', description: '生产环境服务器公网 IP（用于 IP 直接访问）')
        string(name: 'PROD_DOMAIN', defaultValue: 'lumaxai.jialugroup.cn', description: '生产环境域名（需有 SSL 证书）')
        string(name: 'PROD_SSL_CERT_PATH', defaultValue: '/etc/nginx/ssl/jialugroup.crt', description: 'SSL 证书文件路径（服务器上的完整证书链）')
        string(name: 'PROD_SSL_KEY_PATH', defaultValue: '/etc/nginx/ssl/jialugroup.key', description: 'SSL 私钥文件路径')
    }

    stages {
        stage('初始化环境配置') {
            steps {
                script {
                    switch (params.ENVIRONMENT) {
                        case 'dev':
                            env.DEPLOY_HOST = '172.27.202.44'
                            env.DEPLOY_USER = 'root'
                            env.PORT = '2026'
                            env.DOMAIN = 'dev.lumaxai.cn'
                            env.NGINX_CONF = 'dev-lumax.conf'
                            break
                        case 'prod':
                            env.DEPLOY_HOST = '172.27.202.44'
                            env.DEPLOY_USER = 'root'
                            env.PORT = '2027'
                            env.SERVER_IP = params.PROD_SERVER_IP
                            env.DOMAIN = params.PROD_DOMAIN
                            env.SSL_CERT_PATH = params.PROD_SSL_CERT_PATH
                            env.SSL_KEY_PATH = params.PROD_SSL_KEY_PATH
                            break
                    }
                    echo "环境: ${params.ENVIRONMENT} | 域名: ${env.DOMAIN} | 目标主机: ${env.DEPLOY_HOST} | 端口: ${env.PORT}"
                }
            }
        }

        stage('拉取代码') {
            when {
                expression { params.ACTION == 'deploy' }
            }
            steps {
                checkout scm
            }
        }

        stage('同步到目标服务器') {
            when {
                expression { params.ACTION == 'deploy' }
            }
            steps {
                sh """
                    ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST} 'mkdir -p ${REMOTE_DIR}'
                    rsync -avz --delete \
                        --exclude '.git' \
                        --exclude 'node_modules' \
                        --exclude '__pycache__' \
                        --exclude '.venv' \
                        --exclude 'backend/.deer-flow' \
                        --exclude 'config.yaml' \
                        --exclude 'extensions_config.json' \
                        -e 'ssh -o StrictHostKeyChecking=no' \
                        ./ ${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_DIR}/
                """
            }
        }

        stage('部署服务') {
            steps {
                script {
                    def forceFlag = params.FORCE_BUILD ? '--force' : ''
                    sh """
                        ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST} \
                            'cd ${REMOTE_DIR} && PORT=${PORT} bash scripts/jenkins-deploy.sh ${params.ACTION} ${forceFlag}'
                    """
                }
            }
        }

        stage('配置宿主机 Nginx 反向代理') {
            when {
                expression { params.ACTION == 'deploy' }
            }
            steps {
                script {
                    if (params.ENVIRONMENT == 'prod') {
                        sh """
                            ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST} \
                                'bash ${REMOTE_DIR}/scripts/setup-host-nginx.sh ${params.ENVIRONMENT} ${PORT} ${SERVER_IP} ${DOMAIN} ${SSL_CERT_PATH} ${SSL_KEY_PATH}'
                        """
                    } else {
                        sh """
                            ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST} \
                                'bash ${REMOTE_DIR}/scripts/setup-host-nginx.sh ${params.ENVIRONMENT} ${PORT}'
                        """
                    }
                }
            }
        }

        stage('健康检查') {
            when {
                expression { params.ACTION != 'stop' }
            }
            steps {
                sh """
                    ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST} \
                        'cd ${REMOTE_DIR} && PORT=${PORT} bash scripts/jenkins-deploy.sh health'
                """
            }
        }
    }

    post {
        success {
            script {
                echo "部署成功! 环境: ${params.ENVIRONMENT} | 内网: http://${DEPLOY_HOST}:${PORT} | 外网: http://${DOMAIN}"
            }
        }
        failure {
            echo '部署失败，请查看日志排查问题。'
        }
        always {
            cleanWs()
        }
    }
}
