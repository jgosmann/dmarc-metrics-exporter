Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

[0.7.0] - [unreleased]
----------------------

Changed
^^^^^^^

* Renamed Ansible role ``dmarc-metrics-exporter`` to ``dmarc_metrics_exporter``
  [as ``-`` is no longer allowed in role
  names](https://galaxy.ansible.com/docs/contributing/creating_role.html#role-names).
* ``dmarc_metrics_exporter_virtualenv_path`` variable has been added
* The Ansible role no longer creates a system user. Instead the systemd
  "DynamicUser" feature is used.


[0.6.2] - [2022-09-24]
----------------------

Fixed
^^^^^

* More robust handling of IMAP fetch responses including unknown fields.
  (`#29 <https://github.com/jgosmann/dmarc-metrics-exporter/issues/29>`_)


[0.6.1] - [2022-07-17]
----------------------

Fixed
^^^^^

* The polling of the IMAP mailbox was broken since presumably version 0.5 and
  should be fixed now.


[0.6.0] - [2022-06-11]
----------------------

Added
^^^^^

* ``dmarc-metrics-exporter`` script to allow invocation without the `python -m`
  syntax.

Fixed
^^^^^

* Allow installation with Python 3.10.
* Use ``poetry-core`` as build system to allow installations with fetching fewer
  Poetry dependencies.


[0.5.1] - [2022-02-09]
----------------------

Added
^^^^^

* Officially declare Python 3.10 support.


[0.5.0] - [2022-02-09]
----------------------

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
