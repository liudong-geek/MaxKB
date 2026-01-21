# coding=utf-8
"""
    @project: maxkb
    @Author：虎
    @file： base_reset_problem_step.py
    @date：2024/1/10 14:35
    @desc:
"""
from typing import List

from django.utils.translation import gettext as _
from langchain.schema import HumanMessage

from application.chat_pipeline.step.reset_problem_step.i_reset_problem_step import IResetProblemStep
from application.models import ChatRecord
from common.utils.split_model import flat_map
from models_provider.tools import get_model_instance_by_model_workspace_id

prompt = _(
    "You are a query rewrite assistant. Using the chat history, rewrite the user's question ({question}) into a complete and explicit retrieval query. Requirements: 1) Output ONLY the rewritten query inside <data></data>. 2) Remove fillers and politeness. 3) Resolve pronouns based on history. 4) Keep domain terms unchanged. 5) If the question is already clear, return it as-is in <data></data>.")



class BaseResetProblemStep(IResetProblemStep):
    def execute(self, problem_text: str, history_chat_record: List[ChatRecord] = None, model_id: str = None,
                problem_optimization_prompt=None,
                workspace_id=None,
                **kwargs) -> str:
        chat_model = get_model_instance_by_model_workspace_id(model_id, workspace_id) if model_id is not None else None
        if chat_model is None:
            return problem_text
        start_index = len(history_chat_record) - 3
        history_message = [[history_chat_record[index].get_human_message(), history_chat_record[index].get_ai_message()]
                           for index in
                           range(start_index if start_index > 0 else 0, len(history_chat_record))]
        reset_prompt = problem_optimization_prompt if problem_optimization_prompt else prompt
        message_list = [*flat_map(history_message),
                        HumanMessage(content=reset_prompt.replace('{question}', problem_text))]
        response = chat_model.invoke(message_list)

        def clean_text(text: str) -> str:
            if text is None:
                return ''
            cleaned = text.strip().strip('"').strip("'")
            if '\n' in cleaned:
                cleaned = cleaned.splitlines()[0].strip()
            return cleaned

        padding_problem = problem_text
        if response.content.__contains__("<data>") and response.content.__contains__('</data>'):
            padding_problem_data = response.content[
                                   response.content.index('<data>') + 6:response.content.index('</data>')]
            cleaned_problem = clean_text(padding_problem_data)
            if cleaned_problem:
                padding_problem = cleaned_problem
        elif len(response.content) > 0:
            cleaned_problem = clean_text(response.content)
            if cleaned_problem:
                padding_problem = cleaned_problem


        try:
            request_token = chat_model.get_num_tokens_from_messages(message_list)
            response_token = chat_model.get_num_tokens(padding_problem)
        except Exception as e:
            request_token = 0
            response_token = 0
        self.context['message_tokens'] = request_token
        self.context['answer_tokens'] = response_token
        return padding_problem

    def get_details(self, manage, **kwargs):
        return {
            'step_type': 'problem_padding',
            'run_time': self.context['run_time'],
            'model_id': str(manage.context['model_id']) if 'model_id' in manage.context else None,
            'message_tokens': self.context.get('message_tokens', 0),
            'answer_tokens': self.context.get('answer_tokens', 0),
            'cost': 0,
            'padding_problem_text': self.context.get('padding_problem_text'),
            'problem_text': self.context.get("step_args").get('problem_text'),
        }
