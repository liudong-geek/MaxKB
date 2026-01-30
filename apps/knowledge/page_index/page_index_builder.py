# coding=utf-8
"""
PageIndex树构建器
从文档列表构建层次树结构索引
"""
import json
import re
from typing import List, Dict, Optional
from django.db import transaction

from knowledge.models import Document, Knowledge, PageIndexNode, Paragraph, State
from common.utils.split_model import SplitModel, smart_split_paragraph



class PageIndex:
    """PageIndex层次树索引构建器"""
    
    def __init__(self, knowledge: Knowledge):
        self.knowledge = knowledge

    @staticmethod
    def _normalize_title(title: str) -> str:
        if not title:
            return ''
        cleaned = re.sub(r'^\s*#+\s*', '', str(title))
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    def _normalize_path(self, path: List[str]) -> List[str]:
        normalized = [self._normalize_title(item) for item in path]
        return [item for item in normalized if item]

    
    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        knowledge: Knowledge,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> 'PageIndex':
        """
        从文档列表构建PageIndex树
        
        Args:
            documents: 文档列表
            knowledge: 所属知识库
            chunk_size: 章节分块大小（默认1000字符）
            chunk_overlap: 章节重叠大小（默认200字符）
            
        Returns:
            PageIndex实例
        """
        page_index = cls(knowledge)
        page_index.build_tree_from_documents(
            documents, 
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        return page_index
    
    def build_tree_from_documents(
        self,
        documents: List[Document],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        从文档列表构建PageIndex树
        
        流程：
        1. 清理现有PageIndex数据
        2. 解析每个文档为树形结构
        3. 创建PageIndexNode记录
        """
        # 构建新树
        for doc in documents:
            with transaction.atomic():
                PageIndexNode.objects.filter(document=doc).delete()
                self._process_single_document(doc, chunk_size, chunk_overlap)
    
    def _process_single_document(
        self,
        document: Document,
        chunk_size: int,
        chunk_overlap: int
    ):
        """处理单个文档"""
        print(f"[PageIndex] Processing document: {document.name} (ID: {document.id})")

        # 1. 从Paragraph表获取文档所有段落内容
        paragraphs = Paragraph.objects.filter(
            document=document,
            is_active=True
        ).order_by('position')

        print(f"[PageIndex] Found {paragraphs.count()} active paragraphs for document: {document.name}")

        # 拼接所有段落内容为完整文档
        document_content = '\n\n'.join([
            para.content for para in paragraphs
        ])

        print(f"[PageIndex] Document content length: {len(document_content)} characters")

        if not document_content:
            print(f"Warning: Document {document.name} has no active paragraphs")
            return

        # 2. 使用SplitModel解析文档树
        split_model = SplitModel(
            content_level_pattern=self._get_markdown_patterns(),
            with_filter=True,
            limit=chunk_size
        )

        tree = []
        try:
            tree = split_model.parse_to_tree(document_content, index=0)
            print(f"[PageIndex] Document tree parsed successfully, root nodes: {len(tree)}")
        except Exception as e:
            print(f"Warning: Failed to parse document tree for {document.name}: {e}")
            print("[PageIndex] Document may not have Markdown titles (#, ##, ###), creating root node only")

        has_title = any(item.get('state') == 'title' for item in tree)

        # 3. 创建根节点（无论是否解析成功，都创建根节点）
        root_content = document_content[:chunk_size] if has_title else ''
        root_node = self._create_node(
            document=document,
            level=0,
            title=document.name,
            path=[document.name],
            content=root_content,
            parent=None,
            order=0
        )

        print(f"[PageIndex] Root node created: {root_node.id}")

        # 4. 解析成功时递归创建子节点
        if tree and has_title:
            self._create_nodes_from_tree(
                tree=tree,
                document=document,
                parent=root_node,
                current_path=[document.name],
                chunk_size=chunk_size
            )
        else:
            block_list = []
            if tree:
                block_list = [item for item in tree if item.get('state') == 'block']
            if not block_list:
                block_list = [
                    {'state': 'block', 'content': block}
                    for block in smart_split_paragraph(document_content, limit=chunk_size)
                ]

            for idx, block in enumerate(block_list):
                block_content = block.get('content', '')
                if not block_content.strip():
                    continue

                block_title = f"Chunk {idx + 1}"
                self._create_node(
                    document=document,
                    level=1,
                    title=block_title,
                    path=[document.name, block_title],
                    content=block_content,
                    parent=root_node,
                    order=idx
                )

            print(f"[PageIndex] No title structure found, created {len(block_list)} chunk nodes")

        # 4. 同步段落章节信息（写回 Paragraph.section_title/section_path/summary）
        self._sync_paragraph_sections(document, paragraphs)

        # 5. 【新增】调度异步向量化任务（事务提交后执行，避免读取不到节点）
        try:
            from knowledge.tasks import generate_page_index_embeddings


            def _schedule_embedding():
                generate_page_index_embeddings.delay(str(document.id))
                print(f"[PageIndex] Async embedding task scheduled for document: {document.id}")

            transaction.on_commit(_schedule_embedding)
        except ImportError:
            print("[PageIndex] Warning: Celery not available, embedding not scheduled")
        except Exception as e:
            print(f"[PageIndex] Error scheduling embedding: {e}")

        print(f"[PageIndex] Document processing completed: {document.name}")
    
    def _create_nodes_from_tree(
        self,
        tree: List[Dict],
        document: Document,
        parent: PageIndexNode,
        current_path: List[str],
        chunk_size: int
    ):
        """从树结构递归创建节点"""
        for idx, item in enumerate(tree):
            raw_title = item.get('content', '')
            normalized_title = self._normalize_title(raw_title)
            item_path = current_path + ([normalized_title] if normalized_title else [])
            
            if item['state'] == 'title':
                # 创建章节节点
                node = self._create_node(
                    document=document,
                    level=len(item_path) - 1,
                    title=normalized_title or str(raw_title).strip(),
                    path=item_path,
                    content=self._extract_node_content(item, chunk_size),
                    parent=parent,
                    order=idx
                )

                
                # 递归处理子节点
                children = item.get('children', [])
                if children:
                    self._create_nodes_from_tree(
                        children, document, node, item_path, chunk_size
                    )
            
            elif item['state'] == 'block' and parent:
                # 内容块：添加到父节点
                if parent.content:
                    parent.content += "\n\n"
                parent.content += item['content']
                parent.char_count = len(parent.content)
                parent.save()
    
    def _sync_paragraph_sections(self, document: Document, paragraphs):
        """
        【Phase 2 重构】精确同步段落与PageIndex节点的关联
        
        策略：基于段落内容在全文中的位置区间，与节点内容区间求交集
        """
        paragraph_list = list(paragraphs)
        if not paragraph_list:
            return

        # 1. 获取所有节点的数据库记录（需要完整对象以便设置外键）
        nodes = list(PageIndexNode.objects.filter(document=document))
        if not nodes:
            print(f"[PageIndex] No nodes found for document {document.id}")
            return

        # 2. 构建全文档内容（用于偏移量计算）
        separator = '\n\n'
        full_content = separator.join([p.content for p in paragraph_list])
        
        # 3. 计算每个段落在全文中的区间 [start, end)
        paragraph_ranges = []
        cursor = 0
        for para in paragraph_list:
            start = cursor
            end = cursor + len(para.content)
            paragraph_ranges.append({
                'paragraph': para,
                'start': start,
                'end': end
            })
            cursor = end + len(separator)  # 跳过分隔符
        
        # 4. 计算每个节点在全文中的区间（通过查找节点内容在全文中的位置）
        node_ranges = []
        for node in nodes:
            node_content = node.content or ''
            if not node_content.strip():
                continue
            # 使用节点内容的前200字符来定位（避免超长内容）
            search_key = node_content[:200].strip()
            if not search_key:
                continue
            try:
                start_idx = full_content.find(search_key)
                if start_idx != -1:
                    node_ranges.append({
                        'node': node,
                        'start': start_idx,
                        'end': start_idx + len(node_content)
                    })
            except Exception:
                pass
        
        # 按起始位置排序节点
        node_ranges.sort(key=lambda x: x['start'])
        
        # 5. 匹配段落到节点（基于区间重叠）
        root_node = next((n for n in nodes if n.level == 0), None)
        updates = []
        
        for pr in paragraph_ranges:
            para = pr['paragraph']
            para_start, para_end = pr['start'], pr['end']
            matched_node = None
            max_overlap = 0
            
            # 找重叠度最大的节点（优先深层节点）
            for nr in node_ranges:
                node = nr['node']
                node_start, node_end = nr['start'], nr['end']
                
                # 计算重叠区间
                overlap_start = max(para_start, node_start)
                overlap_end = min(para_end, node_end)
                overlap = max(0, overlap_end - overlap_start)
                
                if overlap > max_overlap or (overlap == max_overlap and node.level > (matched_node.level if matched_node else -1)):
                    max_overlap = overlap
                    matched_node = node
            
            # 如果没有找到匹配，使用根节点
            if matched_node is None:
                matched_node = root_node
            
            # 6. 更新段落的关联字段
            if matched_node:
                section_title = self._normalize_title(matched_node.title) or ''
                path = matched_node.path or []
                if isinstance(path, str):
                    try:
                        path = json.loads(path)
                    except json.JSONDecodeError:
                        path = [path]
                path_items = [self._normalize_title(item) for item in path if item]
                section_path = " > ".join([item for item in path_items if item])
                summary = (matched_node.content or para.content)[:200].strip()
                
                # 直接设置外键关联
                para.page_index_node = matched_node
                para.section_title = section_title
                para.section_path = section_path
                para.summary = summary
                updates.append(para)
        
        # 7. 批量更新
        if updates:
            try:
                Paragraph.objects.bulk_update(
                    updates, 
                    ['page_index_node', 'section_title', 'section_path', 'summary']
                )
                print(f"[PageIndex] Updated {len(updates)} paragraphs with precise node association")
            except Exception as e:
                print(f"[PageIndex] Bulk update failed: {e}, falling back to individual saves")
                for para in updates:
                    try:
                        para.save(update_fields=['page_index_node', 'section_title', 'section_path', 'summary'])
                    except Exception as e2:
                        print(f"[PageIndex] Error saving paragraph {para.id}: {e2}")

    def _create_node(
        self,
        document: Document,
        level: int,
        title: str,
        path: List[str],
        content: str,
        parent: Optional[PageIndexNode] = None,
        order: int = 0
    ) -> PageIndexNode:
        """创建PageIndexNode记录"""
        normalized_title = self._normalize_title(title)
        normalized_path = self._normalize_path(path)
        return PageIndexNode.objects.create(
            document=document,
            knowledge=self.knowledge,
            level=level,
            title=normalized_title or title,
            path=normalized_path,
            parent=parent,
            order=order,
            content=content,
            char_count=len(content),
            embedding_status=State.PENDING.value
        )


    
    def _extract_node_content(self, item: Dict, chunk_size: int) -> str:
        """提取节点内容"""
        content_parts = []
        current_length = 0
        
        # 收集子节点内容
        children = item.get('children', [])
        for child in children:
            if child['state'] == 'block':
                if current_length + len(child['content']) > chunk_size:
                    break
                content_parts.append(child['content'])
                current_length += len(child['content'])
        
        return "\n\n".join(content_parts)
    
    def _get_markdown_patterns(self):
        """获取Markdown标题正则"""
        return [
            re.compile('(?<=^)# .*|(?<=\\n)# .*'),
            re.compile('(?<=\\n)(?<!#)## (?!#).*|(?<=^)(?<!#)## (?!#).*'),
            re.compile("(?<=\\n)(?<!#)### (?!#).*|(?<=^)(?<!#)### (?!#).*"),
            re.compile("(?<=\\n)(?<!#)#### (?!#).*|(?<=^)(?<!#)#### (?!#).*"),
        ]
    
    def get_tree_summary(self, max_depth: int = 3) -> str:
        """获取树结构摘要"""
        nodes = PageIndexNode.objects.filter(
            knowledge=self.knowledge,
            level__lte=max_depth
        ).order_by('level', 'order')
        
        summary_lines = []
        for node in nodes:
            indent = "  " * node.level
            summary_lines.append(f"{indent}- {node.title}")
        
        return "\n".join(summary_lines)
    
    def get_statistics(self) -> Dict:
        """获取PageIndex统计信息"""
        total_nodes = PageIndexNode.objects.filter(
            knowledge=self.knowledge
        ).count()
        
        depth_stats = {}
        for level in range(0, 10):
            count = PageIndexNode.objects.filter(
                knowledge=self.knowledge,
                level=level
            ).count()
            if count > 0:
                depth_stats[f"level_{level}"] = count
        
        max_depth = 0
        if depth_stats:
            max_depth = max(int(k.split('_')[1]) for k in depth_stats.keys())
        
        return {
            'total_nodes': total_nodes,
            'depth_distribution': depth_stats,
            'max_depth': max_depth
        }
