from pygments import lex
from pygments.lexers.objective import SwiftLexer

from analyzer.swift.swift_features import SwiftFeatures


class SwiftParser:
    def __init__(self):
        self.lexer = SwiftLexer()

    def parse(self, lines: [str]) -> [SwiftFeatures]:
        is_function_scope = False
        is_lambda_scope = False
        is_guard_scope = False
        is_loop_scope = False
        is_condition_scope = False
        is_multiline_comment = False
        is_single_comment = False
        is_opened_round_brackets = False
        is_pierce_expected = False
        else_captured = False
        scope_stack = []
        line_results = []
        comments_len = 0
        for line in lines:
            tokens = lex(line, self.lexer)
            features = SwiftFeatures()
            features.line = line.rstrip()
            tokens_count = 0
            is_before_any_token = True

            for token in tokens:
                tokens_count += 1
                token_type = str(token[0])
                value = token[1]

                if is_single_comment and token_type != 'Token.Comment.Single':
                    is_single_comment = False
                    features.comment_len = comments_len
                    comments_len = 0

                elif else_captured and token_type not in ['Token.Text', 'Token.Punctuation']:
                    else_captured = False
                    is_condition_scope = False

                elif is_multiline_comment and token_type != 'Token.Comment.Multiline':
                    comments_len += len(value)
                    features.has_comment = 1

                elif token_type == 'Token.Text':
                    if value.isspace() and is_before_any_token:
                        features.spaces_count = len(value)
                        is_before_any_token = False

                elif token_type == 'Token.Comment.Multiline':
                    features.has_comment = 1
                    if '/*' in value:
                        is_multiline_comment = True
                        comments_len += len(value)
                    elif '*/' in value:
                        is_multiline_comment = False
                        comments_len += len(value)
                        features.comment_len = comments_len
                        comments_len = 0
                    elif is_multiline_comment:
                        comments_len += len(value)

                elif token_type == 'Token.Comment.Single':
                    features.has_comment = 1
                    if '//' in value:
                        is_single_comment = True
                        comments_len += len(value)
                    elif is_single_comment:
                        comments_len += len(value)

                elif 'Token.Keyword' in token_type:
                    features.keywords_count += 1
                    if 'Declaration' in token_type:
                        features.is_declaration = 1
                        if value == 'func':
                            is_function_scope = 1
                            scope_stack.append('function')
                            features.has_func_keyword = 1
                    elif value == 'if':
                        is_condition_scope = 1
                        scope_stack.append('condition')
                        else_captured = False
                        features.has_condition = 1
                    elif value == 'else' and not is_guard_scope:
                        else_captured = True
                    elif value == 'guard':
                        is_guard_scope = 1
                        scope_stack.append('guard')
                        features.has_guard_keyword = 1
                    elif value == 'func':
                        is_function_scope = 1
                        scope_stack.append('function')
                        features.has_func_keyword = 1
                    elif value == 'class':
                        features.has_class_keyword = 1
                    elif value in ['for', 'while'] or value == 'while' and not is_loop_scope:
                        is_loop_scope = True
                        scope_stack.append('loop')

                elif token_type == 'Token.Punctuation':
                    if is_pierce_expected and value != '->':
                        is_pierce_expected = False

                    if value == '(':
                        is_opened_round_brackets = True
                    elif value == ')' and is_opened_round_brackets:
                        is_opened_round_brackets = False
                        is_pierce_expected = True
                    elif value == '->' and is_pierce_expected:
                        is_lambda_scope = True
                        scope_stack.append('lambda')
                    elif value == '}':
                        if len(scope_stack) > 0:
                            last_input = scope_stack[-1:]
                            scope_stack = scope_stack[1:]
                            if last_input == 'condition' and 'condition' not in scope_stack:
                                is_condition_scope = False
                            elif last_input == 'function' and 'function' not in scope_stack:
                                is_function_scope = False
                            elif last_input == 'lambda' and 'lambda' not in scope_stack:
                                is_lambda_scope = False
                            elif last_input == 'guard' and 'guard' not in scope_stack:
                                is_guard_scope = False
                            elif last_input == 'loop' and 'loop' not in scope_stack:
                                is_loop_scope = False

            features.in_condition = 1 if is_condition_scope else -1
            features.in_function = 1 if is_function_scope else -1
            features.in_lambda = 1 if is_lambda_scope else -1
            features.in_loop = 1 if is_loop_scope else -1
            features.in_guard = 1 if is_guard_scope else -1
            # features.comment_len = comments_len
            features.lineLen = line.__len__()
            line_results.append(features)
        return line_results

    def get_serialized_results(self, lines: [str]) -> [[]]:
        line_results = self.parse(lines)
        result = []
        for lr in line_results:
            result.append(lr.serialize())
        return result
