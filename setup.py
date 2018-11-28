
import setuptools

with open('README.md', encoding='utf8') as fp:
  readme = fp.read()

setuptools.setup(
  name = 'quel',
  version = '2.0.0.dev0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  install_requires = ['nr.types', 'requests'],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'}
)
