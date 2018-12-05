from setuptools import setup

setup(name='mongoimx',
      version='0.1',
      description='Criate a API to help document insertion in a mongo db in IMX line.',
      url='https://github.com/gustavu92/MO410-projeto_final',
      author='Caio Dadauto and Gustavo Vasconcelos',
      author_email='caiodadauto@gmail.com and gustavu92@gmail.com',
      license='GNU GLP',
      packages=['mongoimx'],
      install_requires=[
          'pymongo'
      ],
      zip_safe=False)
