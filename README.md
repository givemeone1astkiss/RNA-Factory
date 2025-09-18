# RNA-Factory

一个基于 AI 的 RNA 序列设计和分析平台，使用 DeepSeek API 进行智能序列生成和优化。

## 🚀 快速开始

### 使用 GitLab CI/CD 自动部署（推荐）

1. **克隆项目**

   ```bash
   git clone https://gitlab.com/your-username/rna-factory.git
   cd rna-factory
   ```

2. **配置 GitLab CI/CD 变量**

   - 在 GitLab 项目设置中配置必要的环境变量
   - 参考 [GitLab 部署指南](GITLAB_DEPLOYMENT.md)

3. **推送代码触发部署**
   ```bash
   git push origin develop  # 部署到测试环境
   git push origin main     # 部署到生产环境
   ```

### 本地开发

1. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

2. **设置环境变量**

   ```bash
   cp env.example .env
   # 编辑 .env 文件，设置你的API密钥
   ```

3. **运行应用**
   ```bash
   python run.py
   ```

## 🏗️ 项目结构

```
rna-factory/
├── app/                    # Flask应用主目录
│   ├── static/            # 静态文件
│   ├── templates/         # HTML模板
│   ├── __init__.py        # Flask应用初始化
│   ├── routes.py          # 路由定义
│   ├── models.py          # 数据模型
│   └── utils.py           # 工具函数
├── models/                 # AI模型相关
├── tests/                  # 测试文件
├── docker-compose.yml      # Docker Compose配置
├── Dockerfile             # Docker镜像构建
├── .gitlab-ci.yml         # GitLab CI/CD配置
└── requirements.txt        # Python依赖
```

## 🔧 技术栈

- **后端**: Flask, Python 3.11+
- **AI 服务**: DeepSeek API
- **容器化**: Docker, Docker Compose
- **CI/CD**: GitLab CI/CD
- **监控**: Prometheus, Grafana
- **数据库**: SQLite (可扩展)

## 📋 功能特性

- 🤖 AI 驱动的 RNA 序列设计
- 🔬 序列分析和优化
- 📊 可视化结果展示
- 🚀 自动化部署和监控
- 🔒 安全的环境变量管理

## 🚀 部署

### GitLab CI/CD 自动部署

项目配置了完整的 GitLab CI/CD 流水线：

- **测试阶段**: 自动运行单元测试
- **构建阶段**: 构建 Docker 镜像
- **部署阶段**: 自动部署到测试/生产环境

详细配置请参考 [GitLab 部署指南](GITLAB_DEPLOYMENT.md)

### Docker 部署

```bash
# 构建镜像
docker build -t rna-factory .

# 运行容器
docker run -p 8000:8000 rna-factory
```

### Docker Compose 部署

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 🧪 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_routes.py -v
```

## 📚 API 文档

### 主要端点

- `POST /api/design` - 设计新的 RNA 序列
- `GET /api/sequences` - 获取序列列表
- `GET /api/sequences/<id>` - 获取特定序列详情
- `PUT /api/sequences/<id>` - 更新序列
- `DELETE /api/sequences/<id>` - 删除序列

### 请求示例

```bash
curl -X POST http://localhost:8000/api/design \
  -H "Content-Type: application/json" \
  -d '{
    "target_function": "ribozyme",
    "constraints": {
      "length": 100,
      "gc_content": 0.5
    }
  }'
```

## 🔒 环境变量

| 变量名                 | 描述              | 默认值                     |
| ---------------------- | ----------------- | -------------------------- |
| `DEEPSEEK_API_KEY`     | DeepSeek API 密钥 | 必需                       |
| `DEEPSEEK_API_BASE`    | API 基础 URL      | `https://api.deepseek.com` |
| `DEEPSEEK_API_VERSION` | API 版本          | `v1`                       |
| `FLASK_ENV`            | Flask 环境        | `production`               |
| `SECRET_KEY`           | Flask 密钥        | 必需                       |

## 🤝 贡献

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

- 创建 [Issue](https://gitlab.com/your-username/rna-factory/-/issues)
- 查看 [GitLab 部署指南](GITLAB_DEPLOYMENT.md)
- 联系维护团队
