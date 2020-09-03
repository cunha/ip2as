from setuptools import setup, find_packages

setup(
    name="ip2as",
    version='0.0.1',
    author='Alex Marder',
    # author_email='notlisted',
    description="Create prefix-to-AS mappings.",
    url="https://github.com/alexmarder/traceutils",
    packages=find_packages(),
    install_requires=['traceutils'],
    entry_points={
        'console_scripts': [
            'ip2as=ip2as.ip2as:main',
            'ip2ases=ip2as.ip2ases:main',
            'rir2as=ip2as.rir_delegations:main'
        ],
    },
    zip_safe=False,
    include_package_data=True,
    python_requires='>3.6'
)
