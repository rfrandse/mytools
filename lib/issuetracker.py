#!/usr/bin/env python3
import abc

class IssueTracker(abc.ABC):
    """
    """

    @abc.abstractmethod
    def create(self):
        pass

    @abc.abstractmethod
    def addnote(self):
        pass

    @abc.abstractmethod
    def modify(self):
        pass

    @abc.abstractmethod
    def view(self, id):
        pass

