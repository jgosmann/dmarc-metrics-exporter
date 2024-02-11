Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

unreleased
----------

Added
^^^^^

* `dmarc_invalid_reports_total` metric with a count of emails from which no
  DMARC report could be parsed.


[0.10.1] - 2024-01-07
---------------------

Fixed
^^^^^

* Add missing Python 3.12 classifier to package.


[0.10.0] - 2024-01-07
---------------------

Added
^^^^^

* Official support for Python 3.12.

Fixed
^^^^^

* Prevent deadlock if IMAP connection terminates abnormally.


[0.9.4] - 2023-08-01
--------------------

This release exclusively updates dependencies in use.


[0.9.3] - 2023-07-25
--------------------

Fixed
^^^^^

* Gracefully handle unknown properties within report XML. In particular, this
  should allow to process reports send by Google again, which was not working
  anymore starting June 2023.


[0.9.2] - 2023-06-30
--------------------

Fixed
^^^^^

* Fix issue with Microsoft Exchange not handling string length being split
  across multiple packages.
  (`#36 <https://github.com/jgosmann/dmarc-metrics-exporter/pull/36>`_)


[0.9.1] - 2023-02-09
--------------------

Fixed
^^^^^

* Fix problems with large emails that would either cause the whole program to
  crash or prevent the processing of any new emails. This was solved by
  updating the bite-parser dependency to at least version 0.2.2.
  (`#34 <https://github.com/jgosmann/dmarc-metrics-exporter/issues/34>`_,
  `bite-parser v0.2.2 <https://github.com/jgosmann/bite-parser/releases/tag/v0.2.2>`_)


[0.9.0] - 2023-01-12
--------------------

Changed
^^^^^^^

* Update bite-parser dependency to version 0.2.1 to get better error output.
* Drop support for Python 3.7.


[0.8.1] - 2023-01-05
--------------------

Fixed
^^^^^

* With some IMAP servers emails were not correctly processed if the UID and
  RFC822 where returned in reverse order in the response.
  (`#33 <https://github.com/jgosmann/dmarc-metrics-exporter/issues/33>`_)


[0.8.0] - 2022-12-11
--------------------

Added
^^^^^

* More logging when email are not processed and more debug logging on closing
  the IMAP connection.

Changed
^^^^^^^

* The systemd unit provided as part of the Ansible role has been hardened.

Fixed
^^^^^

* Correctly handle logout timeout when closing IMAP connection. Previously,
  a timeout during logout would have aborted the process of closing the
  connection.


[0.7.0] - 2022-11-06
--------------------

Added
^^^^^

* Officially declare Python 3.11 support.
* Added the ``dmarc_metrics_exporter_build_info`` metric which contains version
  information in its labels.

Changed
^^^^^^^

* Renamed Ansible role ``dmarc-metrics-exporter`` to ``dmarc_metrics_exporter``
  [as ``-`` is no longer allowed in role
  names](https://galaxy.ansible.com/docs/contributing/creating_role.html#role-names).
* ``dmarc_metrics_exporter_virtualenv_path`` variable has been added
* The Ansible role no longer creates a system user. Instead the systemd
  "DynamicUser" feature is used.
* Add the ``imap_use_ssl`` and ``imap_verify_certificate`` variables to the
  Ansible role.


[0.6.2] - 2022-09-24
--------------------

Fixed
^^^^^

* More robust handling of IMAP fetch responses including unknown fields.
  (`#29 <https://github.com/jgosmann/dmarc-metrics-exporter/issues/29>`_)


[0.6.1] - 2022-07-17
--------------------

Fixed
^^^^^

* The polling of the IMAP mailbox was broken since presumably version 0.5 and
  should be fixed now.


[0.6.0] - 2022-06-11
--------------------

Added
^^^^^

* ``dmarc-metrics-exporter`` script to allow invocation without the `python -m`
  syntax.

Fixed
^^^^^

* Allow installation with Python 3.10.
* Use ``poetry-core`` as build system to allow installations with fetching fewer
  Poetry dependencies.


[0.5.1] - 2022-02-09
--------------------

Added
^^^^^

* Officially declare Python 3.10 support.


[0.5.0] - 2022-02-09
--------------------

Added
^^^^^

* Possibility to configure log output with ``logging`` key in the configuration
  file. `See logging.config documentation for details.
  <https://docs.python.org/3/library/logging.config.html#configuration-dictionary-schema>`_
* ``--debug`` flag to quickly enable debug log output.


Fixed
^^^^^

* Parse IMAP fetch responses properly to support a wider range of IMAP servers.
  (`#17 <https://github.com/jgosmann/dmarc-metrics-exporter/issues/17>`_)


[0.4.3] - 2022-01-25
--------------------

Fixed
^^^^^

* Improve compatibility with different IMAP servers.
  (`#17 <https://github.com/jgosmann/dmarc-metrics-exporter/issues/17>`_)


[0.4.2] - 2022-01-01
--------------------

Fixed
^^^^^

* Make detection of required folders more robust. Fixes issues with Office365.
  (`#15 <https://github.com/jgosmann/dmarc-metrics-exporter/issues/15>`_,
  `#16 <https://github.com/jgosmann/dmarc-metrics-exporter/pull/16>`_)


[0.4.1] - 2021-11-13
--------------------

Fixed
^^^^^

* Fixed the changelog markup so that it renders correctly.
* Fixes of the deployment pipelines.


[0.4.0] - 2021-11-13
--------------------

Changed
^^^^^^^

* The ``metrics_db`` configuration option has been replaced with the
  ``storage_path`` configuration option. To migrate your existing setup:

  1. Ensure that your ``metrics_db`` file is called ``metrics.db``.
  2. Ensure that the directory containing the `metrics.db` file is writable by
     the dmarc-metrics-exporter.
  2. Remove the ``metrics_db`` setting from the configuration file.
  3. Add a new ``storage_path`` setting pointing to the directory containing the
     ``metrics.db`` file.

* Disabled the access log. It clutters the log output with barely relevant
  messages (there is only a single page being served and it will be polled
  regularly by Prometheus).

Added
^^^^^

* Support for reports sent in gzip format.
* A log message will be produced for emails from which no report could be
  extracted.
* Duplicate reports will now only be counted once. The duration for which report
  IDs are stored to detect duplicates can be configured with the
  ``deduplication_max_seconds`` configuration setting. The default is one week.
* Added a Dockerfile to the repository to build a Docker image with
  dmarc-metrics-exporter. `Images for official releases will be published on
  Docker Hub. <https://hub.docker.com/repository/docker/jgosmann/dmarc-metrics-exporter>`_
* Support for Python 3.9.


[0.3.0] - 2021-03-01
--------------------

Changed
^^^^^^^

* Change default port to 9797 which does to collide with other Prometheus
  exporter.


[0.2.3] - 2021-01-11
--------------------

Fixed
^^^^^

* Change the repository link to the correct repository (e.g. on PyPI)


[0.2.2] - 2020-12-31
--------------------

Added
^^^^^

* Ansible role for deployment.


[0.2.1] - 2020-12-31
--------------------

Initial release.
