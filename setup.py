from setuptools import setup, find_packages

requires = [
    'bs4',
    'slackclient'
]

setup(
    name="gameday-bot",
    version='0.0.1',
    author="Dennis Chan",
    packages=find_packages(),
    install_requires=requires,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'gameday=gameday:main',
        ]
    }
)
