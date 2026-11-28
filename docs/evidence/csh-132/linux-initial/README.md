# Initial Linux report-capacity failure

The 52-target selected command passed. The stock audit then exhausted the
256 MiB `/work/build/tests` tmpfs while writing reports. The stock command
statuses happened to match their expected nonzero verdicts, but the truncated
reports are invalid evidence; `diagnostic.json` identifies them. The raw logs
and compressed reports are retained here without converting the setup failure
into utility evidence.

The rerun uses a 512 MiB report tmpfs. Fixture `/tmp` remains 512 MiB; provider
limits, cases, source pins and assertions are unchanged. The final verifier
requires parseable reports and exact predecessor stock failure identities.
The validation driver now parses every report before retaining it, so an
incomplete report cannot be accepted solely by its command exit status.
