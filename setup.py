from setuptools import setup

setup(
    name='importtime_waterfall',
    description='Generate waterfalls from `-Ximporttime` tracing.',
    url='https://github.com/asottile/importtime-waterfall',
    version='0.0.0',
    author='Anthony Sottile',
    author_email='asottile@umich.edu',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    python_requires='>=3.7',
    py_modules=['importtime_waterfall'],
    entry_points={
        'console_scripts': ['importtime-waterfall=importtime_waterfall:main'],
    },
)
