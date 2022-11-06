dmarc-metrics-exporter Ansible role
===================================

This Ansible role allows an automated deployment of dmarc-metrics-exporter.

To use the role add

.. code-block:: yaml

    roles:
      - name: dmarc_metrics_exporter
        src: https://github.com/jgosmann/dmarc-metrics-exporter.git

to your ``requirements.yml``
and then install the role with:

.. code-block:: bash

    ansible-galaxy install -r requirements.yml

You can then use the role in your playbooks like so:

.. code-block:: yaml

  - hosts: all
    roles:
      - role: dmarc-metrics-exporter
        vars:
          imap_username: dmarc@your-domain.com
          imap_password: !vault |
            $ANSIBLE_VAULT;1.1;AES256
            62663862643861313432633433373264663362313362353865313362396666356230653630633135
            6265623537383536363639613034643162396230376163610a363564306334326234386630646265
            38626566663965633931366364613663626539623938633133303830613263383831363532326530
            3062303461343065650a313935376235313466616233376639613437353230626561653534643537
            6166

Use ``ansible-vault encrypt_string`` to obtain an encrypted password.

Available role variables
------------------------

* ``dmarc_metrics_exporter_version`` (string, default: ``""``): dmarc-metrics-exporter version to install.
* ``dmarc_metrics_exporter_virtualenv_path`` (string, default: ``"/opt/dmarc_metrics_exporter"``): Path to create Python virtualenv in for the dmarc-metrics-exporter.
* ``listen_addr`` (string, default ``"127.0.0.1"``): Listen address for the HTTP endpoint.
* ``listen_port`` (number, default ``9797``): Port to listen on for the HTTP endpoint.
* ``imap_host`` (string, default ``"localhost"``): Hostname of IMAP server to connect to.
* ``imap_port`` (number, default ``993``): Port of the IMAP server to connect to.
* ``imap_username`` (string, required): Login username for the IMAP connection.
* ``imap_password``: (string, required): Login password for the IMAP connection.
* ``imap_use_ssl``: (boolean, default ``true``): Whether to use SSL encryption on the IMAP connection.
* ``imap_verify_certificate``: (boolean, default ``true``): Whether to verify the SSL certificate.
* ``folder_inbox`` (string, default ``"INBOX"``): IMAP mailbox that is checked for incoming DMARC aggregate reports.
* ``folder_done`` (string, default ``"Archive"``): IMAP mailbox that successfully processed reports are moved to.
* ``folder_error``: (string, default ``"Invalid"``): IMAP mailbox that emails are moved to that could not be processed.
* ``poll_interval_seconds`` (number, default ``60``): How often to poll the IMAP server in seconds.
* ``deduplication_max_seconds`` (number, default ``604800`` which is 7 days): How long individual report IDs will be remembered to avoid counting double delivered reports twice.
