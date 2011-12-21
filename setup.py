#!/usr/bin/env python

#Copyright (C) 2011  Tartaise Philippe

    #This program is free software: you can redistribute it and/or modify
    #it under the terms of the GNU General Public License as published by
    #the Free Software Foundation, either version 3 of the License, or
    #(at your option) any later version.

    #This program is distributed in the hope that it will be useful,
    #but WITHOUT ANY WARRANTY; without even the implied warranty of
    #MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    #GNU General Public License for more details.

    #You should have received a copy of the GNU General Public License
    #along with this program.  If not, see <http://www.gnu.org/licenses/>.

sdict = {
    'name' : 'txRedEvent',
    'version' : '1.0',
'packages' : ['txRedEvent'],
    'description' : 'Python/Twisted/Redis event system based on PubSub',
    'author' : 'Tartaise Philippe',
    'author_email' : 'ptartaise@dynamikdev.com',
    'keywords': ['Redis', 'Twisted', 'PubSub', 'event'],
    'classifiers' : [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GPLv3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Twisted',
        ],
}

from setuptools import setup
setup(**sdict)