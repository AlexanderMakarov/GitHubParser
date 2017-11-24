from pygments import lex
from pygments.lexers.html import XmlLexer
from features.XmlFeatures import XmlFeatures


class XmlParser:
    def __init__(self):
        self.lexer = XmlLexer()

    def parse(self, lines: [str]) -> [XmlFeatures]:
        nested_level = 0
        spaces_count = 0
        opened_comments = 0
        opened_tags = 0
        remaining_attribute = ''
        lineResults = []
        for line in lines:
            tokens = lex(line, self.lexer)
            features = XmlFeatures()
            features.line = line.rstrip()
            is_before_open_tag = True
            features.openedTagsCnt = opened_tags
            features.openedCommentsCnt = opened_comments
            tokens_count = 0
            tags_len = 0
            attrs_len = 0
            attrs_val_len = 0
            comments_len = 0
            for token in tokens:
                tokens_count += 1
                token_type = str(token[0])
                value = token[1]
                if token_type == 'Token.Name.Tag':
                    if value[0] == '<' and value[1] != '/':
                        features.tagsCount += 1
                        tags_len += value.__len__()
                        features.openedTagsCnt += 1
                    elif '</' in value or '/>' in value:
                        features.closedTagsCnt += 1
                elif token_type == 'Token.Name.Attribute':
                    features.attrCnt += 1
                    attrs_len += value.__len__()
                    remaining_attribute = value[:value.__len__() - 1]
                elif token_type == 'Token.Literal.String':
                    if remaining_attribute != '':
                        attrs_val_len += value.__len__()
                        remaining_attribute = ''
                elif token_type == 'Token.Text':
                    if value.isspace() and is_before_open_tag:
                        is_before_open_tag = False
                        if value.__len__() > spaces_count:
                            nested_level += 1
                            spaces_count = value.__len__()
                        elif value.__len__() < spaces_count:
                            nested_level -= 1
                            spaces_count = value.__len__()
                elif token_type == 'Token.Comment':
                    if value == '<!--':
                        features.openedCommentsCnt += 1
                    elif value == '-->':
                        features.closedCommentsCnt += 1
                    elif value != '\n':
                        features.commentsCnt += 1

            features.nestingLevel = nested_level
            if tokens_count == 1:
                for token in lex(line, self.lexer):
                    if '<!--' in token[1]:
                        features.openedCommentsCnt += 1
                    elif '-->' in token[1]:
                        features.closedCommentsCnt += 1
            features.isComment = 1 if features.openedCommentsCnt > 0 \
                                 and features.closedCommentsCnt == 0 \
                                 and features.openedTagsCnt == opened_tags \
                                 and features.closedTagsCnt == 0 else -1

            opened_tags = features.openedTagsCnt - features.closedTagsCnt
            opened_comments = features.openedCommentsCnt - features.closedCommentsCnt
            if features.isComment:
                features.commentsCnt += 1
            features.avgAttrLen = attrs_len / features.attrCnt if features.attrCnt > 0 else 0
            features.avgAttrValLen = attrs_val_len / features.attrCnt if features.attrCnt > 0 else 0
            features.tagsAvgLen = tags_len / features.tagsCount if features.tagsCount > 0 else 0
            features.avgCommentsLen = comments_len / features.commentsCnt if features.commentsCnt > 0 else 0
            features.lineLen = line.__len__()
            lineResults.append(features)
        return lineResults

    def get_serialized_results(self, lines: [str]) -> [[]]:
        line_results = self.parse(lines)
        result = []
        for lr in line_results:
            result.append(lr.serialize())
        return result
