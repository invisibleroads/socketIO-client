from os.path import abspath, dirname, join
from setuptools import find_packages, setup


REQUIREMENTS = [
    'requests',
    'six',
    'websocket-client',
]


HERE = dirname(abspath(__file__))
DESCRIPTION = '\n\n'.join(open(join(HERE, _)).read() for _ in [
    'README.rst',
    'CHANGES.rst',
])
setup(
    name='socketIO-client',
    version='0.6.1',
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
    install_requires=REQUIREMENTS,
    tests_require=[
        'nose',
        'coverage',
    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False)
