import dmarc_metrics_exporter.model as m


def create_sample_xml(*, report_id: str = "12598866915817748661") -> str:
    return f"""
<?xml version="1.0" encoding="UTF-8" ?>
<feedback>
  <report_metadata>
    <org_name>google.com</org_name>
    <email>noreply-dmarc-support@google.com</email>
    <extra_contact_info>https://support.google.com/a/answer/2466580</extra_contact_info>
    <report_id>{report_id}</report_id>
    <date_range>
      <begin>1607299200</begin>
      <end>1607385599</end>
    </date_range>
  </report_metadata>
  <policy_published>
    <domain>mydomain.de</domain>
    <adkim>r</adkim>
    <aspf>r</aspf>
    <p>none</p>
    <sp>none</sp>
    <pct>100</pct>
    <np>none</np>
  </policy_published>
  <record>
    <row>
      <source_ip>dead:beef:1:abc::</source_ip>
      <count>1</count>
      <policy_evaluated>
        <disposition>none</disposition>
        <dkim>pass</dkim>
        <spf>fail</spf>
      </policy_evaluated>
    </row>
    <identifiers>
      <header_from>mydomain.de</header_from>
    </identifiers>
    <auth_results>
      <dkim>
        <domain>mydomain.de</domain>
        <result>pass</result>
        <selector>default</selector>
      </dkim>
      <spf>
        <domain>my-spf-domain.de</domain>
        <result>pass</result>
      </spf>
    </auth_results>
  </record>
</feedback>
""".strip()


SAMPLE_DATACLASS = m.Feedback(
    report_metadata=m.ReportMetadataType(
        org_name="google.com",
        email="noreply-dmarc-support@google.com",
        extra_contact_info="https://support.google.com/a/answer/2466580",
        report_id="12598866915817748661",
        date_range=m.DateRangeType(
            begin=1607299200,
            end=1607385599,
        ),
    ),
    policy_published=m.PolicyPublishedType(
        domain="mydomain.de",
        adkim=m.AlignmentType.R,
        aspf=m.AlignmentType.R,
        p=m.DispositionType.NONE_VALUE,
        sp=m.DispositionType.NONE_VALUE,
        pct=100,
    ),
    record=[
        m.RecordType(
            row=m.RowType(
                source_ip="dead:beef:1:abc::",
                count=1,
                policy_evaluated=m.PolicyEvaluatedType(
                    disposition=m.DispositionType.NONE_VALUE,
                    dkim=m.DmarcresultType.PASS_VALUE,
                    spf=m.DmarcresultType.FAIL,
                ),
            ),
            identifiers=m.IdentifierType(
                header_from="mydomain.de",
            ),
            auth_results=m.AuthResultType(
                dkim=[
                    m.DkimauthResultType(
                        domain="mydomain.de",
                        result=m.DkimresultType.PASS_VALUE,
                        selector="default",
                    )
                ],
                spf=[
                    m.SpfauthResultType(
                        domain="my-spf-domain.de", result=m.SpfresultType.PASS_VALUE
                    )
                ],
            ),
        )
    ],
)
