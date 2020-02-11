---
name: Bug report
about: Create a report to help us improve
labels: 

---

Thanks for taking the time to report an issue!

Please before continuing read http://docs.python-zeep.org/en/master/reporting_bugs.html

Since Zeep is a module I've created and currently maintain in my spare
time I need as much information as possible to quickly analyze/fix issues.

Please provide the following information:

1. The version of zeep (or if you are running master the commit hash/date)
2. The WSDL you are using
3. And most importantly, a [runnable example script](http://docs.python-zeep.org/en/master/reporting_bugs.html) which exposes the problem.

Note that issues without a runnable example script are likely to be closed
without further research. This is done to keep the number of issues 
manageable and focus my time on actually fixing issues instead of analyzing
the exact nature of the issue.

Also please don't paste WSDL/XSD file contents directly into the issue since 
that makes it hard to read. Please make it available somewhere public where your example script can retrieve it form (so not behind a company firewall)
