class SwiftFeatures:
    def __init__(self):
        self.lineLen = 0
        self.line = ''
        self.in_lambda = -1
        self.in_function = -1
        self.in_guard = -1
        self.in_loop = -1
        self.keywords_count = 0
        self.has_comment = -1
        self.comment_len = 0
        self.in_condition = -1
        self.has_condition = -1
        self.is_declaration = -1
        self.has_class_keyword = -1
        self.has_func_keyword = -1
        self.has_guard_keyword = -1
        self.spaces_count = 0

    def __str__(self):
        iter1 = SwiftFeatures.get_headers()
        iter1.append('line')
        iter2 = self.serialize()
        iter2.append(self.line)
        return str(dict(zip(iter1, iter2)))

    def serialize(self):
        result = [str(self.lineLen), str(self.in_lambda), str(self.in_function), str(self.in_guard), str(self.in_loop),
                  str(self.keywords_count), str(self.has_comment), str(self.comment_len),
                  str(self.in_condition), str(self.has_condition), str(self.is_declaration), str(self.has_class_keyword), str(self.has_func_keyword),
                  str(self.has_guard_keyword), str(self.spaces_count)]
        return result

    @staticmethod
    def get_headers() -> [str]:
        result = ['lineLen', 'in_lambda', 'in_function', 'in_guard', 'in_loop',
                  'keywords_count', 'has_comment', 'comment_len',
                  'in_condition', 'has_condition', 'is_declaration', 'has_class_keyword',
                  'has_func_keyword', 'has_guard_keyword', 'spaces_count']
        return result
