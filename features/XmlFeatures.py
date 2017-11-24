class XmlFeatures:
    def __init__(self):
        self.tagsCount = 0
        self.tagsAvgLen = 0.0
        self.attrCnt = 0
        self.avgAttrLen = 0.0
        self.avgAttrValLen = 0.0
        self.openedTagsCnt = 0
        self.closedTagsCnt = 0
        self.nestingLvl = 0
        self.openedCommentsCnt = 0
        self.closedCommentsCnt = 0
        self.commentsCnt = 0
        self.avgCommentsLen = 0.0
        self.isComment = -1
        self.lineLen = 0
        self.line = ''

    def serialize(self):
        result = [str(self.tagsCount), str(self.tagsAvgLen), str(self.attrCnt), str(self.avgAttrLen), str(self.avgAttrValLen),
                  str(self.openedTagsCnt), str(self.closedTagsCnt), str(self.nestingLvl), str(self.openedCommentsCnt),
                  str(self.closedCommentsCnt), str(self.commentsCnt), str(self.avgCommentsLen), str(self.isComment), str(self.lineLen)]
        return result

    @staticmethod
    def get_headers() -> [str]:
        result = ['tagsCount', 'tagsAvgLen', 'attrCnt', 'avgAttrLen', 'avgAttrValLen',
                  'openedTagsCnt', 'closedTagsCnt', 'nestingLvl', 'openedCommentsCnt',
                  'closedCommentsCnt', 'commentsCnt', 'avgCommentsLen', 'isComment',
                  'lineLen']
        return result
