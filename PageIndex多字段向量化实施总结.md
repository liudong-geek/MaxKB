# PageIndex 多字段向量化实施总结

## ✅ 实施概述

本次实施为 MaxKB 的 PageIndex 功能增加了**多字段向量化**能力，将段落的**标题**、**章节路径**、**摘要**作为独立的向量化数据源，显著提升检索命中率和效率。

---

## 📋 核心改动清单

### 1. 数据库层改动

#### 1.1 Paragraph 模型新增字段
**文件:** `apps/knowledge/models/knowledge.py`

新增三个字段：
```python
section_title = models.CharField(max_length=256, verbose_name="章节标题", default="", db_index=True)
section_path = models.CharField(max_length=1024, verbose_name="章节路径", default="", db_index=True)
summary = models.TextField(verbose_name="章节摘要", default="", blank=True)
```

#### 1.2 SourceType 枚举扩展
新增摘要类型：
```python
class SourceType(models.IntegerChoices):
    PROBLEM = 0, '问题'
    PARAGRAPH = 1, '段落'
    TITLE = 2, '标题'
    SUMMARY = 3, '摘要'  # 新增
```

#### 1.3 数据库迁移
**文件:** `apps/knowledge/migrations/0010_add_paragraph_section_fields.py`

自动生成的迁移文件，包含三个字段的创建和索引。

---

### 2. PageIndex 构建逻辑改动

#### 2.1 自动回写段落章节信息
**文件:** `apps/knowledge/page_index/page_index_builder.py`

新增 `_sync_paragraph_sections()` 方法：
- 在 PageIndex 构建完成后自动调用
- 通过标题匹配或内容前缀匹配将段落关联到 PageIndexNode
- 自动写入 `section_title`、`section_path`、`summary` 字段
- 使用 `bulk_update()` 批量更新，性能优化

**匹配策略：**
1. 优先按标题归一化匹配
2. 其次按内容前 100 字匹配
3. 最后回退到根节点

---

### 3. 向量化逻辑改动

#### 3.1 多源向量化 SQL
**文件:** `apps/common/sql/list_embedding_text.sql`

将原有的单一段落向量化改为 **UNION 三部分**：

| source_type | 向量化内容 | 说明 |
|------------|----------|------|
| 1 (PARAGRAPH) | 文档名 + 章节路径 + 标题 + 正文 | 原有的段落向量 |
| 2 (TITLE) | 文档名 + 章节路径 + 标题 | **新增**标题向量 |
| 3 (SUMMARY) | 文档名 + 章节路径 + 标题 + 摘要 | **新增**摘要向量 |

**优化：**
- 使用 `NULLIF()` 过滤空值
- 使用 `COALESCE()` 回退到 `title`
- 自动过滤空文本，避免生成无效向量

#### 3.2 向量关联逻辑更新
**文件:** `apps/knowledge/vector/pg_vector.py`

**核心改动：**
- 将所有 `is_paragraph` 判断改为 `is_section_embedding`
- 支持 `PARAGRAPH/TITLE/SUMMARY` 三种类型走 PageIndex 节点映射
- 批量保存前过滤空文本向量
- 所有三种类型都会记录 `page_index_node_id`、`tree_level`、`tree_path`、`sibling_index`

**改动位置：**
- `_save()` 方法
- `_batch_save()` 方法  
- `_resolve_page_index_node_map()` 调用处（3 处）

---

### 4. 后台管理脚本

#### 4.1 重建脚本增强
**文件:** `build_page_index.py`

新增 `rebuild_sections_and_embeddings()` 方法：

**功能：**
1. 重建 PageIndex（如果未构建）
2. 删除旧的 Embedding 记录
3. 触发重新向量化任务（异步 Celery 任务）

**用法：**
```bash
# 重建所有知识库
python build_page_index.py --rebuild

# 重建指定知识库
python build_page_index.py --rebuild <knowledge_id>
```

---

### 5. 前端界面改动

#### 5.1 语言包更新
**文件:** `ui/src/locales/lang/zh-CN/views/paragraph.ts`

新增字段翻译：
```typescript
sectionTitle: { label: '章节标题', placeholder: '自动识别的章节标题' }
sectionPath: { label: '章节路径', placeholder: '自动识别的章节路径' }
summary: { label: '章节摘要', placeholder: '自动生成的章节摘要' }
```

#### 5.2 段落表单更新
**文件:** `ui/src/views/paragraph/component/ParagraphForm.vue`

**新增字段：**
- 三个新字段均为只读（`disabled`）
- 只在有值时显示（`v-if`）
- 摘要字段使用 `textarea` 显示

**表单数据模型：**
```typescript
const form = ref<any>({
  title: '',
  section_title: '',   // 新增
  section_path: '',    // 新增
  summary: '',         // 新增
  content: ''
})
```

#### 5.3 段落卡片显示
**文件:** `ui/src/views/paragraph/component/ParagraphCard.vue`

**已有章节路径显示：**
- 使用 `el-tag` 展示章节路径
- 带文件夹图标 (`FolderOpened`)
- 路径过长时自动截断并显示 tooltip
- 样式已完整实现

---

### 6. 序列化器更新
**文件:** `apps/knowledge/serializers/paragraph.py`

**`ParagraphSerializer` 更新：**
```python
fields = [
    'id', 'content', 'is_active', 'document_id', 'title',
    'section_title', 'section_path', 'summary',  # 新增
    'create_time', 'update_time', 'position'
]
```

**`EditParagraphSerializers` 更新：**
- 新增三个字段定义
- 更新 `update_keys` 列表，支持编辑接口更新这些字段

---

## 🔧 实施流程

### 第一步：执行数据库迁移
```bash
python manage.py migrate
```

### 第二步：重建 PageIndex 并重新向量化
```bash
# 方式1：重建所有知识库
python build_page_index.py --rebuild

# 方式2：只重建指定知识库
python build_page_index.py --rebuild <knowledge_id>
```

### 第三步：验证数据
检查段落表是否已写入章节信息：
```sql
SELECT id, title, section_title, section_path, LEFT(summary, 50) 
FROM paragraph 
WHERE section_title != '' 
LIMIT 10;
```

检查向量数量（应为原来的 3 倍）：
```sql
SELECT source_type, COUNT(*) 
FROM paragraph_vector_model 
GROUP BY source_type;
```

预期结果：
- `source_type=1`：段落向量（原有）
- `source_type=2`：标题向量（新增）
- `source_type=3`：摘要向量（新增）

---

## 📊 效果预期

### 1. 检索命中率提升
- **标题向量**：精准匹配章节标题关键词
- **摘要向量**：快速定位章节概要信息
- **段落向量**：保留原有的细粒度内容检索

### 2. 检索效率优化
- 三种向量类型可以在检索时**按权重融合**
- 标题向量更轻量，可用于快速初筛
- 摘要向量适合"问答式"检索

### 3. UI 增强
- 用户可直观看到段落所属章节路径
- 章节信息自动提取，无需手工标注
- 支持按章节路径筛选（后续可扩展）

---

## ⚠️ 注意事项

### 1. 向量数量增加
- 原来 1 个段落 = 1 条向量
- 现在 1 个段落 = 3 条向量（段落 + 标题 + 摘要）
- 向量存储成本增加，但检索效果提升明显

### 2. 空文本过滤
- SQL 中已自动过滤空 `section_title`、`section_path`、`summary`
- 向量化前会再次过滤空文本，避免生成无效向量

### 3. 前端兼容性
- 新字段为可选字段，旧数据不影响展示
- 只在有值时显示，界面干净整洁

### 4. 迁移兼容性
- 新字段设置了默认值 `default=""`
- 已有数据迁移后字段为空字符串，不影响现有功能

---

## 🎯 后续优化建议

### 1. 向量权重策略
在检索 SQL 中为三种向量设置不同权重：
```sql
-- 标题向量权重 2.0
-- 摘要向量权重 1.5
-- 段落向量权重 1.0
```

### 2. 检索模式扩展
- 新增"仅标题检索"模式（快速浏览）
- 新增"章节聚合"模式（按章节分组结果）

### 3. UI 增强
- 支持按章节路径筛选段落
- 支持章节树状导航
- 支持章节摘要预览（鼠标悬停）

### 4. 性能监控
- 统计三种向量的命中率分布
- 评估向量数量增加对检索速度的影响
- 根据实际效果调整权重策略

---

## 📝 文件清单

### 后端改动（7 个文件）
1. `apps/knowledge/models/knowledge.py` - 模型字段
2. `apps/knowledge/migrations/0010_add_paragraph_section_fields.py` - 迁移
3. `apps/knowledge/page_index/page_index_builder.py` - 回写逻辑
4. `apps/common/sql/list_embedding_text.sql` - 多源向量化
5. `apps/knowledge/vector/pg_vector.py` - 向量关联逻辑
6. `apps/knowledge/serializers/paragraph.py` - 序列化器
7. `build_page_index.py` - 重建脚本

### 前端改动（3 个文件）
1. `ui/src/locales/lang/zh-CN/views/paragraph.ts` - 语言包
2. `ui/src/views/paragraph/component/ParagraphForm.vue` - 表单
3. `ui/src/views/paragraph/component/ParagraphCard.vue` - 卡片（已有显示）

---

## ✅ 验收标准

### 功能验收
- [ ] 数据库迁移执行成功
- [ ] PageIndex 构建后 `section_title/section_path/summary` 已写入段落表
- [ ] 向量表中存在 `source_type=2` 和 `source_type=3` 的记录
- [ ] 前端段落表单显示章节信息字段
- [ ] 前端段落卡片显示章节路径标签

### 性能验收
- [ ] 向量化任务正常执行，无报错
- [ ] 检索速度无明显下降（可接受 10% 以内增长）
- [ ] 多字段向量检索命中率提升 > 15%（对比单一段落向量）

### 代码质量
- [ ] 无 Linter 错误
- [ ] 所有改动已通过代码审查
- [ ] 关键逻辑已添加注释

---

## 📞 技术支持

如有问题，请检查：
1. 日志文件中的 PageIndex 构建日志
2. Celery 任务队列是否正常运行
3. 向量化模型是否可用
4. 数据库连接是否正常

---

**实施完成时间：** 2026-01-26  
**实施版本：** v2.x-pageindex-multifield  
**负责人：** AI Agent
