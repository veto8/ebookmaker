#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

Writer package

Copyright 2009-2010 by Marcello Perathoner
Copyright 2025 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Base classes for *Writer modules. (EpubWriter, PluckerWriter, ...)

"""
import re
import subprocess

from functools import partial
import os.path

from lxml import etree
from lxml.builder import ElementMaker

from libgutenberg.Logger import critical, debug, info, error
import libgutenberg.GutenbergGlobals as gg
from libgutenberg import MediaTypes

from ebookmaker import parsers
from ebookmaker import ParserFactory
from ebookmaker.CommonCode import Options
from ebookmaker.Version import VERSION, GENERATOR


options = Options()

def remove_cr(content):
    content = re.sub(r'\s*[\r\n]+\s*', '&#10;', content)
    return content

class BaseWriter(object):
    """
    Base class for EpubWriter, PluckerWriter, ...

    also used as /dev/null writer for debugging

    """

    VALIDATOR = None

    def build(self, job):
        """ override this in a real writer """
        pass


    @staticmethod
    def write_with_crlf(filename, bytes_):
        # \r\n is PG standard
        bytes_ = b'\r\n'.join(bytes_.splitlines()) + b'\r\n'

        # open binary so windows doesn't add another \r
        with open(filename, 'wb') as fp:
            fp.write(bytes_)


    def validate(self, job):
        """ Validate generated file using external tools. """

        if not self.VALIDATOR:
            return 0

        debug("Validating %s ..." % job.outputfile)

        filename = os.path.join(os.path.abspath(job.outputdir), job.outputfile)

        if hasattr(options.config, self.VALIDATOR):
            validator = getattr(options.config, self.VALIDATOR)
            info('validating...')
            params = validator.split() + [filename]
            checker = subprocess.run(params,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

            if checker.stderr:
                critical('validation error reported by %s:\r', self.VALIDATOR)
                critical(checker.stderr.decode("utf-8"))
                return 1

        info("%s validates ok." % job.outputfile)
        return 0


    def sync(self):
        """  Override this if you need to sync before program exit. """
        pass


    def make_links_relative(self, xhtml, base_url):
        """ Make absolute links in xhtml relative to base_url. """

        debug("Making links relative to: %s" % base_url)
        xhtml.rewrite_links(partial(gg.make_url_relative, base_url))



em = ElementMaker()

class HTMLishWriter(BaseWriter):
    """ Base class for writers with HTMLish contents. """

    @staticmethod
    def add_class(elem, class_):
        """ Add a class to html element. """

        classes = elem.get('class', '').split()
        classes.append(class_)
        elem.set('class', ' '.join(classes))


    @staticmethod
    def add_meta(xhtml, name, content):
        """ Add a meta tag. """

        for head in gg.xpath(xhtml, '//xhtml:head'):
            meta = em.meta(name=name, content=remove_cr(content))
            meta.tail = '\n'
            head.append(meta)

    @staticmethod
    def add_prop(xhtml, prop, content):
        """ Add a property meta tag. """

        for head in gg.xpath(xhtml, '//xhtml:head'):
            meta = em.meta(property=prop, content=remove_cr(content))
            meta.tail = '\n'
            head.append(meta)


    @staticmethod
    def add_meta_generator(xhtml):
        """ Add our piss mark. """

        HTMLishWriter.add_meta(xhtml, 'generator', GENERATOR % VERSION)


    @staticmethod
    def add_internal_css(xhtml, css_as_string):
        """ Add internal stylesheet to html. """

        if css_as_string and xhtml is not None:
            css_as_string = '\n' + css_as_string.strip(' \n') + '\n'
            for head in gg.xpath(xhtml, '//xhtml:head'):
                style = em.style(css_as_string, type='text/css')
                style.tail = '\n'
                head.insert(0, style)

    @staticmethod
    def add_body_class(xhtml, classname):
        """ Add a class to the body element. """

        if classname and xhtml is not None:
            for body in gg.xpath(xhtml, '//xhtml:body'):
                HTMLishWriter.add_class(body, classname)


    def add_external_css(self, spider, xhtml, css_as_string, url):
        """ Add external stylesheet to html. """

        if css_as_string:
            attribs = parsers.ParserAttributes()
            attribs.orig_mediatype = 'text/css'
            attribs.url = attribs.orig_url = url
            p = ParserFactory.ParserFactory.get(attribs)
            p.parse_string(css_as_string)
            p.make_links_absolute()
            spider.parsers.append(p)

        if xhtml is not None:
            for head in gg.xpath(xhtml, '//xhtml:head'):
                link = em.link(href=url, rel='stylesheet', type='text/css')
                link.tail = '\n'
                head.append(link)


