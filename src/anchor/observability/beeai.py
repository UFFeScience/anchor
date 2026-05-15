from opentelemetry import trace as trace_api
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from openinference.instrumentation.beeai import BeeAIInstrumentor


def setup_observability(span_collector: SpanProcessor) -> None:
    tracer_provider = TracerProvider(
        resource=Resource({"service.name": "beeai-agentic"})
    )

    tracer_provider.add_span_processor(span_collector)
    trace_api.set_tracer_provider(tracer_provider)

    BeeAIInstrumentor().instrument()
