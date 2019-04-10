from setuptools import setup, find_packages

requires = [
    'slackclient'
]

setup(
    name="gameday-bot",
    version='0.2.0',
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
