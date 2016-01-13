"""Parsers for various types of external citations. Consumed by the external
citation layer"""
import abc
from collections import namedtuple
import string
import urllib

from pyparsing import Suppress, Word

from regparser.citations import cfr_citations
from regparser.grammar.utils import Marker, QuickSearchable


Cite = namedtuple('Cite', ['cite_type', 'start', 'end', 'components', 'url'])


class FinderBase(object):
    """Base class for all of the external citation parsers. Defines the
    interface they must implement."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def CITE_TYPE(self):
        """A constant to represent the citations this produces."""
        raise NotImplementedError()

    @abc.abstractmethod
    def find(self, node):
        """Give a Node, pull out any external citations it may contain as a
        generator of Cites"""
        raise NotImplementedError()


def fdsys_url(**params):
    """Generate a URL to an FDSYS redirect"""
    params['year'] = params.get('year', 'mostrecent')
    params['link-type'] = params.get('link-type', 'html')
    return 'http://api.fdsys/link?{}'.format(urllib.urlencode(params))


class CFRFinder(FinderBase):
    """Code of Federal Regulations. Explicitly ignore any references within
    this part"""
    CITE_TYPE = 'CFR'

    def find(self, node):
        for cit in cfr_citations(node.text):
            if cit.label.settings['part'] != node.label[0]:
                fdsys_params = {'titlenum': cit.label.settings['cfr_title'],
                                'partnum': cit.label.settings['part']}
                if 'section' in cit.label.settings:
                    fdsys_params['section'] = cit.label.settings['section']

                yield Cite(self.CITE_TYPE, cit.start, cit.end,
                           cit.label.settings,
                           fdsys_url(collection='cfr', **fdsys_params))


class USCFinder(FinderBase):
    """U.S. Code"""
    CITE_TYPE = 'USC'
    GRAMMAR = QuickSearchable(
        Word(string.digits).setResultsName("title") +
        Marker("U.S.C.") +
        Word(string.digits).setResultsName("section"))

    def find(self, node):
        for match, start, end in self.GRAMMAR.scanString(node.text):
            components = {'title': match.title, 'section': match.section}
            yield Cite(self.CITE_TYPE, start, end, components,
                       fdsys_url(collection='uscode', **components))


class PublicLawFinder(FinderBase):
    """Public Law"""
    CITE_TYPE = 'PUBLIC_LAW'
    GRAMMAR = QuickSearchable(
        Marker("Public") + Marker("Law") +
        Word(string.digits).setResultsName("congress") + Suppress("-") +
        Word(string.digits).setResultsName("lawnum"))

    def find(self, node):
        for match, start, end in self.GRAMMAR.scanString(node.text):
            components = {'congress': match.congress, 'lawnum': match.lawnum}
            yield Cite(self.CITE_TYPE, start, end, components,
                       fdsys_url(collection='plaw', lawtype='public',
                                 **components))


class StatutesFinder(FinderBase):
    """Statutes at large"""
    CITE_TYPE = 'STATUTES_AT_LARGE'
    GRAMMAR = QuickSearchable(
        Word(string.digits).setResultsName("volume") + Suppress("Stat.") +
        Word(string.digits).setResultsName("page"))

    def find(self, node):
        for match, start, end in self.GRAMMAR.scanString(node.text):
            components = {'volume': match.volume, 'page': match.page}
            statcit = match.volume + ' stat ' + match.page
            yield Cite(self.CITE_TYPE, start, end, components,
                       fdsys_url(collection='plaw', statutecitation=statcit))


# Surface all of the external citation finder classes
ALL = FinderBase.__subclasses__()
