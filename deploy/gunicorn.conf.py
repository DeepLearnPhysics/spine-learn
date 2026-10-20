"""Run one bounded tutor process alongside concurrent static-file requests."""

bind = "0.0.0.0:8080"
workers = 1
worker_class = "gthread"
threads = 4
timeout = 60
graceful_timeout = 60
worker_tmp_dir = "/tmp"
# TLS terminates at the S3DF gateway; do not trust arbitrary forwarded headers.
forwarded_allow_ips = ""
accesslog = "-"
errorlog = "-"
# Do not log query strings or chat bodies.
access_log_format = "%(h)s %(m)s %(U)s %(s)s %(L)s"
# No operator control socket is needed in this read-only Kubernetes container.
control_socket_disable = True
