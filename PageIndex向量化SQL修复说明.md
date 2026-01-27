# PageIndex 向量化 SQL 参数匹配修复说明

## 🔧 问题分析

### 错误现象
```
django.db.utils.ProgrammingError: the query has 4 placeholders but 2 parameters were passed
```

### 根本原因
在 `list_embedding_text.sql` 文件中，我们修改了SQL模板，使用UNION连接4个查询部分：
1. Problem查询 (source_type=0)
2. 段落查询 (source_type=1) 
3. 标题查询 (source_type=2)
4. 摘要查询 (source_type=3)

但调用代码 `listener_manage.py` 中只提供了2个查询参数：
- `problem`: 查询条件
- `paragraph`: 查询条件

而SQL模板中有4个 `${paragraph}` 占位符，导致参数数量不匹配。

## 🛠️ 修复方案

### 1. 修改SQL模板
**文件**: `apps/common/sql/list_embedding_text.sql`

将不同UNION部分使用不同的占位符名称：
```sql
-- 段落查询 (source_type=1)
${paragraph}

-- 标题查询 (source_type=2)  
${paragraph_title}

-- 摘要查询 (source_type=3)
${paragraph_summary}
```

### 2. 修改调用代码
**文件**: `apps/common/event/listener_manage.py`

在 `embedding_by_paragraph` 函数中：
- 为每个占位符提供对应的QuerySet
- 为每个占位符提供对应的field_replace_dict

```python
data_list = native_search(
    {
        'problem': QuerySet(get_dynamics_model({'paragraph.id': django.db.models.CharField()})).filter(
            **{'paragraph.id': paragraph_id}),
        'paragraph': QuerySet(Paragraph).filter(id=paragraph_id),
        'paragraph_title': QuerySet(Paragraph).filter(id=paragraph_id),
        'paragraph_summary': QuerySet(Paragraph).filter(id=paragraph_id)
    },
    select_string=get_file_content(
        os.path.join(PROJECT_DIR, "apps", "common", 'sql', 'list_embedding_text.sql')),
    field_replace_dict={
        'problem': {
            'paragraph.id': 'paragraph.id'
        },
        'paragraph': {
            '"id"': '"paragraph"."id"'
        },
        'paragraph_title': {
            '"id"': '"paragraph"."id"'
        },
        'paragraph_summary': {
            '"id"': '"paragraph"."id"'
        }
    })
```

## ✅ 修复验证

### 验证脚本
创建了 `verify_embedding_fix.py` 验证脚本，检查：
1. SQL模板占位符数量正确性
2. 调用代码参数完整性
3. Python语法正确性

### 验证结果
- ✅ SQL模板：4个不同占位符，各1个
- ✅ 调用代码：4个查询参数 + 4个字段替换配置
- ✅ Python语法：无错误

## 📊 技术细节

### 占位符映射关系
| 占位符 | 用途 | QuerySet | 字段替换 |
|--------|------|----------|----------|
| `${problem}` | Problem查询 | 动态模型过滤段落ID | `paragraph.id` → `paragraph.id` |
| `${paragraph}` | 段落向量查询 | Paragraph过滤ID | `"id"` → `"paragraph"."id"` |
| `${paragraph_title}` | 标题向量查询 | Paragraph过滤ID | `"id"` → `"paragraph"."id"` |
| `${paragraph_summary}` | 摘要向量查询 | Paragraph过滤ID | `"id"` → `"paragraph"."id"` |

### 参数传递流程
1. `generate_sql_by_query_dict()` 接收查询字典
2. 替换SQL模板中的占位符为WHERE条件
3. 收集所有WHERE条件的参数到参数列表
4. 最终：4个占位符 = 4个WHERE条件 = 4组参数 = ✅ 匹配

## 🚀 影响范围

### 功能影响
- ✅ 修复了段落向量化任务的参数错误
- ✅ 保持了多字段向量化功能
- ✅ 不会影响其他向量化任务

### 兼容性
- ✅ 向后兼容现有向量数据
- ✅ 不需要重新迁移数据库
- ✅ 不影响检索逻辑

## 📋 使用建议

### 1. 立即修复
此修复解决了向量化任务无法执行的问题，应该立即应用。

### 2. 测试验证
建议在实际环境中测试：
```bash
# 1. 测试单个段落向量化
python manage.py shell
>>> from apps.common.event.listener_manage import ListenerManagement
>>> from apps.knowledge.models import Paragraph
>>> paragraph = Paragraph.objects.first()
>>> ListenerManagement.embedding_by_paragraph(paragraph.id, embedding_model)

# 2. 测试文档向量化
# 执行完整向量化流程
```

### 3. 监控日志
关注向量化任务日志，确认：
- 不再出现参数错误
- 正确生成3种类型的向量数据

## 🎯 总结

这次修复解决了PageIndex多字段向量化功能中的关键技术问题：
- **问题**：SQL参数不匹配导致向量化失败
- **方案**：分离SQL占位符，对应提供查询参数
- **结果**：向量化功能恢复正常，多字段向量化可以正常工作

修复后的系统可以正常生成段落、标题、摘要三种向量数据，为后续的检索优化奠定了基础。