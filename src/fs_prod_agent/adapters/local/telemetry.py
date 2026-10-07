"""Send the pipeline's and the Strands agent's spans to an OTLP endpoint.

The pipeline and Strands call the OpenTelemetry API. This sets the one process-wide provider they write
to. Locally the endpoint is Jaeger (scripts/observability); on AWS it would be the ADOT collector that
feeds CloudWatch and AgentCore Observability, with no change to the instrumented code.
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE_NAME = "fs-prod-agent"
LOCAL_ENDPOINT = "http://127.0.0.1:4318"

_configured: dict[str, TracerProvider] = {}


def configure_tracing(endpoint: str) -> TracerProvider:
    """Idempotent: the desk builds one app per request, and OTel allows one global provider per process."""
    if endpoint in _configured:
        return _configured[endpoint]
    provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")))
    trace.set_tracer_provider(provider)
    _configured[endpoint] = provider
    return provider


def flush() -> None:
    for provider in _configured.values():
        provider.force_flush()
