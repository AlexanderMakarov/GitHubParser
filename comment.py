#!/usr/bin/env python

class Comment:
    """
    Class of comment database object.
    Attributes:
        message: Clean message.
        file_type: File type (js, xml, cfg)
        string: Code string to whcih comment is pointed.
    """

    def __init__(self, message, action_name=None, action_number=None):
        self.message = message
        self.action_name = action_name

    def __str__(self):
        return "Requirement '%s'(id=%s, complexity=%d)" %(self.name, self.id, self.complexity)