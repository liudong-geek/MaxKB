# coding=utf-8
"""测试 jieba 分词对"注册地址"的处理"""
import jieba

# 模拟实际内容（包含空格和特殊字符）
test_content = """关于我们成立时间：2025年7月30日注册地址：北京市大兴区礼贤镇元平北路1号自贸试                 验区大兴机场片区自贸创新服务中心W7                 栋1层0158号"""

print("=" * 60)
print("测试 jieba 分词")
print("=" * 60)

# cut_all=True 全切分模式
result_all = jieba.lcut(test_content, cut_all=True)
print(f"\n【cut_all=True 全切分模式】")
print(f"分词结果: {result_all[:50]}...")

# 检查是否包含关键词
has_zhuce = '注册' in result_all
has_dizhi = '地址' in result_all
print(f"\n含'注册': {has_zhuce}")
print(f"含'地址': {has_dizhi}")

# 测试清理后的内容
import re
clean_content = re.sub(r'\s+', ' ', test_content)  # 合并空白字符
print(f"\n【清理后内容】")
print(f"{clean_content}")

result_clean = jieba.lcut(clean_content, cut_all=True)
print(f"\n【清理后分词】")
print(f"分词结果: {result_clean[:50]}...")

has_zhuce = '注册' in result_clean
has_dizhi = '地址' in result_clean
print(f"\n含'注册': {has_zhuce}")
print(f"含'地址': {has_dizhi}")

# 测试精确模式
result_accurate = jieba.lcut(clean_content, cut_all=False)
print(f"\n【cut_all=False 精确模式】")
print(f"分词结果: {result_accurate[:30]}...")
has_zhuce = '注册' in result_accurate
has_dizhi = '地址' in result_accurate
print(f"含'注册': {has_zhuce}")
print(f"含'地址': {has_dizhi}")

# 搜索引擎模式
result_search = jieba.lcut_for_search(clean_content)
print(f"\n【lcut_for_search 搜索模式】")
print(f"分词结果: {result_search[:30]}...")
has_zhuce = '注册' in result_search
has_dizhi = '地址' in result_search
print(f"含'注册': {has_zhuce}")
print(f"含'地址': {has_dizhi}")
