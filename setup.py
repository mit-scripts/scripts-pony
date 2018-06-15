# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="ScriptsPony",
    version="0.1",
    description="",
    author="",
    author_email="",
    # url='',
    install_requires=[
        "decorator >= 3.4",
        "dnspython >= 1.11",
        "mako >= 1.0",
        "nose >= 1.0",
        "paste >= 1.7",
        "routes >= 1.13",
        "python-ldap >= 2.4",
        "TurboGears2 >= 2.0b7",
        "MySQL-python >= 1.2",
        "zope.sqlalchemy >= 0.4 ",
    ],
    setup_requires=["PasteScript >= 1.7"],
    paster_plugins=["PasteScript", "TurboGears2", "tg.devtools"],
    packages=find_packages(),
    include_package_data=True,
    test_suite="nose.collector",
    tests_require=["WebTest"],
    entry_points={
        "paste.app_factory": ["main = scriptspony.config.middleware:make_app"],
        "paste.app_install": ["main = paste.script.appinstall:Installer"],
        "gearbox.plugins": ["turbogears-devtools = tg.devtools"],
    },
)
