# coding=utf-8
import csv
import io
import traceback

from charset_normalizer import detect
from common.handle.base_parse_qa_handle import get_title_row_index_dict, get_row_value
from common.handle.base_parse_table_handle import BaseParseTableHandle
from common.utils.logger import maxkb_logger


class CsvParseTableHandle(BaseParseTableHandle):
    TITLE_KEYS = {'分段标题', '标题', '段落标题', 'section_title', 'title'}
    CONTENT_KEYS = {'分段内容', '内容', '段落内容', 'content', 'text', '正文'}

    def support(self, file, get_buffer):
        file_name: str = file.name.lower()
        if file_name.endswith(".csv"):
            return True
        return False

    def _extract_paragraph(self, row: dict):
        title = ''
        content = ''
        extras = []
        for key, value in row.items():
            key_text = str(key).strip()
            value_text = '' if value is None else str(value).strip()
            if not title and key_text in self.TITLE_KEYS:
                title = value_text
                continue
            if not content and key_text in self.CONTENT_KEYS:
                content = value_text
                continue
            if key_text:
                extras.append(f"{key_text}: {value_text}")
        if content:
            if extras:
                content = f"{content}\n" + "; ".join(extras)
        else:
            content = "; ".join(extras)
        if not content:
            content = "; ".join([f"{key}: {value}" for key, value in row.items()])
        return {'title': title, 'content': content}


    def handle(self, file, get_buffer, save_image):
        buffer = get_buffer(file)
        try:
            content = buffer.decode(detect(buffer)['encoding'])
        except BaseException as e:
            maxkb_logger.error(f"Error processing CSV file {file.name}: {e}, {traceback.format_exc()}")
            return [{'name': file.name, 'paragraphs': []}]

        csv_model = content.split('\n')
        paragraphs = []
        # 第一行为标题
        title = csv_model[0].split(',')
        for row in csv_model[1:]:
            if not row:
                continue
            row_values = row.split(',')
            row_dict = {key: value for key, value in zip(title, row_values)}
            paragraphs.append(self._extract_paragraph(row_dict))


        return [{'name': file.name, 'paragraphs': paragraphs}]

    def get_content(self, file, save_image):
        buffer = file.read()
        try:
            reader = csv.reader(io.TextIOWrapper(io.BytesIO(buffer), encoding=detect(buffer)['encoding']))
            rows = list(reader)

            if not rows:
                return ""

            # 构建 Markdown 表格
            md_lines = []

            # 添加表头
            header = [cell.replace('\n', '<br>').replace('\r', '') for cell in rows[0]]
            md_lines.append('| ' + ' | '.join(header) + ' |')

            # 添加分隔线
            md_lines.append('| ' + ' | '.join(['---'] * len(header)) + ' |')

            # 添加数据行
            for row in rows[1:]:
                if row:  # 跳过空行
                    # 确保行长度与表头一致,并将换行符转换为 <br>
                    padded_row = [
                                     cell.replace('\n', '<br>').replace('\r', '') for cell in row
                                 ] + [''] * (len(header) - len(row))
                    md_lines.append('| ' + ' | '.join(padded_row[:len(header)]) + ' |')

            return '\n'.join(md_lines)

        except Exception as e:
            maxkb_logger.error(f"Error processing CSV file {file.name}: {e}, {traceback.format_exc()}")
            return ""
