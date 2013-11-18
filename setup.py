import os
from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()


setup(
    name='socketIO-client',
    version='0.5.3',
    description='A socket.io client library',
    long_description=README + '\n\n' + CHANGES,
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
        'requests',
        'six',
        'websocket-client',
    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True)
