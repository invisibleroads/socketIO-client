import io
from os.path import abspath, dirname, join
from setuptools import find_packages, setup


HERE = dirname(abspath(__file__))
DESCRIPTION = '\n\n'.join(io.open(
    join(HERE, _), encoding='utf-8',
).read() for _ in [
    'README.rst',
    'CHANGES.rst',
])
setup(
    name='socketIO-client',
    version='0.5.7.4',
    description='A socket.io client library',
    long_description=DESCRIPTION,
    license='MIT',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License',
    ],
    keywords='socket.io node.js',
    author='Roy Hyunjin Han',
    author_email='rhh@crosscompute.com',
    url='https://github.com/invisibleroads/socketIO-client',
    install_requires=[
        'requests>=2.7.0',
        'six>=1.10.0',
        'websocket-client>=0.44.0',
    ],
    tests_require=[
        'nose',
        'coverage',
    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False)
