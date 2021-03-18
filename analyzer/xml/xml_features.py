class XmlFeatures:
    def __init__(self):
        self.tagsCount = 0
        self.attrCnt = 0
        self.openedTagsCnt = 0
        self.closedTagsCnt = 0
        self.openedCommentsCnt = 0
        self.closedCommentsCnt = 0
        self.commentsCnt = 0
        self.isComment = -1
        self.lineLen = 0
        self.line = ''

    def __str__(self):
        iter1 = XmlFeatures.get_headers()
        iter1.append('line')
        iter2 = self.serialize()
        iter2.append(self.line)
        return str(dict(zip(iter1, iter2)))

    def serialize(self):
        result = [str(self.tagsCount), str(self.attrCnt),
                  str(self.openedTagsCnt), str(self.closedTagsCnt), str(self.openedCommentsCnt),
                  str(self.closedCommentsCnt), str(self.commentsCnt), str(self.isComment), str(self.lineLen)]
        return result

    @staticmethod
    def get_headers() -> [str]:
        result = ['tagsCount', 'attrCnt',
                  'openedTagsCnt', 'closedTagsCnt', 'openedCommentsCnt',
                  'closedCommentsCnt', 'commentsCnt', 'isComment',
                  'lineLen']
        return result
