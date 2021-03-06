# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2016-2017 Ryan Roden-Corrent (rcorre) <ryan@rcorre.net>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Test the web history completion category."""

import datetime

import pytest
from PyQt5.QtCore import QModelIndex

from qutebrowser.misc import sql
from qutebrowser.completion.models import histcategory


@pytest.fixture
def hist(init_sql, config_stub):
    config_stub.data['completion'] = {'timestamp-format': '%Y-%m-%d',
                                      'web-history-max-items': -1}
    return sql.SqlTable('CompletionHistory', ['url', 'title', 'last_atime'])


@pytest.mark.parametrize('pattern, before, after', [
    ('foo',
     [('foo', ''), ('bar', ''), ('aafobbb', '')],
     [('foo',)]),

    ('FOO',
     [('foo', ''), ('bar', ''), ('aafobbb', '')],
     [('foo',)]),

    ('foo',
     [('FOO', ''), ('BAR', ''), ('AAFOBBB', '')],
     [('FOO',)]),

    ('foo',
     [('baz', 'bar'), ('foo', ''), ('bar', 'foo')],
     [('foo', ''), ('bar', 'foo')]),

    ('foo',
     [('fooa', ''), ('foob', ''), ('fooc', '')],
     [('fooa', ''), ('foob', ''), ('fooc', '')]),

    ('foo',
     [('foo', 'bar'), ('bar', 'foo'), ('biz', 'baz')],
     [('foo', 'bar'), ('bar', 'foo')]),

    ('foo bar',
     [('foo', ''), ('bar foo', ''), ('xfooyybarz', '')],
     [('xfooyybarz', '')]),

    ('foo%bar',
     [('foo%bar', ''), ('foo bar', ''), ('foobar', '')],
     [('foo%bar', '')]),

    ('_',
     [('a_b', ''), ('__a', ''), ('abc', '')],
     [('a_b', ''), ('__a', '')]),

    ('%',
     [('\\foo', '\\bar')],
     []),

    ("can't",
     [("can't touch this", ''), ('a', '')],
     [("can't touch this", '')]),
])
def test_set_pattern(pattern, before, after, model_validator, hist):
    """Validate the filtering and sorting results of set_pattern."""
    for row in before:
        hist.insert({'url': row[0], 'title': row[1], 'last_atime': 1})
    cat = histcategory.HistoryCategory()
    model_validator.set_model(cat)
    cat.set_pattern(pattern)
    model_validator.validate(after)


@pytest.mark.parametrize('max_items, before, after', [
    (-1, [
        ('a', 'a', '2017-04-16'),
        ('b', 'b', '2017-06-16'),
        ('c', 'c', '2017-05-16'),
    ], [
        ('b', 'b', '2017-06-16'),
        ('c', 'c', '2017-05-16'),
        ('a', 'a', '2017-04-16'),
    ]),
    (3, [
        ('a', 'a', '2017-04-16'),
        ('b', 'b', '2017-06-16'),
        ('c', 'c', '2017-05-16'),
    ], [
        ('b', 'b', '2017-06-16'),
        ('c', 'c', '2017-05-16'),
        ('a', 'a', '2017-04-16'),
    ]),
    (2 ** 63 - 1, [  # Maximum value sqlite can handle for LIMIT
        ('a', 'a', '2017-04-16'),
        ('b', 'b', '2017-06-16'),
        ('c', 'c', '2017-05-16'),
    ], [
        ('b', 'b', '2017-06-16'),
        ('c', 'c', '2017-05-16'),
        ('a', 'a', '2017-04-16'),
    ]),
    (2, [
        ('a', 'a', '2017-04-16'),
        ('b', 'b', '2017-06-16'),
        ('c', 'c', '2017-05-16'),
    ], [
        ('b', 'b', '2017-06-16'),
        ('c', 'c', '2017-05-16'),
    ]),
    (1, [], []),  # issue 2849 (crash with empty history)
])
def test_sorting(max_items, before, after, model_validator, hist, config_stub):
    """Validate the filtering and sorting results of set_pattern."""
    config_stub.data['completion']['web-history-max-items'] = max_items
    for url, title, atime in before:
        timestamp = datetime.datetime.strptime(atime, '%Y-%m-%d').timestamp()
        hist.insert({'url': url, 'title': title, 'last_atime': timestamp})
    cat = histcategory.HistoryCategory()
    model_validator.set_model(cat)
    cat.set_pattern('')
    model_validator.validate(after)


def test_remove_rows(hist, model_validator):
    hist.insert({'url': 'foo', 'title': 'Foo'})
    hist.insert({'url': 'bar', 'title': 'Bar'})
    cat = histcategory.HistoryCategory()
    model_validator.set_model(cat)
    cat.set_pattern('')
    hist.delete('url', 'foo')
    # histcategory does not care which index was removed, it just regenerates
    cat.removeRows(QModelIndex(), 1)
    model_validator.validate([('bar', 'Bar', '')])
