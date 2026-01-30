# coding=utf-8
"""
    @project: maxkb
    @Author：虎
    @file： pg_vector.py
    @date：2023/10/19 15:28
    @desc:
"""
import json
import os
import re
from abc import ABC, abstractmethod
from typing import Dict, List


import uuid_utils.compat as uuid
from django.contrib.postgres.search import SearchVector
from django.db.models import QuerySet, Value
from langchain_core.embeddings import Embeddings

from common.db.search import generate_sql_by_query_dict
from common.db.sql_execute import select_list
from common.utils.common import get_file_content
from common.utils.logger import maxkb_logger
from common.utils.ts_vecto_util import to_ts_vector, to_query
from knowledge.models import Embedding, SearchMode, SourceType, Knowledge, PageIndexNode, Paragraph, Document


from knowledge.vector.base_vector import BaseVectorStore
from maxkb.conf import PROJECT_DIR


class PGVector(BaseVectorStore):

    def delete_by_source_ids(self, source_ids: List[str], source_type: str):
        if len(source_ids) == 0:
            return
        QuerySet(Embedding).filter(source_id__in=source_ids, source_type=source_type).delete()

    def update_by_source_ids(self, source_ids: List[str], instance: Dict):
        QuerySet(Embedding).filter(source_id__in=source_ids).update(**instance)

    def vector_is_create(self) -> bool:
        # 项目启动默认是创建好的 不需要再创建
        return True

    def vector_create(self):
        return True

    def _is_page_index_enabled(self, knowledge_id: str) -> bool:
        try:
            from config.page_index_config import PageIndexConfig
            result = PageIndexConfig.is_enabled(knowledge_id)
            maxkb_logger.debug(f'[PageIndex] _is_page_index_enabled({knowledge_id}) = {result}')
            return result
        except Exception as e:
            maxkb_logger.warning(f'[PageIndex] _is_page_index_enabled error: {e}')
            return False

    def _resolve_page_index_node_info(self, paragraph_id: str, document_id: str, knowledge_id: str):
        """
        解析单个段落对应的 PageIndexNode

        匹配策略（按优先级）：
        1. 段落标题精确匹配节点标题（支持清洗后匹配）
        2. 段落内容包含在节点内容中
        3. Fallback 到文档根节点（level=0）
        """
        if not self._is_page_index_enabled(knowledge_id):
            return None

        paragraph = QuerySet(Paragraph).filter(id=paragraph_id).values('title', 'content').first()
        if not paragraph:
            return None

        para_title = (paragraph.get('title') or '').strip()
        para_content = (paragraph.get('content') or '').strip()

        node_query = QuerySet(PageIndexNode).filter(document_id=document_id)
        node = None

        # 策略1：标题精确匹配（支持清洗后匹配）
        normalized_para_title = self._normalize_title(para_title)
        if normalized_para_title:
            nodes = node_query.exclude(title='').exclude(title__isnull=True).values('id', 'level', 'path', 'order', 'title', 'content')
            for n in nodes:
                if self._normalize_title(n.get('title')) == normalized_para_title:
                    node = {
                        'id': n.get('id'),
                        'level': n.get('level'),
                        'path': n.get('path'),
                        'order': n.get('order'),
                        'content': n.get('content')
                    }
                    break


        # 策略2：基于内容匹配
        if node is None and para_content:
            content_prefix = para_content[:100]
            nodes_with_content = node_query.exclude(content='').exclude(content__isnull=True).order_by('-level', 'order')
            for n in nodes_with_content:
                if content_prefix in (n.content or ''):
                    node = {
                        'id': n.id,
                        'level': n.level,
                        'path': n.path,
                        'order': n.order,
                        'content': n.content
                    }
                    break

        # 策略3：Fallback 到根节点
        if node is None:
            node = node_query.filter(level=0).order_by('order').values(
                'id', 'level', 'path', 'order', 'content'
            ).first()

        return node

    def _ensure_page_index_exists(self, document_ids: set, knowledge_id: str):
        """
        确保 PageIndex 节点存在，如果不存在则自动构建
        """
        if not document_ids:
            return

        # 检查是否已有节点
        existing_doc_ids = set(
            str(doc_id) for doc_id in
            QuerySet(PageIndexNode).filter(document_id__in=document_ids).values_list('document_id', flat=True).distinct()
        )

        missing_doc_ids = {str(d) for d in document_ids} - existing_doc_ids
        if not missing_doc_ids:
            return

        # 为缺失的文档构建 PageIndex
        try:
            from knowledge.models import Document, Knowledge
            from knowledge.page_index import PageIndex

            knowledge = QuerySet(Knowledge).filter(id=knowledge_id).first()
            if not knowledge:
                return

            for doc_id in missing_doc_ids:
                document = QuerySet(Document).filter(id=doc_id).first()
                if document:
                    maxkb_logger.info(f'[PageIndex] Auto building for document {doc_id} before embedding')
                    PageIndex.from_documents(
                        documents=[document],
                        knowledge=knowledge,
                        chunk_size=1000,
                        chunk_overlap=200
                    )
        except Exception as e:
            maxkb_logger.warning(f'[PageIndex] Auto build failed: {e}')

    def _resolve_page_index_node_map(self, text_list: List[Dict]):
        """
        【Phase 3 简化】获取段落到 PageIndexNode 的映射关系
        
        重构后：直接从 Paragraph.page_index_node 读取已建立的外键关联，
        无需再进行模糊匹配。
        """
        paragraph_source_types = {
            SourceType.PARAGRAPH,
            SourceType.TITLE,
            SourceType.SUMMARY,
            SourceType.PARAGRAPH.value,
            SourceType.TITLE.value,
            SourceType.SUMMARY.value
        }
        paragraph_ids = [
            row.get('paragraph_id') for row in text_list
            if row.get('paragraph_id') and str(row.get('source_type')) in paragraph_source_types
        ]

        if not paragraph_ids:
            return {}

        # 直接查询 Paragraph 及其关联的 page_index_node
        paragraphs = list(QuerySet(Paragraph).filter(id__in=paragraph_ids).select_related('page_index_node'))
        
        node_map = {}
        for para in paragraphs:
            if para.page_index_node:
                # 构建与旧接口兼容的 node_info 字典
                node = para.page_index_node
                node_map[str(para.id)] = {
                    'id': str(node.id),
                    'title': node.title,
                    'level': node.level,
                    'path': node.path,
                    'order': node.order,
                    'document_id': str(node.document_id),
                    'content': node.content
                }
        
        maxkb_logger.info(f'[PageIndex] _resolve_page_index_node_map: {len(node_map)}/{len(paragraph_ids)} paragraphs have node association')
        if node_map:
             # Debug log: print first resolved node info
             first_key = list(node_map.keys())[0]
             node_info = node_map[first_key]
             maxkb_logger.info(f"[PageIndex] Debug Node Content: ID={node_info['id']}, ContentLen={len(node_info.get('content', '') or '')}")
        return node_map

    def _get_embedding_meta_maps(self, knowledge_ids: set, document_ids: set):
        knowledge_map = {}
        document_map = {}
        if knowledge_ids:
            knowledge_map = {
                str(item.get('id')): item
                for item in QuerySet(Knowledge).filter(id__in=knowledge_ids).values('id', 'name', 'meta')
            }
        if document_ids:
            document_map = {
                str(item.get('id')): item
                for item in QuerySet(Document).filter(id__in=document_ids).values('id', 'name', 'meta')
            }
        return knowledge_map, document_map

    @staticmethod
    def _build_embedding_meta(knowledge_info: Dict, document_info: Dict, raw_text: str, is_paragraph: bool):
        meta = {}
        knowledge_meta = (knowledge_info or {}).get('meta') or {}
        document_meta = (document_info or {}).get('meta') or {}

        def parse_weight(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        source = document_meta.get('source') or knowledge_meta.get('source') or (knowledge_info or {}).get('name')
        if source:
            meta['source'] = source

        source_weight = (
            document_meta.get('source_weight')
            or document_meta.get('weight')
            or document_meta.get('priority')
            or knowledge_meta.get('source_weight')
            or knowledge_meta.get('weight')
            or knowledge_meta.get('priority')
        )
        source_weight = parse_weight(source_weight)
        if source_weight is not None:
            meta['source_weight'] = max(source_weight, 0.0)


        knowledge_name = (knowledge_info or {}).get('name')
        if knowledge_name:
            meta['knowledge_name'] = knowledge_name

        document_name = (document_info or {}).get('name')
        if document_name:
            meta['document_name'] = document_name

        author = document_meta.get('author') or knowledge_meta.get('author')
        if author:
            meta['author'] = author

        published_at = document_meta.get('published_at') or document_meta.get('publish_time') or document_meta.get('created_at')
        if published_at:
            meta['published_at'] = published_at

        if is_paragraph and raw_text:
            quality_score = min(len(raw_text) / 1000.0, 1.0)
            meta['quality_score'] = round(quality_score, 3)

        return meta

    @staticmethod
    def _normalize_title(title: str) -> str:
        if not title:
            return ''
        cleaned = re.sub(r'^\s*#+\s*', '', str(title))
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    @staticmethod
    def _build_title_context(title: str) -> str:
        normalized_title = PGVector._normalize_title(title)
        return f"章节标题：{normalized_title}" if normalized_title else ''

    def _build_embedding_context(self, node_info: Dict):

        if not node_info:
            return ''
        path = node_info.get('path') or []
        if isinstance(path, str):
            try:
                path = json.loads(path)
            except json.JSONDecodeError:
                path = [path]
        path_items = [self._normalize_title(item) for item in path]
        path_items = [item for item in path_items if item]
        path_text = " > ".join(path_items)
        title = self._normalize_title(node_info.get('title'))
        context_parts = []
        if path_text:
            context_parts.append(f"章节路径：{path_text}")
        if title and (not path_text or title not in path_text):
            context_parts.append(f"章节标题：{title}")
        
        # 注入章节摘要（内容）
        summary = (node_info.get('content') or '').strip()
        if summary:
            # 截取前500字符作为摘要，避免token过长
            summary_text = summary[:500].replace('\n', ' ')
            context_parts.append(f"章节摘要：{summary_text}")

        return "\n".join(context_parts)



    def _save(self, text, source_type: SourceType, knowledge_id: str, document_id: str, paragraph_id: str,
              source_id: str,
              is_active: bool,
              embedding: Embeddings):

        raw_text = text or ''
        text_for_embedding = raw_text
        # 兼容 source_type 为整数或枚举的情况
        is_section_embedding = source_type in (
            SourceType.PARAGRAPH,
            SourceType.TITLE,
            SourceType.SUMMARY,
            SourceType.PARAGRAPH.value,
            SourceType.TITLE.value,
            SourceType.SUMMARY.value
        )
        node_info = None
        if is_section_embedding and paragraph_id:
            node_info = self._resolve_page_index_node_info(paragraph_id, document_id, knowledge_id)
            if node_info:
                context_text = self._build_embedding_context(node_info)
            else:
                paragraph_title = QuerySet(Paragraph).filter(id=paragraph_id).values_list('title', flat=True).first()
                context_text = self._build_title_context(paragraph_title)
            if context_text:
                text_for_embedding = f"{context_text}\n{text_for_embedding}"



        text_embedding = [float(x) for x in embedding.embed_query(text_for_embedding)]
        embedding = Embedding(
            id=uuid.uuid7(),
            knowledge_id=knowledge_id,
            document_id=document_id,
            is_active=is_active,
            paragraph_id=paragraph_id,
            source_id=source_id,
            embedding=text_embedding,
            source_type=source_type,
            search_vector=to_ts_vector(text_for_embedding)
        )
        if node_info:
            embedding.page_index_node_id = node_info.get('id')
            embedding.tree_level = node_info.get('level', 0)
            embedding.tree_path = node_info.get('path', [])
            embedding.sibling_index = node_info.get('order', 0)


        knowledge_info = QuerySet(Knowledge).filter(id=knowledge_id).values('id', 'name', 'meta').first()
        document_info = QuerySet(Document).filter(id=document_id).values('id', 'name', 'meta').first()
        embedding_meta = self._build_embedding_meta(knowledge_info, document_info, raw_text, is_section_embedding)

        if embedding_meta:
            embedding.meta = embedding_meta


        embedding.save()
        return True



    def _batch_save(self, text_list: List[Dict], embedding: Embeddings, is_the_task_interrupted):
        filtered_text_list = [row for row in text_list if (row.get('text') or '').strip()]
        if len(filtered_text_list) != len(text_list):
            maxkb_logger.info(f'[PageIndex] _batch_save: filtered empty text {len(text_list) - len(filtered_text_list)}')
        text_list = filtered_text_list
        if not text_list:
            return True

        # 调试日志：检查 text_list 的内容
        maxkb_logger.info(f'[PageIndex] _batch_save: text_list count={len(text_list)}')
        if text_list:
            sample = text_list[0]
            maxkb_logger.info(f'[PageIndex] _batch_save sample: source_type={sample.get("source_type")} (type={type(sample.get("source_type")).__name__}), paragraph_id={sample.get("paragraph_id")}')

        node_map = self._resolve_page_index_node_map(text_list)
        maxkb_logger.info(f'[PageIndex] _batch_save: node_map size={len(node_map)}')
        if node_map and text_list:
            # DEBUG: Check key mismatch
            row_id = str(text_list[0].get('paragraph_id'))
            map_keys = list(node_map.keys())
            maxkb_logger.info(f"[PageIndex] Key Mismatch Debug: RowID='{row_id}' (len={len(row_id)}) vs MapKeys={map_keys[:3]} (FirstKeyLen={len(map_keys[0]) if map_keys else 0})")


        knowledge_ids = {str(row.get('knowledge_id')) for row in text_list if row.get('knowledge_id')}
        document_ids = {str(row.get('document_id')) for row in text_list if row.get('document_id')}
        knowledge_map, document_map = self._get_embedding_meta_maps(knowledge_ids, document_ids)

        paragraph_ids = [str(row.get('paragraph_id')) for row in text_list if row.get('paragraph_id')]
        title_map = {}
        if paragraph_ids:
            title_map = {
                str(item.get('id')): item.get('title')
                for item in QuerySet(Paragraph).filter(id__in=paragraph_ids).values('id', 'title')
            }

        embedding_texts = []
        base_texts = []
        matched_count = 0
        for row in text_list:
            base_text = row.get('text') or ''
            source_type = row.get('source_type')
            is_section_embedding = str(source_type) in (
                SourceType.PARAGRAPH,
                SourceType.TITLE,
                SourceType.SUMMARY,
                SourceType.PARAGRAPH.value,
                SourceType.TITLE.value,
                SourceType.SUMMARY.value
            )
            context_text = ''
            if is_section_embedding and row.get('paragraph_id'):
                node_info = node_map.get(str(row.get('paragraph_id')))
                if node_info:
                    context_text = self._build_embedding_context(node_info)
                    matched_count += 1
                else:
                    paragraph_title = title_map.get(str(row.get('paragraph_id')))
                    context_text = self._build_title_context(paragraph_title)

            embedding_text = f"{context_text}\n{base_text}" if context_text else base_text
            embedding_texts.append(embedding_text)
            base_texts.append(base_text)


        embeddings = embedding.embed_documents(embedding_texts)


        embedding_list = []
        # matched_count already calculated above
        for index in range(0, len(embedding_texts)):

            row = text_list[index]
            base_text = base_texts[index]
            embedding_text = embedding_texts[index]
            embedding_item = Embedding(
                id=uuid.uuid7(),
                document_id=row.get('document_id'),
                paragraph_id=row.get('paragraph_id'),
                knowledge_id=row.get('knowledge_id'),
                is_active=row.get('is_active', True),
                source_id=row.get('source_id'),
                source_type=row.get('source_type'),
                embedding=[float(x) for x in embeddings[index]],
                search_vector=SearchVector(Value(to_ts_vector(embedding_text)))
            )

            # 兼容 source_type 为整数或枚举的情况
            source_type = row.get('source_type')
            is_section_embedding = source_type in (
                SourceType.PARAGRAPH,
                SourceType.TITLE,
                SourceType.SUMMARY,
                SourceType.PARAGRAPH.value,
                SourceType.TITLE.value,
                SourceType.SUMMARY.value
            )
            if is_section_embedding and row.get('paragraph_id'):
                node_info = node_map.get(str(row.get('paragraph_id')))
                if node_info:
                    embedding_item.page_index_node_id = node_info.get('id')
                    embedding_item.tree_level = node_info.get('level', 0)
                    embedding_item.tree_path = node_info.get('path', [])
                    embedding_item.sibling_index = node_info.get('order', 0)
                    matched_count += 1


            knowledge_info = knowledge_map.get(str(row.get('knowledge_id'))) if row.get('knowledge_id') else None
            document_info = document_map.get(str(row.get('document_id'))) if row.get('document_id') else None
            embedding_meta = self._build_embedding_meta(knowledge_info, document_info, base_text, is_section_embedding)

            if embedding_meta:
                embedding_item.meta = embedding_meta

            embedding_list.append(embedding_item)


        maxkb_logger.info(f'[PageIndex] _batch_save: matched_count={matched_count}/{len(embedding_list)}')

        if not is_the_task_interrupted():
            QuerySet(Embedding).bulk_create(embedding_list) if len(embedding_list) > 0 else None
        return True


    def hit_test(self, query_text, knowledge_id_list: list[str], exclude_document_id_list: list[str], top_number: int,
                 similarity: float,
                 search_mode: SearchMode,
                 embedding: Embeddings,
                 vector_weight: float = None,
                 keyword_weight: float = None):
        if knowledge_id_list is None or len(knowledge_id_list) == 0:
            return []
        exclude_dict = {}
        embedding_query = embedding.embed_query(query_text)
        query_set = QuerySet(Embedding).filter(knowledge_id__in=knowledge_id_list, is_active=True)
        if exclude_document_id_list is not None and len(exclude_document_id_list) > 0:
            exclude_dict.__setitem__('document_id__in', exclude_document_id_list)
        query_set = query_set.exclude(**exclude_dict)

        page_index_results = self._try_page_index_search(
            knowledge_id_list,
            query_text,
            embedding_query,
            top_number,
            similarity,
            search_mode,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight
        )
        if page_index_results is not None:
            return page_index_results

        for search_handle in search_handle_list:
            if search_handle.support(search_mode):
                # 对于 BlendSearch，传递权重参数
                if hasattr(search_handle, 'handle') and search_mode == SearchMode.blend:
                    return search_handle.handle(query_set, query_text, embedding_query, top_number, similarity, 
                                               search_mode, vector_weight, keyword_weight)
                else:
                    return search_handle.handle(query_set, query_text, embedding_query, top_number, similarity, search_mode)

        return []


    def query(self, query_text: str, query_embedding: List[float], knowledge_id_list: list[str],
              document_id_list: list[str],
              exclude_document_id_list: list[str],
              exclude_paragraph_list: list[str], is_active: bool, top_n: int, similarity: float,
              search_mode: SearchMode, vector_weight: float = None, keyword_weight: float = None):
        exclude_dict = {}
        if knowledge_id_list is None or len(knowledge_id_list) == 0:
            return []
        query_set = QuerySet(Embedding).filter(knowledge_id__in=knowledge_id_list, is_active=is_active)
        if document_id_list is not None and len(document_id_list) > 0:
            query_set = query_set.filter(document_id__in=document_id_list)
        if exclude_document_id_list is not None and len(exclude_document_id_list) > 0:
            query_set = query_set.exclude(document_id__in=exclude_document_id_list)
        if exclude_paragraph_list is not None and len(exclude_paragraph_list) > 0:
            query_set = query_set.exclude(paragraph_id__in=exclude_paragraph_list)
        query_set = query_set.exclude(**exclude_dict)

        # 【方案B】检查是否启用PageIndex检索模式
        page_index_results = self._try_page_index_search(
            knowledge_id_list,
            query_text,
            query_embedding,
            top_n,
            similarity,
            search_mode
        )
        if page_index_results is not None:
            return page_index_results

        # 回退到传统检索模式
        for search_handle in search_handle_list:
            if search_handle.support(search_mode):
                if isinstance(search_handle, BlendSearch):
                    return search_handle.handle(query_set, query_text, query_embedding, top_n, similarity, search_mode,
                                                vector_weight, keyword_weight)
                return search_handle.handle(query_set, query_text, query_embedding, top_n, similarity, search_mode)

    def _try_page_index_search(
        self,
        knowledge_id_list: list[str],
        query_text: str,
        query_embedding: List[float],
        top_n: int,
        similarity: float,
        search_mode: SearchMode,
        section_filter: List[str] = None,
        aggregate_by_section: bool = False,
        vector_weight: float = None,
        keyword_weight: float = None
    ):
        """
        尝试使用PageIndex检索（方案B）

        检查知识库是否配置了PageIndex检索模式，如果是则使用PageIndex检索

        Args:
            knowledge_id_list: 知识库ID列表
            query_text: 查询文本
            query_embedding: 查询向量
            top_n: 返回数量
            similarity: 相似度阈值
            search_mode: 检索模式
            section_filter: 章节过滤列表（节点ID列表），只搜索这些章节下的内容
            aggregate_by_section: 是否按章节聚合结果

        Returns:
            PageIndex检索结果，如果未启用则返回None
        """
        try:
            from knowledge.models import Knowledge
            from knowledge.page_index.page_index_retriever import PageIndexRetriever

            # 获取第一个知识库（简化处理，假设只有一个知识库）
            knowledge = Knowledge.objects.filter(id__in=knowledge_id_list).first()
            if not knowledge:
                return None

            try:
                from config.page_index_config import PageIndexConfig
                if not PageIndexConfig.is_enabled(str(knowledge.id)):
                    return None
            except Exception:
                return None

            meta = knowledge.meta or {}
            # 检查知识库是否配置了PageIndex检索模式
            search_mode_config = meta.get('search_mode', 'traditional')
            if search_mode_config != 'page_index':
                return None  # 未启用PageIndex检索模式


            # 检查PageIndexNode是否有数据
            from knowledge.models import PageIndexNode
            page_index_count = PageIndexNode.objects.filter(
                knowledge_id=knowledge.id
            ).count()

            if page_index_count == 0:
                # PageIndex未构建，回退到传统检索
                return None

            # 使用PageIndex检索
            # 注意：page_index 是检索类型，不是检索模式
            # 检索模式应该是 embedding/keywords/blend，从 meta 配置读取或默认使用 blend
            search_mode_str = meta.get('inner_search_mode', 'blend')
            # 如果传入的 search_mode 是有效的检索模式（非 page_index），则使用传入值
            if search_mode and search_mode.value in ('embedding', 'keywords', 'blend'):
                search_mode_str = search_mode.value
            use_tree_filter = meta.get('use_tree_filter', True)
            meta_top_n = meta.get('top_n', top_n)
            meta_similarity = meta.get('similarity_threshold', similarity)
            # 从 meta 获取聚合配置，或使用传入参数
            meta_aggregate = meta.get('aggregate_by_section', aggregate_by_section)

            retriever = PageIndexRetriever(
                knowledge_id=str(knowledge.id),
                use_tree_filter=use_tree_filter,
                search_mode=search_mode_str,
                top_n=meta_top_n,
                similarity_threshold=meta_similarity,
                section_filter=section_filter,
                aggregate_by_section=meta_aggregate,
                vector_weight=vector_weight,
                keyword_weight=keyword_weight
            )


            results = retriever.query(
                query_text=query_text,
                query_embedding=query_embedding,
                top_n=meta_top_n,
                similarity_threshold=meta_similarity
            )


            return results

        except Exception as e:
            maxkb_logger.warning(f'[PageIndex] Search failed: {e}')
            # PageIndex检索失败，回退到传统检索
            return None

    def update_by_source_id(self, source_id: str, instance: Dict):
        QuerySet(Embedding).filter(source_id=source_id).update(**instance)

    def update_by_paragraph_id(self, paragraph_id: str, instance: Dict):
        QuerySet(Embedding).filter(paragraph_id=paragraph_id).update(**instance)

    def update_by_paragraph_ids(self, paragraph_id: str, instance: Dict):
        QuerySet(Embedding).filter(paragraph_id__in=paragraph_id).update(**instance)

    def delete_by_knowledge_id(self, knowledge_id: str):
        QuerySet(Embedding).filter(knowledge_id=knowledge_id).delete()

    def delete_by_knowledge_id_list(self, knowledge_id_list: List[str]):
        QuerySet(Embedding).filter(knowledge_id__in=knowledge_id_list).delete()

    def delete_by_document_id(self, document_id: str):
        QuerySet(Embedding).filter(document_id=document_id).delete()
        return True

    def delete_by_document_id_list(self, document_id_list: List[str]):
        if len(document_id_list) == 0:
            return True
        return QuerySet(Embedding).filter(document_id__in=document_id_list).delete()

    def delete_by_source_id(self, source_id: str, source_type: str):
        QuerySet(Embedding).filter(source_id=source_id, source_type=source_type).delete()
        return True

    def delete_by_paragraph_id(self, paragraph_id: str):
        QuerySet(Embedding).filter(paragraph_id=paragraph_id).delete()

    def delete_by_paragraph_ids(self, paragraph_ids: List[str]):
        QuerySet(Embedding).filter(paragraph_id__in=paragraph_ids).delete()


class ISearch(ABC):
    @abstractmethod
    def support(self, search_mode: SearchMode):
        pass

    @abstractmethod
    def handle(self, query_set, query_text, query_embedding, top_number: int,
               similarity: float, search_mode: SearchMode):
        pass


class EmbeddingSearch(ISearch):
    MAX_CANDIDATE_LIMIT = 200

    def handle(self,
               query_set,
               query_text,
               query_embedding,
               top_number: int,
               similarity: float,
               search_mode: SearchMode):
        
        # 优化：采用两阶段检索 (Candidate Generation + Reranking)
        # 1. 候选集生成 (Candidate Generation) - 利用 HNSW 索引
        candidate_top_k = self.MAX_CANDIDATE_LIMIT
        
        # 使用 <=> 运算符利用 vector 索引
        vector_candidate_sql = """
            SELECT id FROM embedding 
            ${embedding_query} 
            ORDER BY embedding <=> %s 
            LIMIT %s
        """
        
        v_sql, v_params = generate_sql_by_query_dict(
            {'embedding_query': query_set},
            select_string=vector_candidate_sql,
            with_table_name=True
        )
        
        candidate_ids = set()
        try:
            # 参数顺序：WhereParams + QueryVector + Limit
            # 注意: generate_sql_by_query_dict 返回的 v_sql 可能包含 params 占位符
            # v_params 是 query_set 过滤条件的参数
            vector_results = select_list(v_sql, [*v_params, json.dumps(query_embedding), candidate_top_k])
            for row in vector_results:
                candidate_ids.add(str(row['id']))
        except Exception as e:
            maxkb_logger.error(f"[EmbeddingSearch] Candidate generation failed: {e}")
            pass
            
        maxkb_logger.warning(f"[EmbeddingSearch] Candidate Generation: Count={len(candidate_ids)}")
        
        # 2. 精确重排 (Reranking)
        # 如果有候选，限制范围；否则（或索引失效时）回退到全表扫描（虽然慢但保底）
        # 只有当确实找到了候选才过滤，否则如果因为某种原因没找到（比如索引还没建好），就走原来逻辑？
        # 不，如果用了 query_set 依然没结果，说明真的没有。
        # 这里为了稳健：如果有 id，则 filter(id__in=...)
        if candidate_ids:
            final_query_set = query_set.filter(id__in=list(candidate_ids))
        else:
            # 候选集为空，可能是真的没匹配，或者 query_set 本身就没数据
            # 直接使用原始 query_set (可能会全表扫描，但在无结果时也很快)
            final_query_set = query_set

        exec_sql, exec_params = generate_sql_by_query_dict({'embedding_query': final_query_set},
                                                           select_string=get_file_content(
                                                               os.path.join(PROJECT_DIR, "apps", "knowledge", 'sql',
                                                                            'embedding_search.sql')),
                                                           with_table_name=True)
                                                           
        # 调整默认阈值为 0.5 (Winston: catch more relevant but lower-score items)
        similarity_val = similarity if similarity is not None else 0.5
        top_n_val = top_number if top_number is not None else 5
        
        # maxkb_logger.warning(f"[EmbeddingSearch] Reranking: similarity={similarity_val}, top_n={top_n_val}")

        embedding_model = select_list(exec_sql, [
            len(query_embedding),
            json.dumps(query_embedding),
            *exec_params,
            similarity_val,
            top_n_val
        ])
        
        # maxkb_logger.warning(f"[EmbeddingSearch] Finish: Return={len(embedding_model)}")
        return embedding_model


    def support(self, search_mode: SearchMode):
        return search_mode.value == SearchMode.embedding.value


class KeywordsSearch(ISearch):
    def handle(self,
               query_set,
               query_text,
               query_embedding,
               top_number: int,
               similarity: float,
               search_mode: SearchMode):
        exec_sql, exec_params = generate_sql_by_query_dict({'keywords_query': query_set},
                                                           select_string=get_file_content(
                                                               os.path.join(PROJECT_DIR, "apps", "knowledge", 'sql',
                                                                            'keywords_search.sql')),
                                                           with_table_name=True)
        query_tokens = to_query(query_text)
        embedding_model = select_list(exec_sql, [
            query_tokens,
            query_tokens,
            *exec_params,
            similarity,
            top_number
        ])
        return embedding_model

    def support(self, search_mode: SearchMode):
        return search_mode.value == SearchMode.keywords.value


class BlendSearch(ISearch):
    def handle(self,
               query_set,
               query_text,
               query_embedding,
               top_number: int,
               similarity: float,
               search_mode: SearchMode,
               vector_weight: float = None,
               keyword_weight: float = None):
        # 1. 候选集生成 (Candidate Generation)
        candidate_top_k = 100
        candidate_ids = set()

        # 1.1 向量检索候选 (Vector Candidates) - 利用 HNSW 索引
        # 注意：generate_sql_by_query_dict 会将 ${embedding_query} 替换为 WHERE ...
        # 我们把 ORDER BY 放最后，参数顺序：[...where_params, query_vector, limit]
        vector_candidate_sql = """
            SELECT id FROM embedding 
            ${embedding_query} 
            ORDER BY embedding <=> %s 
            LIMIT %s
        """
        v_sql, v_params = generate_sql_by_query_dict(
            {'embedding_query': query_set},
            select_string=vector_candidate_sql,
            with_table_name=True
        )
        
        try:
            # 参数顺序：WhereParams + QueryVector + Limit
            vector_results = select_list(v_sql, [*v_params, json.dumps(query_embedding), candidate_top_k])
            for row in vector_results:
                candidate_ids.add(str(row['id']))
        except Exception as e:
            maxkb_logger.error(f"[BlendSearch] Vector candidate generation failed: {e}")

        # 1.2 关键词检索候选 (Keyword Candidates) - 利用 GIN 索引
        # 必须加上 search_vector @@ ... 条件才能利用索引
        query_tokens = to_query(query_text)
        keyword_candidate_sql = """
            SELECT id FROM embedding 
            ${embedding_query} 
            AND search_vector @@ to_tsquery('simple', %s)
            ORDER BY ts_rank_cd(search_vector, to_tsquery('simple', %s), 32) DESC 
            LIMIT %s
        """
        k_sql, k_params = generate_sql_by_query_dict(
            {'embedding_query': query_set},
            select_string=keyword_candidate_sql,
            with_table_name=True
        )

        try:
            # 参数顺序：WhereParams + QueryTokens(Match) + QueryTokens(Rank) + Limit
            keyword_results = select_list(k_sql, [*k_params, query_tokens, query_tokens, candidate_top_k])
            for row in keyword_results:
                candidate_ids.add(str(row['id']))
        except Exception as e:
            maxkb_logger.error(f"[BlendSearch] Keyword candidate generation failed: {e}")

        maxkb_logger.warning(
            f"[BlendSearch] Candidate Generation: Vector={len(vector_results) if 'vector_results' in locals() else 0}, "
            f"Keyword={len(keyword_results) if 'keyword_results' in locals() else 0}, "
            f"Total Unique={len(candidate_ids)}"
        )

        # 2. 如果没有候选，直接返回空
        if not candidate_ids:
            return []

        # 3. 精确重排 (Reranking) - 仅对候选集进行复杂打分
        # 将 query_set 限制在 candidate_ids 范围内
        final_query_set = query_set.filter(id__in=list(candidate_ids))

        exec_sql, exec_params = generate_sql_by_query_dict({'embedding_query': final_query_set},
                                                           select_string=get_file_content(
                                                               os.path.join(PROJECT_DIR, "apps", "knowledge", 'sql',
                                                                            'blend_search.sql')),
                                                           with_table_name=True)
        
        # 调试日志：检索参数
        maxkb_logger.warning(f"[BlendSearch] Reranking: vector_weight={vector_weight}, keyword_weight={keyword_weight}, "
                            f"query_tokens='{query_tokens}', similarity={similarity}, top_n={top_number}")

        embedding_model = select_list(exec_sql, [
            vector_weight,  # Vector weight (dynamic)
            keyword_weight,  # Keyword weight (dynamic)
            vector_weight,  # Vector weight for comprehensive_score
            keyword_weight,  # Keyword weight for comprehensive_score
            len(query_embedding),
            json.dumps(query_embedding),
            query_tokens,
            query_tokens,  # 传递第二次，用于归一化计算的分母
            *exec_params, similarity,
            top_number
        ])
        
        maxkb_logger.warning(f"[BlendSearch] Finish: Return={len(embedding_model)}")
        return embedding_model

    def support(self, search_mode: SearchMode):
        return search_mode.value == SearchMode.blend.value


search_handle_list = [EmbeddingSearch(), KeywordsSearch(), BlendSearch()]
